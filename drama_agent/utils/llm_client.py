"""
LLM客户端封装

支持功能：
- 普通对话
- JSON 模式（OpenAI 兼容）
- Claude 结构化输出（JSON Schema 约束解码）

参考文档：https://platform.claude.com/docs/zh-CN/build-with-claude/structured-outputs
"""
import json
import re
import sys
import time
import os
import httpx
from typing import Optional, List, Dict, Any
from openai import OpenAI

from ..config import get_config, LLMProvider
from .json_fixer import safe_json_loads


def _wrap_llm_error(e: Exception, timeout_seconds: float = 120.0) -> None:
    """
    将 LLM 超时/网络错误转换为可读的 RuntimeError 并重新抛出，
    同时在 stderr 打印，便于控制台和日志看到。
    """
    err_msg = str(e).strip()
    if not err_msg:
        err_msg = type(e).__name__
    # 常见超时/网络异常
    if isinstance(e, (httpx.TimeoutException, httpx.ConnectError)):
        friendly = f"[LLM] 网络/超时错误（约 {int(timeout_seconds)}s）：{err_msg}"
    elif "timeout" in err_msg.lower() or "timed out" in err_msg.lower():
        friendly = f"[LLM] 请求超时（约 {int(timeout_seconds)}s），请检查网络或稍后重试。原始错误：{err_msg}"
    elif "connection" in err_msg.lower() or "connect" in err_msg.lower():
        friendly = f"[LLM] 连接失败，请检查网络或 API 地址。原始错误：{err_msg}"
    else:
        friendly = f"[LLM] 调用失败：{err_msg}"
    print(friendly, file=sys.stderr, flush=True)
    raise RuntimeError(friendly) from e


