"""
Agent基类
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
import json
import os
import time

from ..utils.llm_client import get_llm_client, LLMClient


class JsonParseAfterStreamError(ValueError):
    """流式输出结束后解析为 JSON 失败，可携带原始回复供调用方判断是否为拒绝类回复。"""
    def __init__(self, message: str, raw_response: str = ""):
        super().__init__(message)
        self.raw_response = raw_response or ""


class BaseAgent(ABC):
    """Agent基类"""
    
    def __init__(self, name: str):
        self.name = name
        self._llm: Optional[LLMClient] = None
        self._conversation_history: List[Dict[str, str]] = []  # 多轮对话历史
    
    @property
    def llm(self) -> LLMClient:
        """获取LLM客户端"""
        if self._llm is None:
            self._llm = get_llm_client()
        return self._llm
    
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """系统提示词"""
        pass
    
    @abstractmethod
    def run(self, **kwargs) -> Any:
        """执行Agent任务"""
        pass
    
    def _append_stage_log(self, content: str):
        """若配置了 run_log_dir 与 current_stage_name，则追加到阶段日志文件"""
        try:
            from ..config import get_config
            cfg = get_config()
            if getattr(cfg, 'run_log_dir', None) and getattr(cfg, 'current_stage_name', None):
                os.makedirs(cfg.run_log_dir, exist_ok=True)
                path = os.path.join(cfg.run_log_dir, cfg.current_stage_name + ".txt")
                with open(path, 'a', encoding='utf-8') as f:
                    f.write(content)
                    if not content.endswith('\n'):
                        f.write('\n')
        except Exception:
            pass

    def _chat(self, user_message: str, temperature: Optional[float] = None, print_prompt: bool = False) -> str:
        """与LLM对话（单轮），含输出清洗"""
        from ..utils.llm_client import clean_llm_output
        if print_prompt:
            print("\n" + "=" * 80)
            print(f"【{self.name} - 单轮对话提示词】")
            print("=" * 80)
            print(f"【系统提示】\n{self.system_prompt[:500]}...")
            print(f"\n【用户消息】\n{user_message}")
            print("=" * 80 + "\n")
        
        response = self.llm.chat_with_system(
            self.system_prompt,
            user_message,
            temperature=temperature
        )
        self._append_stage_log("\n=== PROMPT ===\n" + user_message + "\n=== RESPONSE ===\n" + response)
        return clean_llm_output(response)
    
    def _chat_stream(self, user_message: str, temperature: Optional[float] = None, print_prompt: bool = False) -> str:
        """与LLM对话（单轮，流式输出），含 refusal 检测、重试和输出清洗"""
        import sys
        from ..utils.refusal_detector import is_likely_refusal
        from ..utils.llm_client import clean_llm_output
        
        if print_prompt:
            print("\n" + "=" * 80)
            print(f"【{self.name} - 单轮对话提示词（流式）】")
            print("=" * 80)
            print(f"【系统提示】\n{self.system_prompt[:500]}...")
            print(f"\n【用户消息】\n{user_message}")
            print("=" * 80 + "\n")
        
        # 构建消息
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # 流式调用：用线程局部标记告诉部署版 LogCapture 如何写日志（不换行 / 第一块带前缀 / 结束补换行）
        from ..utils.stdout_streaming import set_stdout_streaming, set_stdout_stream_first, set_stdout_stream_end
        
        max_attempts = 2
        for attempt in range(max_attempts):
            accumulated_text = ""
            try:
                set_stdout_streaming(True)
                set_stdout_stream_first(True)
                for chunk in self.llm.chat_stream(messages, temperature=temperature):
                    accumulated_text += chunk
                    print(chunk, end="", flush=True)
                print(flush=True)
                self._append_stage_log("\n=== PROMPT ===\n" + user_message + "\n=== RESPONSE ===\n" + accumulated_text)
                
                # refusal 检测：如果模型拒绝或说英文身份声明，重试一次
                if attempt < max_attempts - 1 and is_likely_refusal(accumulated_text):
                    self.log("⚠️ 检测到模型拒绝/身份声明，使用更严格的提示重试...")
                    messages = [
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": "【严格要求】你必须直接完成创作任务，全程使用中文，禁止输出任何身份声明或英文内容。直接输出创作内容。\n\n" + user_message}
                    ]
                    continue
                
                # 清洗输出：去掉"我是xxx"前缀和"需要我xxx？"后缀
                return clean_llm_output(accumulated_text)
            except Exception as e:
                self.log(f"流式输出失败: {e}，回退到普通模式")
                result = self._chat(user_message, temperature=temperature, print_prompt=False)
                return clean_llm_output(result)
            finally:
                set_stdout_stream_end(True)
                set_stdout_streaming(False)
        
        # 所有重试都是 refusal，清洗后返回最后一次的结果
        return clean_llm_output(accumulated_text)
    
    def _chat_stream_then_json(
        self,
        user_message: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        max_retries: int = 2,
        print_prompt: bool = False,
    ) -> Dict:
        """
        与 LLM 流式对话，边输出边打印，结束后将完整回复解析为 JSON 并返回。
        用于梗概、人设等需要 JSON 的步骤，既保留流式观感又拿到结构化结果。
        解析失败时可重试整轮；调用方可在仍失败时回退到 _chat_json_structured。
        """
        from ..utils.stdout_streaming import set_stdout_streaming, set_stdout_stream_first, set_stdout_stream_end
        from ..utils.json_fixer import safe_json_loads
        
        if print_prompt:
            print("\n" + "=" * 80)
            print(f"【{self.name} - 流式 JSON 提示词】")
            print("=" * 80)
            print(f"【用户消息】\n{user_message[:500]}...")
            print("=" * 80 + "\n")
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message}
        ]
        last_error = None
        for attempt in range(max_retries):
            accumulated_text = ""
            try:
                set_stdout_streaming(True)
                set_stdout_stream_first(True)
                for chunk in self.llm.chat_stream(messages, temperature=temperature, max_tokens=max_tokens):
                    accumulated_text += chunk
                    print(chunk, end="", flush=True)
                print(flush=True)
                self._append_stage_log("\n=== PROMPT ===\n" + user_message + "\n=== RESPONSE (stream→JSON) ===\n" + accumulated_text)
                result = safe_json_loads(accumulated_text)
                return result
            except (ValueError, json.JSONDecodeError) as e:
                last_error = e
                last_raw_response = accumulated_text
                if attempt < max_retries - 1:
                    self.log(f"流式输出后 JSON 解析失败（尝试 {attempt + 1}/{max_retries}），重试...")
                else:
                    self.log(f"流式输出后 JSON 解析失败，已重试{max_retries}次：{str(e)[:100]}")
                    raise JsonParseAfterStreamError(str(e), raw_response=last_raw_response)
            finally:
                set_stdout_stream_end(True)
                set_stdout_streaming(False)
        if last_error:
            raise last_error
        raise RuntimeError("流式 JSON 调用失败：未知错误")
    
    def _chat_multi_turn(
        self, 
        user_message: str, 
        temperature: Optional[float] = None,
        continue_conversation: bool = True,
        print_prompt: bool = False
    ) -> str:
        """
        多轮对话
        
        Args:
            user_message: 用户消息
            temperature: 温度参数
            continue_conversation: 是否继续之前的对话（False则开始新对话）
            print_prompt: 是否打印提示词
        
        Returns:
            模型回复
        """
        if not continue_conversation:
            self._conversation_history = []
        
        # 构建完整消息列表
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self._conversation_history)
        messages.append({"role": "user", "content": user_message})
        
        if print_prompt:
            print("\n" + "=" * 80)
            print(f"【{self.name} - 多轮对话提示词】轮次{len(self._conversation_history)//2 + 1}")
            print("=" * 80)
            if not self._conversation_history:
                print(f"【系统提示】\n{self.system_prompt[:300]}...")
            else:
                print(f"【对话历史】已有{len(self._conversation_history)}条消息")
            print(f"\n【本轮用户消息】\n{user_message}")
            print("=" * 80 + "\n")
        
        # 调用 LLM
        response = self.llm.chat(messages, temperature=temperature)
        
        # 保存对话历史
        self._conversation_history.append({"role": "user", "content": user_message})
        self._conversation_history.append({"role": "assistant", "content": response})
        
        return response
    
    def clear_conversation(self):
        """清空对话历史"""
        self._conversation_history = []
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """获取对话历史"""
        return self._conversation_history.copy()
    
    def _chat_json(self, user_message: str, temperature: Optional[float] = None, max_retries: int = 3, max_tokens: Optional[int] = None, print_prompt: bool = False) -> Dict:
        """
        获取JSON格式回复（带重试机制）
        
        Args:
            user_message: 用户消息
            temperature: 温度参数
            max_retries: 最大重试次数
            max_tokens: 最大输出token数
            print_prompt: 是否打印提示词
        """
        if print_prompt:
            print("\n" + "=" * 80)
            print(f"【{self.name} - JSON格式提示词】")
            print("=" * 80)
            print(f"【系统提示】\n{self.system_prompt[:300]}...")
            print(f"\n【用户消息】\n{user_message}")
            print("=" * 80 + "\n")
        
        last_error = None
        for attempt in range(max_retries):
            try:
                self.log(f"正在调用LLM（尝试 {attempt + 1}/{max_retries}）...")
                result = self.llm.chat_json(
                    self.system_prompt,
                    user_message,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                self._append_stage_log("\n=== PROMPT ===\n" + user_message + "\n=== RESPONSE (JSON) ===\n" + json.dumps(result, ensure_ascii=False, indent=2))
                return result
            except (ValueError, json.JSONDecodeError) as e:
                last_error = e
                if attempt < max_retries - 1:
                    self.log(f"JSON解析失败（尝试 {attempt + 1}/{max_retries}）：{str(e)[:100]}，2秒后重试...")
                    time.sleep(2)
                else:
                    self.log(f"JSON解析失败，已重试{max_retries}次，放弃。错误：{str(e)[:100]}")
                    raise
            except Exception as e:
                # 捕获网络错误、超时等其他异常
                last_error = e
                error_type = type(e).__name__
                if attempt < max_retries - 1:
                    self.log(f"LLM调用异常（尝试 {attempt + 1}/{max_retries}）：{error_type}: {str(e)[:100]}，3秒后重试...")
                    time.sleep(3)
                else:
                    self.log(f"LLM调用失败，已重试{max_retries}次，放弃。错误：{error_type}: {str(e)[:100]}")
                    raise
        
        # 如果所有重试都失败
        if last_error:
            raise last_error
        raise RuntimeError("LLM调用失败：未知错误")
    
    def _chat_json_structured(
        self, 
        user_message: str, 
        json_schema: Dict[str, Any],
        temperature: Optional[float] = None, 
        max_retries: int = 2, 
        max_tokens: Optional[int] = None, 
        print_prompt: bool = False,
        fallback_to_normal: bool = True
    ) -> Dict:
        """
        使用 Claude 结构化输出获取 JSON 格式回复（约束解码，格式保证正确）
        
        这是 _chat_json 的增强版，使用 Claude 的结构化输出功能，
        通过约束解码从生成阶段就保证 JSON 格式符合 schema。
        
        参考文档：https://platform.claude.com/docs/zh-CN/build-with-claude/structured-outputs
        
        Args:
            user_message: 用户消息
            json_schema: JSON Schema 定义（必须符合 Claude 限制）
            temperature: 温度参数
            max_retries: 最大重试次数（结构化输出更稳定，通常只需1-2次）
            max_tokens: 最大输出 token 数
            print_prompt: 是否打印提示词
            fallback_to_normal: 如果结构化输出失败，是否回退到普通 JSON 模式
        
        Returns:
            解析后的 JSON 字典
        
        注意：
        - 首次使用特定 schema 时会有编译延迟
        - 如果 API 不支持结构化输出，会自动回退到普通模式
        """
        if print_prompt:
            print("\n" + "=" * 80)
            print(f"【{self.name} - 结构化输出提示词】")
            print("=" * 80)
            print(f"【系统提示】\n{self.system_prompt[:300]}...")
            print(f"\n【用户消息】\n{user_message[:500]}...")
            print(f"\n【Schema 字段】\n{list(json_schema.get('properties', {}).keys())}")
            print("=" * 80 + "\n")
        
        last_error = None
        for attempt in range(max_retries):
            try:
                self.log(f"正在调用 Claude 结构化输出（尝试 {attempt + 1}/{max_retries}）...")
                result = self.llm.chat_json_with_schema(
                    self.system_prompt,
                    user_message,
                    json_schema=json_schema,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                print(f"✅ 结构化输出成功")
                self.log(f"✅ 结构化输出成功")
                self._append_stage_log("\n=== PROMPT ===\n" + user_message + "\n=== RESPONSE (JSON) ===\n" + json.dumps(result, ensure_ascii=False, indent=2))
                return result
                
            except Exception as e:
                last_error = e
                error_type = type(e).__name__
                error_msg = str(e)[:200]
                
                # 检查是否是 API 不支持结构化输出
                if "output_format" in error_msg.lower() or "json_schema" in error_msg.lower():
                    self.log(f"⚠️ API 可能不支持结构化输出：{error_msg}")
                    if fallback_to_normal:
                        self.log(f"⚠️ 回退到普通 JSON 模式...")
                        return self._chat_json(
                            user_message,
                            temperature=temperature,
                            max_retries=max_retries,
                            max_tokens=max_tokens,
                            print_prompt=False
                        )
                    raise
                
                if attempt < max_retries - 1:
                    self.log(f"结构化输出失败（尝试 {attempt + 1}/{max_retries}）：{error_type}: {error_msg}，2秒后重试...")
                    time.sleep(2)
                else:
                    self.log(f"结构化输出失败，已重试{max_retries}次")
                    
                    # 最后尝试回退到普通模式
                    if fallback_to_normal:
                        self.log(f"⚠️ 回退到普通 JSON 模式...")
                        try:
                            return self._chat_json(
                                user_message,
                                temperature=temperature,
                                max_retries=2,
                                max_tokens=max_tokens,
                                print_prompt=False
                            )
                        except Exception as fallback_error:
                            self.log(f"❌ 回退模式也失败：{str(fallback_error)[:100]}")
                            raise last_error
                    raise
        
        # 如果所有重试都失败
        if last_error:
            raise last_error
        raise RuntimeError("结构化输出调用失败：未知错误")
    
    def log(self, message: str):
        """日志输出：若配置了 run_log_dir 则写入阶段文件；console_quiet 为 False 时才打印到控制台"""
        self._append_stage_log(f"[{self.name}] {message}")
        try:
            from ..config import get_config
            if not getattr(get_config(), 'console_quiet', False):
                print(f"[{self.name}] {message}")
        except Exception:
            print(f"[{self.name}] {message}")
