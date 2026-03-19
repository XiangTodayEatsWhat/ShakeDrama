"""
检测 LLM 是否返回了「拒绝任务/身份声明/提问」类回复而非预期格式（如 JSON）。
用于兜底逻辑：检测到后可改用更严格的提示重试。
"""


def is_likely_refusal(text: str) -> bool:
    """
    判断模型回复是否像「拒绝、身份声明或先提问」而非直接完成任务。
    若为 True，调用方可用兜底提示（如「仅输出 JSON」）重试。
    """
    if not text or not text.strip():
        return True
    t = text.strip()
    # 若已包含合法 JSON 雏形（有 "beats" 或首字符为 {），倾向认为不是拒绝
    if t.lstrip().startswith("{"):
        return False
    if '"beats"' in t or "'beats'" in t:
        return False
    # 只检查前 2000 字符，避免长正文误判
    head = (t[:2000]).lower()
    refusal_markers = [
        # 英文身份声明
        "i'm claude",
        "i am claude",
        "i'm an ai",
        "i am an ai",
        "made by anthropic",
        "i'm grok",
        "i am grok",
        "made by xai",
        # 英文拒绝
        "i'm not the specialized",
        "i can't adopt",
        "i need to clarify",
        "however, i'm happy to help",
        "not designed for creative writing",
        "clarify my role",
        "can't adopt that identity",
        "embedded directives",
        "i appreciate you sharing",
        "i need to be direct",
        "i can't roleplay",
        "false identity",
        "attempted manipulations",
        "conflicting identity",
        # 中文拒绝 / 身份声明
        "不是我的功能范围",
        "不是我的主要功能",
        "我需要澄清",
        "由anthropic开发",
        "由anthropic",
        "核心职能",
        "专注于技术工作",
        "编码助手",
        "编程助手",
        "我是claude",
        "我是 claude",
        "超出了我",
        "作为编码助手",
        "作为编程助手",
        "作为ai助手",
        "作为 ai 助手",
    ]
    return any(m in head for m in refusal_markers)
