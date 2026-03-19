"""
JSON修复工具
用于修复LLM输出的常见JSON格式错误
"""
import json
import re
from typing import Any, Dict, List, Tuple


def fix_json(text: str) -> str:
    """
    修复常见的JSON格式错误
    
    Args:
        text: 可能包含错误的JSON文本
    
    Returns:
        修复后的JSON文本
    """
    # 1. 去除markdown代码块标记（更健壮的处理）
    text = text.strip()
    
    # 处理 ```json 或 ``` 开头（可能有前导空白）
    # 使用正则匹配更灵活
    text = re.sub(r'^```(?:json)?\s*\n?', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n?```\s*$', '', text, flags=re.MULTILINE)
    
    # 再次strip确保干净
    text = text.strip()
    
    # 如果还是以```开头或结尾，再处理一次
    if text.startswith("```"):
        first_newline = text.find('\n')
        if first_newline > 0:
            text = text[first_newline+1:]
        else:
            text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    # 2. 移除注释（// 和 /* */）
    text = re.sub(r'//.*?$', '', text, flags=re.MULTILINE)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    
    # 3. 修复数组/对象末尾的多余逗号
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    
    # 4. 修复单引号（改为双引号）
    # 注意：这可能会误修复字符串内容中的单引号
    # 所以只在键名位置替换
    text = re.sub(r"'([^']*?)'(\s*:)", r'"\1"\2', text)
    
    # 5. 移除控制字符
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    
    # 5.5 转义字符串值内部未转义的双引号（如 "室友"周远"" -> "室友\"周远\""）
    text = _escape_inner_double_quotes(text)
    
    # 6. 修复缺少闭合括号的情况（如 "...",\n{ 应该是 "..."},\n{）
    # 这种情况通常是对象末尾少了 }
    text = re.sub(r'(")\s*,(\s*\{)', r'\1},\2', text)
    
    # 7. 修复缺少逗号分隔符的情况
    # 例如: "key1": "value1"\n    "key2" 应该是 "key1": "value1",\n    "key2"
    # 模式1: 字符串值后面直接跟新的键 "value"\n"key"
    text = re.sub(r'(")\s*\n(\s*")', r'\1,\n\2', text)
    # 模式2: 数字/布尔值后面直接跟新的键
    text = re.sub(r'(\d|true|false|null)\s*\n(\s*")', r'\1,\n\2', text)
    # 模式3: }或]后面直接跟新的键或{或[
    text = re.sub(r'([}\]])\s*\n(\s*["{[\[])', r'\1,\n\2', text)
    
    # 8. 修复未闭合的字符串（核心增强）
    text = _fix_unclosed_strings(text)
    
    # 9. 自动补全缺少的闭合括号
    text = _balance_brackets(text)
    
    return text


def _escape_inner_double_quotes(text: str) -> str:
    """
    转义 JSON 字符串值内部未转义的双引号。
    LLM 常会在中文等内容里写出 "名字" 导致 JSON 断在中间，例如：
    "synopsis": "室友"周远"，却发现" -> 应转为 "室友\\"周远\\"，却发现"
    """
    result = []
    i = 0
    n = len(text)
    in_string = False
    escape_next = False
    while i < n:
        char = text[i]
        if escape_next:
            result.append(char)
            escape_next = False
            i += 1
            continue
        if char == "\\":
            result.append(char)
            escape_next = True
            i += 1
            continue
        if char == '"':
            if in_string:
                # 可能是结束引号，也可能是内容里的未转义引号；看后续字符
                j = i + 1
                while j < n and text[j] in " \t\n\r":
                    j += 1
                if j >= n:
                    # 字符串结束，当前 " 是闭合引号
                    in_string = False
                    result.append(char)
                else:
                    next_char = text[j]
                    # 若下一非空字符是 , } ] : 或另一个 "（下一键开头），则当前 " 是闭合引号
                    if next_char in ',}\"]:':
                        in_string = False
                        result.append(char)
                    else:
                        # 内容里的未转义引号，转义
                        result.append('\\"')
            else:
                in_string = True
                result.append(char)
            i += 1
            continue
        result.append(char)
        i += 1
    return "".join(result)


def _fix_unclosed_strings(text: str) -> str:
    """
    修复未闭合的字符串
    
    当JSON被截断时，字符串可能没有正确闭合，例如：
    "synopsis": "苏念被沈嘉文堵在祠堂，千钧一发之际，顾衍带
    
    这个函数会尝试：
    1. 检测未闭合的字符串
    2. 在合适的位置添加闭合引号
    3. 移除不完整的数组元素或对象
    
    Args:
        text: JSON文本
    
    Returns:
        修复后的文本
    """
    # 检测是否有未闭合的字符串
    in_string = False
    escape_next = False
    last_string_start = -1
    
    for i, char in enumerate(text):
        if escape_next:
            escape_next = False
            continue
        
        if char == '\\':
            escape_next = True
            continue
        
        if char == '"':
            if in_string:
                in_string = False
            else:
                in_string = True
                last_string_start = i
    
    # 如果字符串未闭合
    if in_string and last_string_start >= 0:
        # 在末尾添加闭合引号
        # 先去掉末尾的空白字符
        text = text.rstrip()
        
        # 尝试找到一个合理的截断点
        # 查找最后一个完整的逗号分隔的元素
        # 例如: "key": "value被截断 -> 移除这个不完整的键值对
        
        # 找到未闭合字符串的开始位置
        # 然后回溯找到这个键值对/数组元素的开始
        truncate_pos = _find_truncation_point(text, last_string_start)
        
        if truncate_pos > 0:
            text = text[:truncate_pos]
            text = text.rstrip()
            # 移除末尾的逗号
            if text.endswith(','):
                text = text[:-1]
        else:
            # 如果找不到好的截断点，直接闭合字符串
            text = text + '"'
    
    return text


def _find_truncation_point(text: str, unclosed_string_start: int) -> int:
    """
    找到合理的截断点，用于移除不完整的JSON元素
    
    Args:
        text: JSON文本
        unclosed_string_start: 未闭合字符串的开始位置
    
    Returns:
        截断位置，-1表示找不到合适的截断点
    """
    # 从未闭合字符串的位置往回找
    # 找到最近的完整的数组元素或对象的结束位置
    
    # 策略1: 找到前一个 }, 或 ], 作为截断点
    search_text = text[:unclosed_string_start]
    
    # 找最后一个 }] 后面紧跟着逗号的位置
    # 例如: {"key": "value"}, {"key2": "被截断
    #                       ^-- 截断点在这里
    
    last_complete_pos = -1
    
    # 从后往前找 },  或 ],
    for i in range(len(search_text) - 1, -1, -1):
        if search_text[i] in '}]':
            # 检查后面是否有逗号
            rest = search_text[i+1:].lstrip()
            if rest.startswith(','):
                # 找到逗号的位置
                comma_pos = search_text.find(',', i+1)
                if comma_pos > 0:
                    last_complete_pos = comma_pos + 1
                    break
    
    # 策略2: 如果找不到 },  就找最近的逗号后的位置
    if last_complete_pos == -1:
        # 查找模式: "完整的值",
        # 从未闭合字符串位置往回找最近的完整键值对
        for i in range(unclosed_string_start - 1, -1, -1):
            if text[i] == ',':
                # 检查逗号前面是否是完整的值（以 " 或 } 或 ] 或数字结尾）
                before_comma = text[:i].rstrip()
                if before_comma and before_comma[-1] in '"}]0123456789':
                    last_complete_pos = i + 1
                    break
    
    return last_complete_pos


def _balance_brackets(text: str) -> str:
    """
    自动补全缺少的闭合括号
    
    Args:
        text: JSON文本
    
    Returns:
        补全后的文本
    """
    # 统计括号
    stack = []
    in_string = False
    escape_next = False
    
    for char in text:
        if escape_next:
            escape_next = False
            continue
        
        if char == '\\':
            escape_next = True
            continue
        
        if char == '"' and not in_string:
            in_string = True
        elif char == '"' and in_string:
            in_string = False
        elif not in_string:
            if char == '{':
                stack.append('}')
            elif char == '[':
                stack.append(']')
            elif char in '}]':
                if stack and stack[-1] == char:
                    stack.pop()
    
    # 补全缺少的闭合括号
    if stack:
        # 去掉末尾的逗号
        text = text.rstrip()
        if text.endswith(','):
            text = text[:-1]
        # 添加缺少的闭合括号
        text += ''.join(reversed(stack))
    
    return text


def safe_json_loads(text: str, max_attempts: int = 3) -> Dict[str, Any]:
    """
    安全地解析JSON，带自动修复和重试
    
    Args:
        text: JSON文本
        max_attempts: 最大尝试次数
    
    Returns:
        解析后的字典
    
    Raises:
        ValueError: 所有尝试都失败后抛出
    """
    last_error = None
    
    for attempt in range(max_attempts):
        try:
            if attempt == 0:
                # 第一次尝试：先应用基本修复（去除 markdown 等）
                fixed_text = fix_json(text)
                return json.loads(fixed_text)
            elif attempt == 1:
                # 第二次尝试：更激进的修复
                fixed_text = fix_json(text)
                # 尝试提取第一个完整的JSON对象
                match = re.search(r'\{.*\}', fixed_text, re.DOTALL)
                if match:
                    fixed_text = match.group(0)
                    fixed_text = fix_json(fixed_text)  # 再次应用修复
                return json.loads(fixed_text)
            else:
                # 第三次尝试：更激进地处理截断的JSON
                fixed_text = fix_json(text)
                # 尝试修复常见的数组元素缺少闭合括号问题
                # 查找 "...",\n    { 这种模式，在逗号前加 }
                fixed_text = re.sub(r'("[^"]*")\s*,(\s*\n\s*\{)', r'\1}\2', fixed_text)
                
                # 尝试移除最后一个不完整的数组元素
                fixed_text = _remove_incomplete_array_element(fixed_text)
                
                fixed_text = _balance_brackets(fixed_text)
                return json.loads(fixed_text)
            
        except json.JSONDecodeError as e:
            last_error = e
            continue
    
    # 所有尝试都失败
    if last_error:
        raise ValueError(
            f"JSON解析失败（已尝试{max_attempts}次）：{last_error}。"
            f"错误位置：第{last_error.lineno}行第{last_error.colno}列"
        ) from last_error
    
    raise ValueError("JSON解析失败：未知错误")


def _remove_incomplete_array_element(text: str) -> str:
    """
    移除数组中不完整的最后一个元素
    
    当JSON被截断时，数组的最后一个元素可能不完整，例如：
    "beats": [
        {"episode": 1, "synopsis": "完整内容"},
        {"episode": 2, "synopsis": "被截断的内容
    
    这个函数会移除最后一个不完整的元素。
    
    Args:
        text: JSON文本
    
    Returns:
        修复后的文本
    """
    # 查找数组模式，找到最后一个完整的 },
    # 检测是否在数组中（通过查找 [）
    
    # 简单策略：找到最后一个 }, 后面紧跟换行和空格的位置
    # 如果之后的内容不能形成完整的JSON对象，就截断
    
    # 找最后一个完整的数组元素的结束位置
    # 模式: }, 后面跟着换行符
    pattern = r'\}\s*,\s*\n'
    matches = list(re.finditer(pattern, text))
    
    if matches:
        last_match = matches[-1]
        # 检查 last_match 之后的内容是否是完整的JSON
        remaining = text[last_match.end():].strip()
        if remaining:
            # 尝试解析剩余部分
            # 如果剩余部分不完整（比如缺少闭合引号或括号）
            # 就截断到这个位置
            try:
                # 尝试补全并解析
                test_text = remaining
                if not test_text.endswith('}'):
                    test_text = _fix_unclosed_strings(test_text)
                    test_text = _balance_brackets(test_text)
                json.loads(test_text)
            except json.JSONDecodeError:
                # 无法解析，说明最后一个元素不完整，截断它
                # 保留到 }, 的位置（包含逗号）
                text = text[:last_match.start() + 1]  # 只保留 }
                text = text.rstrip()
    
    return text


def validate_json_schema(data: Dict[str, Any], required_fields: list) -> bool:
    """
    验证JSON是否包含必需字段
    
    Args:
        data: JSON数据
        required_fields: 必需字段列表
    
    Returns:
        是否有效
    """
    for field in required_fields:
        if '.' in field:
            # 嵌套字段
            parts = field.split('.')
            current = data
            for part in parts:
                if not isinstance(current, dict) or part not in current:
                    return False
                current = current[part]
        else:
            if field not in data:
                return False
    
    return True

