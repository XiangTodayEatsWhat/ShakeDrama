"""
剧本校验工具 - 纯算法校验字数、场面数，不依赖AI
"""
import re
from typing import Tuple, List


def count_script_chars(text: str) -> int:
    """
    统计剧本正文字数（纯算法）。
    规则：中文字符、英文/数字字符各计1，标点空格不计。
    """
    if not text or not text.strip():
        return 0
    total = 0
    for char in text:
        if '\u4e00' <= char <= '\u9fff':
            total += 1
        elif char.isalnum():
            total += 1
    return total


def count_script_chars_cn_only(text: str) -> int:
    """
    仅统计中文字符数（不含标点、英文、数字）。
    短剧剧本以中文为主，用此更符合「500-700字」的直觉。
    """
    if not text:
        return 0
    return sum(1 for c in text if '\u4e00' <= c <= '\u9fff')


def count_script_chars_include_punctuation(text: str) -> int:
    """
    统计总字符数（含标点、空格，不含换行符）。
    与 Word 的「字数/字符数」对齐：换行符不计入，避免统计偏大。
    """
    if not text:
        return 0
    t = text.replace("\r", "").replace("\n", "").strip()
    return len(t)


def get_episode_word_count(script_text: str, mode: str = "cn_only") -> int:
    """
    获取单集剧本字数。
    mode: "cn_only" 仅中文 | "no_punct" 中英文数字 | "all" 总字符
    """
    if mode == "cn_only":
        return count_script_chars_cn_only(script_text)
    if mode == "all":
        return count_script_chars_include_punctuation(script_text)
    return count_script_chars(script_text)


def count_scene_headers(script_text: str, episode_num: int) -> List[Tuple[int, int]]:
    """
    解析剧本中的场景头，统计本集场面数。
    场景头格式：
    - 标准格式：{episode}-{scene} 地点 时间 内/外（例如：1-1 客厅 日 内）
    - Markdown格式：## {episode}-{scene} 地点 时间 内/外（例如：## 1-1 客厅 日 内）
    返回本集出现的 (episode, scene_number) 列表。
    """
    if not script_text or episode_num < 1:
        return []
    # 匹配 数字-数字 开头的行（支持 ## 前缀，可能有空格）
    # 改进：支持 markdown 格式的 ## 前缀
    pattern = re.compile(r"^\s*(?:##\s*)?(\d+)\s*-\s*(\d+)\s+", re.MULTILINE)
    found = []
    for m in pattern.finditer(script_text):
        ep, sc = int(m.group(1)), int(m.group(2))
        if ep == episode_num and (ep, sc) not in found:
            found.append((ep, sc))
    return found


def get_episode_scene_count(script_text: str, episode_num: int) -> int:
    """本集场面数（1-1, 1-2, 1-3 等）。"""
    return len(count_scene_headers(script_text, episode_num))


def get_first_scene_and_rest(script_text: str, episode_num: int):
    """
    把剧本拆成「第一场戏」和「其余」。
    第一场戏：从开头到第二个场景头（## N-2 或 N-2）之前，用于衔接修正。
    返回 (first_scene_text, rest_text)。
    """
    if not script_text or episode_num < 1:
        return script_text, ""
    lines = script_text.split("\n")
    pattern = re.compile(r"^\s*(?:##\s*)?(\d+)\s*-\s*(\d+)\s+")
    first_scene_end_idx = None
    count = 0
    for i, line in enumerate(lines):
        m = pattern.match(line.strip() if line else "")
        if m and int(m.group(1)) == episode_num and int(m.group(2)) >= 1:
            count += 1
            if count == 2:
                first_scene_end_idx = i
                break
    if first_scene_end_idx is None:
        # 只有一场或没匹配到，取前 25 行作为「开头」参与衔接
        first_scene_end_idx = min(25, len(lines))
    first_scene = "\n".join(lines[:first_scene_end_idx]).rstrip()
    rest = "\n".join(lines[first_scene_end_idx:]).lstrip()
    return first_scene, rest


def check_episode_word_count(
    script_text: str,
    min_chars: int = 500,
    max_chars: int = 700,
    mode: str = "no_punct",
) -> Tuple[bool, int, str]:
    """
    校验单集字数是否在 [min_chars, max_chars]。
    mode: "no_punct" 汉字+字母+数字（与 Word 字数一致，默认）| "cn_only" 仅中文 | "all" 总字符
    返回 (是否通过, 当前字数, 说明)。
    """
    if mode == "all":
        n = count_script_chars_include_punctuation(script_text)
    elif mode == "cn_only":
        n = count_script_chars_cn_only(script_text)
    else:
        n = count_script_chars(script_text)  # no_punct: 汉字+字母+数字
    if n < min_chars:
        return False, n, f"字数不足：{n}字（要求{min_chars}-{max_chars}字）"
    if n > max_chars:
        return False, n, f"字数超标：{n}字（要求{min_chars}-{max_chars}字）"
    return True, n, f"字数合格：{n}字"