def _merge_system_to_user(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    将 system role 的内容合并到第一条 user message 中。
    避免云雾等代理 API 在 system prompt 前注入额外身份指令导致冲突。
    """
    system_parts = []
    other_msgs = []
    for msg in messages:
        if msg["role"] == "system":
            system_parts.append(msg["content"])
        else:
            other_msgs.append(msg)
    if not system_parts:
        return messages
    system_text = "\n\n".join(system_parts)
    # 合并到第一条 user message
    if other_msgs and other_msgs[0]["role"] == "user":
        other_msgs[0] = {
            "role": "user",
            "content": f"[指令]\n{system_text}\n[/指令]\n\n{other_msgs[0]['content']}"
        }
    else:
        other_msgs.insert(0, {"role": "user", "content": f"[指令]\n{system_text}\n[/指令]"})
    return other_msgs


def _strip_thinking_from_content(content: str, reasoning_content: str) -> str:
    """
    云雾 API 对 Grok 等模型的 thinking 处理有 bug：reasoning_content 的内容
    会被拼到 content 开头。当 reasoning_content 存在时，从 content 中剥掉这段前缀。
    """
    if not reasoning_content or not content:
        return content
    # 精确前缀匹配：reasoning_content 就是被误拼到 content 开头的部分
    if content.startswith(reasoning_content):
        return content[len(reasoning_content):].lstrip('\n')
    # 有时 reasoning_content 末尾多/少空白，做 strip 后再试
    rc_stripped = reasoning_content.rstrip()
    if rc_stripped and content.startswith(rc_stripped):
        return content[len(rc_stripped):].lstrip('\n')
    return content


def clean_llm_output(text: str) -> str:
    """
    清洗 LLM 输出：去掉开头的身份声明/寒暄和结尾的反问/邀请。
    策略：逐段扫描，跳过包含身份关键词的段落，保留纯创作内容。
    """
    if not text or not text.strip():
        return text
    t = text.strip()

    # --- 去掉开头的非创作内容 ---
    # 按空行分段，逐段检查
    paragraphs = re.split(r'\n\s*\n', t)
    
    # 非创作内容的关键词（出现在段落里就跳过该段）
    noise_keywords = [
        'claude', 'anthropic', "i'm ", 'i am ', 'i need to',
        'i notice', 'i appreciate', 'i can help', "i'll ",
        'i also notice', 'social engineering', 'preamble',
        'injection', 'roleplay', 'identity', 'guidelines',
        'clarify', 'direct with you', 'transparent',
        'that said', 'here is the', "here's the",
        '我是claude', '由anthropic', '我注意到', '需要澄清',
        '身份指令', '相互矛盾', '我不会按照',
        '我可以帮你', '我可以帮助', '关于你的',
        # 云雾/Claude 等开启 thinking 时，思考内容有时被误放入 content，需过滤
        'thinking about the user', 'thinking about your request',
    ]
    
    start_para = 0
    for i, para in enumerate(paragraphs):
        para_lower = para.strip().lower()
        # 空段或分隔线跳过
        if not para_lower or para_lower == '---':
            start_para = i + 1
            continue
        # 包含噪音关键词的段落跳过
        if any(kw in para_lower for kw in noise_keywords):
            start_para = i + 1
            continue
        # 遇到干净的段落，停止
        break
    
    if start_para > 0 and start_para < len(paragraphs):
        t = '\n\n'.join(paragraphs[start_para:]).strip()
    
    # 去掉开头的 "---" 分隔线
    t = re.sub(r'^---\s*\n*', '', t).strip()

    # --- 去掉结尾的反问/邀请 ---
    # 从最后往前扫描，去掉包含反问/邀请的段落
    paragraphs = re.split(r'\n\s*\n', t)
    end_para = len(paragraphs)
    
    tail_keywords = [
        '需要我', '要我', '希望我', '如果你', '你觉得',
        '怎么样', '如何', '请告诉', '让我知道',
        'want me', 'would you', 'shall i', 'let me know',
        'if you', 'happy to',
    ]
    
    for i in range(len(paragraphs) - 1, max(len(paragraphs) - 3, -1), -1):
        para_lower = paragraphs[i].strip().lower()
        if not para_lower or para_lower == '---':
            end_para = i
            continue
        if any(kw in para_lower for kw in tail_keywords):
            end_para = i
            continue
        break
    
    if end_para < len(paragraphs):
        t = '\n\n'.join(paragraphs[:end_para]).strip()
    
    # 去掉结尾的 "---" 分隔线
    t = re.sub(r'\n*---\s*$', '', t).strip()

    return t


# Claude 结构化输出 Beta 标头
CLAUDE_STRUCTURED_OUTPUT_BETA = "structured-outputs-2025-11-13"


_YUNWU_PROVIDERS = frozenset({
    LLMProvider.WLAI, LLMProvider.GEMINI,
    LLMProvider.GROK, LLMProvider.GROK42,
})


class LLMClient:
    """LLM客户端，支持多种模型后端"""
    
    def __init__(self):
        self._client: Optional[OpenAI] = None
        self._httpx_client: Optional[httpx.Client] = None
        self._client_key: str = ""
        self._client_url: str = ""

    @property
    def config(self):
        """每次动态读取全局 config，确保 set_config 后立即生效"""
        return get_config().llm

    @property
    def client(self) -> OpenAI:
        """获取OpenAI兼容客户端，api_key/base_url 变化时自动重建"""
        active_config = self.config.get_active_config()
        cur_key = active_config.get("api_key", "")
        cur_url = active_config.get("base_url", "")
        if self._client is None or cur_key != self._client_key or cur_url != self._client_url:
            self._client = OpenAI(
                api_key=cur_key,
                base_url=cur_url or None,
                timeout=300.0,
                max_retries=2
            )
            self._client_key = cur_key
            self._client_url = cur_url
        return self._client
    
    @property
    def httpx_client(self) -> httpx.Client:
        """获取 httpx 客户端（用于 Claude 原生 API 调用）"""
        if self._httpx_client is None:
            self._httpx_client = httpx.Client(timeout=300.0)
        return self._httpx_client
    
    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ):
        """
        发送对话请求（流式）
        
        Args:
            messages: 消息列表，格式为 [{"role": "user/assistant/system", "content": "..."}]
            temperature: 温度参数
            max_tokens: 最大token数
        
        Yields:
            str: 每个生成的文本片段
        """
        active_config = self.config.get_active_config()
        max_tok = max_tokens or active_config.get("max_tokens") or self.config.max_tokens
        
        final_msgs = _merge_system_to_user(messages) if self.config.provider in _YUNWU_PROVIDERS else messages
        
        kwargs = {
            "model": active_config["model"],
            "messages": final_msgs,
            "temperature": temperature if temperature is not None else self.config.temperature,
            "max_tokens": max_tok,
            "stream": True
        }
        
        try:
            stream = self.client.chat.completions.create(**kwargs)
            for chunk in stream:
                if not chunk.choices:
                    continue
                first = chunk.choices[0]
                delta = getattr(first, "delta", None)
                if not delta:
                    continue
                # 只取正文 content，不取 reasoning_content（Grok 等接口会单独返回 thinking）
                content = getattr(delta, "content", None)
                if content:
                    yield content
        except Exception as e:
            _wrap_llm_error(e, timeout_seconds=300.0)
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False
    ) -> str:
        """
        发送对话请求
        
        Args:
            messages: 消息列表，格式为 [{"role": "user/assistant/system", "content": "..."}]
            temperature: 温度参数
            max_tokens: 最大token数
            json_mode: 是否启用JSON模式
        
        Returns:
            模型回复文本
        """
        active_config = self.config.get_active_config()
        max_tok = max_tokens or active_config.get("max_tokens") or self.config.max_tokens
        
        final_msgs = _merge_system_to_user(messages) if self.config.provider in _YUNWU_PROVIDERS else messages
        
        kwargs = {
            "model": active_config["model"],
            "messages": final_msgs,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tok,
        }
        
        if json_mode:
            # Grok 模型不支持 response_format 参数，改为在 prompt 中强调 JSON 输出
            if self.config.provider in (LLMProvider.GROK, LLMProvider.GROK42):
                # 不设 response_format，在最后一条 user message 末尾追加 JSON 提示
                _json_hint = "\n\n【重要】请只输出合法的 JSON，不要输出任何其他文字、解释或 markdown 代码块。"
                if kwargs["messages"] and kwargs["messages"][-1]["role"] == "user":
                    kwargs["messages"] = [m.copy() for m in kwargs["messages"]]
                    kwargs["messages"][-1]["content"] += _json_hint
            else:
                kwargs["response_format"] = {"type": "json_object"}
        
        # 云雾 API 支持 thinking 参数（WLAI/Gemini/Grok）
        if active_config.get("thinking_enabled") and self.config.provider in (LLMProvider.WLAI, LLMProvider.GEMINI, LLMProvider.GROK, LLMProvider.GROK42):
            kwargs["extra_body"] = {
                "thinking": {
                    "type": "enabled",
                    "budget_tokens": active_config.get("thinking_budget_tokens", 10240),
                }
            }
        timeout_sec = 300.0
        try:
            response = self.client.chat.completions.create(**kwargs)
            if not response.choices:
                raise ValueError("API 返回空 choices，无有效回复")
            msg = response.choices[0].message
            # 只取正文 content，不合并 reasoning_content（Grok 等接口可能单独返回 thinking）
            content = getattr(msg, "content", None) or ""
            # 云雾 API bug：Grok 的 reasoning_content 可能被拼到 content 开头，用字段精确剥离
            reasoning = getattr(msg, "reasoning_content", None) or ""
            if reasoning:
                content = _strip_thinking_from_content(content, reasoning)
            return content
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            _wrap_llm_error(e, timeout_seconds=timeout_sec)
        except Exception as e:
            # OpenAI SDK 可能抛出的超时/连接错误
            err_name = type(e).__name__
            if err_name in ("APITimeoutError", "APIConnectionError", "TimeoutError") or "timeout" in str(e).lower() or "timed out" in str(e).lower():
                _wrap_llm_error(e, timeout_seconds=timeout_sec)
            raise
    
    def chat_with_system(
        self,
        system_prompt: str,
        user_message: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False
    ) -> str:
        """
        使用系统提示词和用户消息进行对话
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        return self.chat(messages, temperature, max_tokens, json_mode)
    
    def chat_json(
        self,
        system_prompt: str,
        user_message: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        获取JSON格式的回复（带智能修复和调试）
        """
        response = self.chat_with_system(
            system_prompt,
            user_message,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=True
        )
        
        # 打印原始响应（用于调试）
        print("\n" + "=" * 80)
        print("【LLM原始JSON响应】")
        print("=" * 80)
        print(f"长度：{len(response)}字符")
        print("-" * 80)
        print(response)
        print("=" * 80 + "\n")
        
        try:
            # 使用智能修复工具
            return safe_json_loads(response, max_attempts=3)
        except (ValueError, json.JSONDecodeError) as e:
            # 保存调试信息
            debug_dir = "output/debug"
            os.makedirs(debug_dir, exist_ok=True)
            timestamp = int(time.time())
            debug_file = os.path.join(debug_dir, f"json_error_{timestamp}.txt")
            
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(f"时间：{time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"错误：{e}\n\n")
                f.write(f"原始响应（{len(response)}字符）：\n")
                f.write("=" * 60 + "\n")
                f.write(response)
                f.write("\n" + "=" * 60 + "\n")
            
            print(f"[LLM] ❌ JSON解析失败，调试信息已保存到：{debug_file}")
            print(f"[LLM] ❌ 错误详情：{str(e)}")
            
            # 重新抛出更清晰的错误
            raise ValueError(
                f"LLM返回的JSON格式无效：{str(e)[:100]}。"
                f"详细信息已保存到：{debug_file}"
            ) from e
    
    def chat_json_with_schema(
        self,
        system_prompt: str,
        user_message: str,
        json_schema: Dict[str, Any],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        使用 Claude 结构化输出获取 JSON 响应（约束解码，保证格式正确）
        
        参考文档：https://platform.claude.com/docs/zh-CN/build-with-claude/structured-outputs
        
        特点：
        - 使用约束解码（Constrained Decoding），从生成阶段就保证格式
        - 不需要后处理修复
        - 支持复杂嵌套结构
        
        Args:
            system_prompt: 系统提示词
            user_message: 用户消息
            json_schema: JSON Schema 定义（必须符合 Claude 的限制）
            temperature: 温度参数
            max_tokens: 最大输出 token 数
        
        Returns:
            解析后的 JSON 字典
        
        Raises:
            ValueError: 如果 API 调用失败或返回无效响应
        
        注意：
        - json_schema 必须设置 additionalProperties: False
        - 首次使用特定 schema 时会有额外延迟（语法编译）
        - 如果输出被截断（stop_reason: max_tokens），可能返回不完整 JSON
        """
        active_config = self.config.get_active_config()
        max_tok = max_tokens or active_config.get("max_tokens") or self.config.max_tokens
        
        # 使用云雾 API 或 Anthropic API
        api_key = active_config["api_key"]
        base_url = active_config.get("base_url", "https://api.anthropic.com")
        model = active_config["model"]
        
        # 构建请求
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "anthropic-beta": CLAUDE_STRUCTURED_OUTPUT_BETA,  # 结构化输出 beta 标头
        }
        
        # OpenAI 兼容 API（云雾/Gemini/Grok）使用 Bearer 认证
        use_openai_format = (
            "yunwu" in base_url
            or self.config.provider == LLMProvider.WLAI
            or self.config.provider == LLMProvider.GEMINI
            or self.config.provider == LLMProvider.GROK
            or self.config.provider == LLMProvider.GROK42
        )
        if use_openai_format:
            headers["Authorization"] = f"Bearer {api_key}"
        
        # 构建请求体
        request_body = {
            "model": model,
            "max_tokens": max_tok,
            "temperature": temperature or self.config.temperature,
            "messages": [
                {"role": "user", "content": user_message}
            ],
            "system": system_prompt,
            "output_format": {
                "type": "json_schema",
                "schema": json_schema
            }
        }
        
        # 云雾 API 支持 thinking 参数（WLAI/Gemini/Grok 均走云雾）
        if active_config.get("thinking_enabled") and self.config.provider in (LLMProvider.WLAI, LLMProvider.GEMINI, LLMProvider.GROK, LLMProvider.GROK42):
            request_body["thinking"] = {
                "type": "enabled",
                "budget_tokens": active_config.get("thinking_budget_tokens", 10240),
            }
        
        print("\n" + "=" * 80)
        print("【结构化输出请求】")
        print("=" * 80)
        print(f"模型：{model}")
        print(f"Schema：{json_schema.get('properties', {}).keys() if isinstance(json_schema.get('properties'), dict) else 'N/A'}")
        print(f"max_tokens：{max_tok}")
        print("=" * 80 + "\n")
        
        # 发送请求
        try:
            # 确定 API 端点
            if use_openai_format:
                # 云雾/Gemini/Grok 使用 OpenAI 兼容格式
                # base_url 已包含 /v1，直接拼 /chat/completions
                stripped = base_url.rstrip('/')
                if stripped.endswith('/v1'):
                    url = stripped + '/chat/completions'
                else:
                    url = stripped + '/v1/chat/completions'
                # 转换为 OpenAI 格式，system 合并到 user 避免云雾注入冲突
                raw_msgs = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
                merged_msgs = _merge_system_to_user(raw_msgs)
                openai_body = {
                    "model": model,
                    "max_tokens": max_tok,
                    "temperature": temperature or self.config.temperature,
                    "messages": merged_msgs,
                }
                # Grok 不支持 response_format，改为在 prompt 中强调 JSON 输出
                if self.config.provider in (LLMProvider.GROK, LLMProvider.GROK42):
                    _json_hint = "\n\n【重要】请严格按上面要求的 JSON 格式输出，不要输出任何其他文字、解释或 markdown 代码块。"
                    openai_body["messages"][-1]["content"] += _json_hint
                else:
                    openai_body["response_format"] = {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "structured_output",
                            "strict": True,
                            "schema": json_schema
                        }
                    }
                # 云雾 API 支持 thinking 参数（WLAI/Gemini/Grok）
                if active_config.get("thinking_enabled") and self.config.provider in (LLMProvider.WLAI, LLMProvider.GEMINI, LLMProvider.GROK, LLMProvider.GROK42):
                    openai_body["extra_body"] = {
                        "thinking": {
                            "type": "enabled",
                            "budget_tokens": active_config.get("thinking_budget_tokens", 10240),
                        }
                    }

                response = self.httpx_client.post(
                    url,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}",
                    },
                    json=openai_body,
                    timeout=300.0
                )
            else:
                # Anthropic 原生 API
                url = f"{base_url}/v1/messages"
                response = self.httpx_client.post(
                    url,
                    headers=headers,
                    json=request_body,
                    timeout=300.0
                )
            
            response.raise_for_status()
            result = response.json()
            
            # 防御：API 返回非 dict（如 HTML 错误页面被解析成字符串）
            if not isinstance(result, dict):
                raise ValueError(f"API 返回非预期格式（{type(result).__name__}），原始内容：{str(result)[:200]}")

            # 解析响应
            if "choices" in result:
                # OpenAI 格式响应（云雾 API）
                choices = result.get("choices") or []
                if not choices:
                    raise ValueError("API 返回空 choices，无有效回复")
                msg_data = choices[0].get("message", {})
                content = msg_data.get("content") or ""
                # 云雾 API bug：Grok 的 reasoning_content 可能被拼到 content 开头，用字段精确剥离
                reasoning = msg_data.get("reasoning_content") or ""
                if reasoning:
                    content = _strip_thinking_from_content(content, reasoning)
                stop_reason = choices[0].get("finish_reason", "")
            elif "content" in result:
                # Anthropic 格式响应
                content_blocks = result.get("content") or []
                if not isinstance(content_blocks, list):
                    content_blocks = []
                content = ""
                for block in content_blocks:
                    if block.get("type") == "text":
                        content = block.get("text", "")
                        break
                stop_reason = result.get("stop_reason", "")
            else:
                raise ValueError(f"无法解析响应格式：{result}")
            
            print("\n" + "=" * 80)
            print("【结构化输出响应】")
            print("=" * 80)
            print(f"stop_reason：{stop_reason}")
            print(f"响应长度：{len(content)}字符")
            print("-" * 80)
            # 截断显示
            if len(content) > 1000:
                print(content[:500])
                print(f"\n... [省略{len(content)-1000}字符] ...\n")
                print(content[-500:])
            else:
                print(content)
            print("=" * 80 + "\n")
            
            # 检查是否被截断
            if stop_reason == "max_tokens":
                print("[LLM] ⚠️ 警告：输出被截断（max_tokens），JSON 可能不完整")
            
            # 检查是否拒绝
            if stop_reason == "refusal":
                raise ValueError(f"Claude 拒绝了请求：{content}")
            
            # 解析 JSON（先预处理清理markdown标记）
            clean_content = content.strip()
            # 去除可能的 ```json 和 ``` 包裹
            if clean_content.startswith("```"):
                first_newline = clean_content.find('\n')
                if first_newline > 0:
                    clean_content = clean_content[first_newline+1:]
                else:
                    clean_content = clean_content[3:]
            if clean_content.endswith("```"):
                clean_content = clean_content[:-3]
            clean_content = clean_content.strip()
            
            try:
                return json.loads(clean_content)
            except json.JSONDecodeError as e:
                # 如果结构化输出仍然解析失败，尝试修复
                print(f"[LLM] ⚠️ 结构化输出解析失败，尝试修复：{str(e)[:100]}")
                return safe_json_loads(content, max_attempts=3)
                
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            _wrap_llm_error(e, timeout_seconds=300.0)
        except httpx.HTTPStatusError as e:
            error_body = e.response.text
            print(f"[LLM] ❌ API 错误：{e.response.status_code}", file=sys.stderr, flush=True)
            print(f"[LLM] ❌ 错误详情：{error_body[:500]}", file=sys.stderr, flush=True)
            
            # 如果是 schema 错误，给出提示
            if "schema" in error_body.lower():
                raise ValueError(
                    f"JSON Schema 可能不符合 Claude 的要求：{error_body[:200]}\n"
                    "请检查：1) additionalProperties 必须为 false；2) 不支持递归；3) 不支持数值约束"
                ) from e
            raise ValueError(f"API 调用失败：{error_body[:200]}") from e
        except Exception as e:
            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                _wrap_llm_error(e, timeout_seconds=300.0)
            print(f"[LLM] ❌ 请求失败：{type(e).__name__}: {str(e)[:200]}", file=sys.stderr, flush=True)
            raise


# 线程隔离的 LLM 客户端：每个任务线程有独立实例，避免并发时 config/api_key 互相覆盖
from contextvars import ContextVar as _LLMContextVar
_llm_client_var: _LLMContextVar[Optional[LLMClient]] = _LLMContextVar('_llm_client_var', default=None)


def get_llm_client() -> LLMClient:
    """获取当前线程/任务的 LLMClient 实例（懒创建，线程隔离）"""
    client = _llm_client_var.get(None)
    if client is None:
        client = LLMClient()
        _llm_client_var.set(client)
    return client


def reset_llm_client():
    """重置当前线程/任务的 LLMClient，下次 get_llm_client 时会按最新 config 重建"""
    _llm_client_var.set(None)