def check_episode_scene_count(script_text: str, episode_num: int, max_scenes: int = 3) -> Tuple[bool, int, str]:
    """
    校验本集场面数是否不超过 max_scenes（默认3）。
    返回 (是否通过, 当前场面数, 说明)。
    """
    scenes = count_scene_headers(script_text, episode_num)
    n = len(scenes)
    if n > max_scenes:
        return False, n, f"场面过多：{n}个（最多{max_scenes}个，仅允许{episode_num}-1、{episode_num}-2、{episode_num}-3）"
    return True, n, f"场面数合格：{n}个"


def get_episode_action_lines(script_text: str) -> List[str]:
    """
    提取本集中所有以 △ 开头的行，返回每条△后的内容（去掉△及前导空格）。
    """
    if not script_text:
        return []
    lines = []
    for line in script_text.splitlines():
        s = line.strip()
        if s.startswith("△"):
            content = s[1:].lstrip()  # 去掉 △ 及紧跟的空格
            lines.append(content)
    return lines


def check_episode_action_markers(
    script_text: str,
    max_count: int = 15,
    max_chars_per_line: int = 25,
) -> Tuple[bool, int, int, str]:
    """
    校验三角号△：个数不超过 max_count，每条△后描述字数不超过 max_chars_per_line（按汉字+字母+数字计）。
    返回 (是否通过, △个数, 超标的那条字数（0表示无）, 说明)。
    """
    action_lines = get_episode_action_lines(script_text)
    n = len(action_lines)
    max_found = 0
    for content in action_lines:
        c = count_script_chars(content)
        if c > max_found:
            max_found = c
    issues = []
    if n > max_count:
        issues.append(f"△过多：{n}处（最多{max_count}处）")
    if max_found > max_chars_per_line:
        issues.append(f"△描述过长：最长{max_found}字（每条最多{max_chars_per_line}字）")
    if issues:
        return False, n, max_found, "；".join(issues)
    return True, n, max_found, f"△合格：{n}处，单条≤{max_chars_per_line}字"


# 场景头行：## 1-1 或 1-1 开头
_SCENE_HEADER_RE = re.compile(r"^\s*(?:##\s*)?\d+\s*-\s*\d+")


def remove_separator_lines(script_text: str) -> str:
    """
    生成后处理：去掉剧本中的 --- 分隔符行（模型常出的场景分隔），避免进入后续校验与定稿。
    """
    if not script_text or not script_text.strip():
        return script_text
    lines = [line for line in script_text.split("\n") if line.strip() != "---"]
    return "\n".join(lines)


def _is_dialogue_line(line: str) -> bool:
    """判断是否为「xxx：」对话行（角色名+冒号，支持中英文冒号）。"""
    s = line.strip()
    for sep in ("：", ":"):
        if sep in s:
            before_colon = s.split(sep, 1)[0].strip()
            # 角色名一般较短，且可能带（OS）、VO 等，长度放宽到 25
            if len(before_colon) <= 25 and before_colon != "":
                return True
    return False


def ensure_action_triangles(script_text: str) -> str:
    """
    后处理：在所有检查都通过后，对当前剧本中「非对话行」统一加三角号△。
    规则：每一行只要不是「xxx：」这种对话行，且不是空行/场景头/人物列表，就在前面加上△。
    用于最终定稿，避免重写时漏掉△导致格式不一致。
    会先去掉 --- 分隔符行。
    """
    if not script_text or not script_text.strip():
        return script_text
    script_text = remove_separator_lines(script_text)
    lines = script_text.split("\n")
    out = []
    for line in lines:
        s = line.strip()
        if not s:
            out.append(line)
            continue
        if s.startswith("△"):
            out.append(line)
            continue
        if _SCENE_HEADER_RE.match(s):
            out.append(line)
            continue
        if s.startswith("人物："):
            out.append(line)
            continue
        if s == "---":
            out.append(line)
            continue  # 分隔符，前面已 remove_separator_lines，此处兜底不自动加△
        if _is_dialogue_line(line):
            out.append(line)
            continue
        # 其余视为动作/描写行，前面加△（保留行首缩进则用 strip 再补△）
        out.append("△ " + s)
    return "\n".join(out)


def check_action_triangles_present(script_text: str) -> Tuple[bool, str]:
    """
    算法检查：非对话、非场景头、非空行、非「人物：」的行是否都带有三角号△。
    用于审稿时判断「三角号加没加」。
    返回 (是否通过, 说明)。
    """
    if not script_text or not script_text.strip():
        return True, "无内容"
    lines = script_text.split("\n")
    for i, line in enumerate(lines):
        s = line.strip()
        if not s:
            continue
        if s.startswith("△"):
            continue
        if _SCENE_HEADER_RE.match(s):
            continue
        if s.startswith("人物："):
            continue
        if s == "---":
            continue  # 分隔符，后处理会去掉，此处不严格报错
        if _is_dialogue_line(line):
            continue
        # 非对话、非场景头、非人物列表 → 应为动作行，必须有△
        content_preview = s if len(s) <= 60 else s[:60] + "..."
        return False, f"第{i+1}行应为动作描写，需在行首加△。该行内容：「{content_preview}」"
    return True, "三角号格式合格"


def check_scene_followed_by_character_line(script_text: str, episode_num: int) -> Tuple[bool, str]:
    """
    算法检查：每个场景头（如 1-1 客厅 日 内）后面是否有人物/对话行（角色：台词 或 人物：xxx）。
    用于审稿时判断「场景下面写没写人物：xxx 或 角色：台词」。
    返回 (是否通过, 说明)。
    """
    if not script_text or not script_text.strip():
        return True, "无内容"
    lines = script_text.split("\n")
    in_scene = False
    scene_has_dialogue = False
    last_scene_start = 0   # 上一场景头所在行号（1-based）
    last_scene_header = ""  # 上一场景头内容
    for i, line in enumerate(lines):
        s = line.strip()
        if not s:
            continue
        if _SCENE_HEADER_RE.match(s):
            if in_scene and not scene_has_dialogue:
                return False, f"第{last_scene_start}行场景「{last_scene_header[:50]}{'...' if len(last_scene_header) > 50 else ''}」下缺少人物/对话行（应有「角色名：台词」或「人物：xxx」）"
            in_scene = True
            scene_has_dialogue = False
            last_scene_start = i + 1
            last_scene_header = s
            continue
        if in_scene:
            if s.startswith("人物：") or _is_dialogue_line(line):
                scene_has_dialogue = True
    if in_scene and not scene_has_dialogue:
        return False, f"最后一场景（第{last_scene_start}行「{last_scene_header[:50]}{'...' if len(last_scene_header) > 50 else ''}」）下缺少人物/对话行（应有「角色名：台词」或「人物：xxx」）"
    return True, "场景下人物/对话格式合格"


def is_mostly_english(script_text: str, ratio_threshold: float = 0.5) -> bool:
    """
    判断剧本是否「过半英文」，用于检测输出崩盘（整段乱答/英文）。
    只统计字母与中文，若英文字母占比超过 ratio_threshold 则视为崩盘。
    """
    if not script_text or not script_text.strip():
        return False
    letters_en = sum(1 for c in script_text if c.isascii() and c.isalpha())
    letters_cn = sum(1 for c in script_text if "\u4e00" <= c <= "\u9fff")
    total = letters_en + letters_cn
    if total == 0:
        return False
    return (letters_en / total) > ratio_threshold


def run_algorithm_checks(
    script_text: str,
    episode_num: int,
    max_scenes: int = 3,
) -> Tuple[bool, List[str]]:
    """
    除字数外所有算法检查，用于「边写边审」：场景数、英文、Meta、三角号、场景下人物行、对话冒号。
    返回 (是否通过, 不通过时的问题列表，用于重写提示)。
    """
    issues: List[str] = []

    # 场景数
    scene_ok, scene_count, scene_msg = check_episode_scene_count(
        script_text, episode_num, max_scenes=max_scenes
    )
    if not scene_ok:
        issues.append(scene_msg)

    # 英文
    english_pattern = re.compile(r"\b[a-zA-Z]{2,}\b")
    english_words = english_pattern.findall(script_text)
    exclude = {"OS", "VO", "BGM", "SFX", "POV", "CUT", "FADE", "INT", "EXT"}
    english_words = [w for w in english_words if w.upper() not in exclude]
    if english_words:
        issues.append(f"剧本中有英文：{', '.join(english_words[:5])}，必须改成中文")

    # Meta
    meta_patterns = [
        r"——第\d+集完——",
        r"【字数[约]?\d+字?】",
        r"【节奏[^\]]*】",
        r"【本集完】",
        r"第\d+集完",
        r"\(完\)",
        r"（完）",
        r"（剧终）",
        r"\(剧终\)",
        r"【剧终】",
        r"剧终",
    ]
    meta_found = []
    for pattern in meta_patterns:
        meta_found.extend(re.findall(pattern, script_text))
    if meta_found:
        issues.append(f"剧本中有 meta 信息：{', '.join(meta_found[:3])}，必须删除")

    # 三角号
    triangle_ok, triangle_msg = check_action_triangles_present(script_text)
    if not triangle_ok:
        issues.append(triangle_msg)

    # 场景下人物/对话行
    scene_char_ok, scene_char_msg = check_scene_followed_by_character_line(
        script_text, episode_num
    )
    if not scene_char_ok:
        issues.append(scene_char_msg)

    # 对话冒号统一中文
    dialogue_lines = [
        line.strip()
        for line in script_text.split("\n")
        if line.strip()
        and not line.strip().startswith("△")
        and not line.strip().startswith("【")
        and not re.match(r"^\d+-\d+", line.strip())
    ]
    colon_lines = [line for line in dialogue_lines if "：" in line or ":" in line]
    mixed_colon = any(":" in line and "：" not in line for line in colon_lines)
    if mixed_colon:
        issues.append("对话格式不统一：应使用中文冒号「：」而非英文冒号「:」")

    passed = len(issues) == 0
    return passed, issues
