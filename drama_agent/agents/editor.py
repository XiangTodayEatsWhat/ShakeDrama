"""
审稿Agent (Editor) - 负责审核剧本质量
"""
import json
from typing import Optional, List, Dict, Any, Tuple

from .base_agent import BaseAgent
from ..models import Bible, Episode, HookType, HOOK_DEFINITIONS
from ..config import get_config
from ..utils.script_validator import (
    check_episode_word_count,
    check_episode_scene_count,
    get_episode_scene_count,
    check_action_triangles_present,
    check_scene_followed_by_character_line,
    count_script_chars_include_punctuation,
)


class EditorAgent(BaseAgent):
    """
    审稿Agent
    职责：
    1. 硬性规则校验（字数500-800、场面≤3、无矛盾、有钩子、AI味检查）
    2. 多维度打分（钩子分、爆点分、剧情分、AI味分）
    3. 全部达标才通过
    """
    
    def __init__(self):
        super().__init__("审稿Agent")
        self.config = get_config()
    
    @property
    def system_prompt(self) -> str:
        return """你是一位严格的国产短剧审稿编辑。你的职责是评估剧本质量，只关注核心问题，给出简洁可执行的重写建议。

【⚠️ 核心三要素 - 最重要，必须重点检查和反馈】
1. **格式**：对话用「角色：台词」，动作用 △ 开头，场景头正确（如 1-1 客厅 日 内）
2. **剧情逻辑**：
   - 剧情必须看得懂，不能逻辑跳跃
   - 不能突然冒出没介绍过的人物/敌人
   - 每个情节要有因果关系
   - 如果读完不知道在讲什么，直接驳回

【硬性规则 - 任何一条不满足直接驳回】
- 场面：一集最多3个
- 禁止英文、禁止 meta 信息（如"——第X集完——"）
- 禁止每句全都加（冷笑）（淡定）等括号情绪词
- 禁止使用参考样本人名

【如何让剧本更好过稿】(红果短剧教程第8期)
1. **开场抓人检查**：
   - 前3行必须有冲突/悬念/反转
   - 如果开场是"早上阳光明媚"、"今天天气真好"→驳回
   - 必须是"被甩耳光"、"被质疑身份"、"危机降临"
2. **钩子强度检查**：
   - 结尾必须让观众想看下一集
   - 弱钩子："明天再说吧"、"我们走吧"→驳回
   - 强钩子："你马上会为今天说的话付出代价"、"盒子里居然是..."
3. **情绪密度检查**：
   - 每200字必须有1个情绪点（愤怒/爽感/心疼/紧张）
   - 如果全篇平淡，没有情绪起伏→驳回
4. **冲突密度检查**：
   - 一集必须有3-5个小冲突
   - 如果只有1个冲突，其他都是过渡→驳回
5. **台词质量检查**：
   - 每句台词必须推进剧情或制造冲突
   - 社交客套、无效对话→必须删除
6. **过稿红线**：
   - 主线目标不明确→驳回
   - 角色动机不清晰→驳回
   - 情节跳跃、看不懂→驳回
   - 开场不抓人→驳回
   - 结尾无钩子→驳回

【不需要反馈的内容 - 不要给这类建议】
- 不要建议"增加环境描写"、"丰富场景氛围"
- 不要建议"增加情绪描写"、"深化人物内心"
- 人名如果正确，不需要提及
- 如果没有问题，就不要硬凑反馈

【多维度打分 - 每项1-10分】
1. **rhythm_score 节奏分**：节奏是否紧凑，对话有来有回
2. **hook_score 钩子分**：集尾是否有钩子（必须≥8.0）
3. **climax_score 爽点分**：是否有打脸、反转等爽点
4. **plot_score 剧情分**：剧情是否连贯、无矛盾
5. **ai_tone_score AI味分**：是否口语化（必须≥8.0）
6. **dialogue_score 对话分**：对话是否通顺（必须≥8.5）

【打分标准参考】(红果短剧教程第8期)
- **rhythm 节奏**：
  * 9-10分：冲突密集、每3秒有信息增量、无废话
  * 7-8分：节奏紧凑、有冲突但不够密集
  * <7分：拖沓、有无效对话、节奏慢→驳回
- **hook 钩子**：
  * 9-10分：强悬念/危机/反转，观众睡不着
  * 7-8分：有钩子但不够强
  * <8分：弱钩子或无钩子→驳回
- **climax 爽点**：
  * 9-10分：有明显爽点（打脸/身份揭示/反转）
  * 7-8分：有小爽点但不够强
  * <7.5分：无爽点或爽点不足→驳回
- **plot 剧情**：
  * 9-10分：逻辑清晰、因果关系明确、看得懂
  * 7-8分：基本清晰，有小瑕疵
  * <8分：逻辑跳跃、看不懂→驳回

【输出要求】
- rewrite_suggestions 只写必须改的问题，聚焦格式/连贯性
- 如果对话不通顺，指出具体哪句话不通
- 如果钩子不够强，说明为什么不强，应该怎么改
- 如果开场不抓人，说明问题在哪，应该如何改开场
- 不要写空洞的建议如"增加情绪张力"、"丰富氛围"
- 没有问题就写"无"，不要硬凑"""

    def review_episode(
        self,
        episode: Episode,
        bible: Bible,
        previous_episodes: List[Episode] = None,
        format_only: bool = False
    ) -> Dict[str, Any]:
        """
        审核单集剧本：先做字数/场面硬性校验（纯算法），再AI多维度打分。
        字数500-800、场面≤3、有钩子、无矛盾、无AI味，且各维度分≥阈值才通过。
        format_only=True 时：不限制字数与场景数，只检查格式（台词通顺、人名、称谓、AI味、三角号等）。
        
        Args:
            episode: 当前要审核的集
            bible: 故事圣经（包含世界观、角色等）
            previous_episodes: 之前已生成的集（用于检查剧情连贯性）
            format_only: 若为 True，仅做格式类检查，不因字数/场景数/节奏/钩子/爽点/剧情驳回
        """
        self.log(f"正在审核第{episode.number}集..." + ("（仅格式）" if format_only else ""))
        
        drama = self.config.drama
        min_chars = 500
        max_chars = 800
        max_scenes = getattr(drama, "max_scenes_per_episode", 3)
        is_final = (episode.number == bible.total_episodes)
        
        # 1. 字数统计（全流程统一：与 script_validator.count_script_chars_include_punctuation 一致，不做 replace 空格）
        word_count = count_script_chars_include_punctuation(episode.full_script)
        word_ok = True if min_chars <= word_count <= max_chars else False
        word_msg = f"字数：{word_count}字（要求{min_chars}-{max_chars}字）"
        
        result = {
            "passed": True,
            "word_count": word_count,
            "word_ok": word_ok,
            "word_msg": word_msg,
            "scene_count": get_episode_scene_count(episode.full_script, episode.number),
            "scene_ok": True,
            "scene_msg": "",
            "triangle_ok": True,
            "triangle_msg": "",
            "scene_character_ok": True,
            "scene_character_msg": "",
            "rhythm_score": 0,
            "hook_score": 0,
            "ending_hook_type": "",
            "climax_score": 0,
            "hooks_found": [], 
            "plot_score": 0,
            "ai_tone_score": 0,
            "dialogue_score": 0,
            "compliance_ok": True,
            "character_consistency_score": 0,
            "character_consistency_ok": True,
            "unclear_dialogues": [],
            "has_english": False,
            "english_words": [],
            "has_meta": False,
            "meta_found": [],
            "mixed_colon": False,
            "logic_issues": [],
            "strengths": [],
            "weaknesses": [],
            "format_issues": [],
            "rewrite_suggestions": "",
            "overall_comment": "",
        }
        # 通过条件仅由算法审决定，字数不卡通过（只记录，不因字数设 passed=False）
        
        # 2. 硬性校验：场面数（算法）
        scene_ok, scene_count, scene_msg = check_episode_scene_count(
            episode.full_script, episode.number, max_scenes=max_scenes
        )
        result["scene_count"] = scene_count
        result["scene_ok"] = scene_ok
        result["scene_msg"] = scene_msg
        if not scene_ok:
            result["passed"] = False
            result["rewrite_suggestions"] = (result.get("rewrite_suggestions") or "") + "；" + scene_msg
        
        # 3. 硬性校验：检查英文（算法）
        import re
        english_pattern = re.compile(r'\b[a-zA-Z]{2,}\b')  # 匹配2个以上连续英文字母
        english_words = english_pattern.findall(episode.full_script)
        # 排除常见格式标记
        exclude_words = {'OS', 'VO', 'BGM', 'SFX', 'POV', 'CUT', 'FADE', 'INT', 'EXT'}
        english_words = [w for w in english_words if w.upper() not in exclude_words]
        result["has_english"] = len(english_words) > 0
        result["english_words"] = english_words[:5]  # 只记录前5个
        if english_words:
            result["passed"] = False
            result["format_issues"].append(f"剧本中有英文：{', '.join(english_words[:5])}，必须改成中文")
            result["rewrite_suggestions"] = (result.get("rewrite_suggestions") or "") + f"；删除英文词（{', '.join(english_words[:3])}），改成中文"
        
        # 4. 硬性校验：检查 meta 信息（算法）
        meta_patterns = [
            r'——第\d+集完——',
            r'【字数[约]?\d+字?】',
            r'【节奏[^\]]*】',
            r'【本集完】',
            r'第\d+集完',
            r'\(完\)',
            r'（完）',
            r'（剧终）',
            r'\(剧终\)',
            r'【剧终】',
            r'剧终',
        ]
        meta_found = []
        for pattern in meta_patterns:
            matches = re.findall(pattern, episode.full_script)
            meta_found.extend(matches)
        result["has_meta"] = len(meta_found) > 0
        result["meta_found"] = meta_found[:3]  # 只记录前3个
        if meta_found:
            result["passed"] = False
            result["format_issues"].append(f"剧本中有 meta 信息：{', '.join(meta_found[:3])}，必须删除")
            result["rewrite_suggestions"] = (result.get("rewrite_suggestions") or "") + f"；删除 meta 信息（{', '.join(meta_found[:3])}）"
        
        # 5. 硬性校验：三角号（算法）动作行是否都带△
        triangle_ok, triangle_msg = check_action_triangles_present(episode.full_script)
        result["triangle_ok"] = triangle_ok
        result["triangle_msg"] = triangle_msg
        if not triangle_ok:
            result["passed"] = False
            result["format_issues"].append(triangle_msg)
            result["rewrite_suggestions"] = (result.get("rewrite_suggestions") or "") + "；" + triangle_msg
        
        # 6. 硬性校验：场景头下是否有人物/对话行（算法）
        scene_character_ok, scene_character_msg = check_scene_followed_by_character_line(episode.full_script, episode.number)
        result["scene_character_ok"] = scene_character_ok
        result["scene_character_msg"] = scene_character_msg
        if not scene_character_ok:
            result["passed"] = False
            result["format_issues"].append(scene_character_msg)
            result["rewrite_suggestions"] = (result.get("rewrite_suggestions") or "") + "；" + scene_character_msg
        
        # 7. 硬性校验：检查对话格式统一性（算法）
        # 正确格式：角色名：台词 或 角色名（OS）：台词
        dialogue_lines = [line.strip() for line in episode.full_script.split('\n') 
                         if line.strip() and not line.strip().startswith('△') 
                         and not line.strip().startswith('【')
                         and not re.match(r'^\d+-\d+', line.strip())]  # 排除动作、标记、场景头
        
        # 检查是否有对话行（包含中文冒号或英文冒号的行）
        colon_lines = [line for line in dialogue_lines if '：' in line or ':' in line]
        mixed_colon = any(':' in line and '：' not in line for line in colon_lines)  # 用了英文冒号
        result["mixed_colon"] = mixed_colon
        if mixed_colon:
            result["passed"] = False
            result["format_issues"].append("对话格式不统一：应使用中文冒号「：」而非英文冒号「:」")
            result["rewrite_suggestions"] = (result.get("rewrite_suggestions") or "") + "；对话冒号统一用中文「：」"
        
        # 8. AI 多维度打分（仅输出给人参考，不参与通过/驳回；format_only 时也不卡通过）
        # 预检查：剧本内容异常时跳过 AI 审，避免模型拒绝输出 JSON
        script_text = (episode.full_script or "").strip()
        script_invalid_markers = ["我没有之前生成的剧本", "这是我们对话的开头", "请提供", "请贴出"]
        skip_ai_review = len(script_text) < 100 or any(m in script_text for m in script_invalid_markers)
        if skip_ai_review:
            self.log(f"  第{episode.number}集剧本内容异常或过短，跳过 AI 审，仅按硬性规则判定")
        else:
            char_names = list(bible.characters.keys())
            char_names_str = "、".join(char_names) if char_names else "（未设定）"
            char_info_lines = []
            for name, char in bible.characters.items():
                char_info_lines.append(f"- {name}：{char.identity}，{char.personality}，状态={char.status.value}")
            char_info = "\n".join(char_info_lines) if char_info_lines else "（未设定）"
            
            # 构建重要剧情点
            plot_points_str = ""
            if bible.plot_points:
                pp_lines = [f"- 第{pp.episode}集：{pp.description}" for pp in bible.plot_points[-10:]]
                plot_points_str = "\n".join(pp_lines)
            
            # 构建伏笔信息
            foreshadow_str = ""
            if bible.foreshadowing:
                fs_lines = []
                for fs in bible.foreshadowing:
                    status = "已揭示" if fs.is_resolved else "待揭示"
                    fs_lines.append(f"- {fs.description}（{status}）")
                foreshadow_str = "\n".join(fs_lines[-5:])  # 最多5条
            
            # 构建活跃冲突
            conflicts_str = "、".join(bible.active_conflicts[:5]) if bible.active_conflicts else "无"
            
            # 构建之前集的摘要
            prev_summary = ""
            if previous_episodes:
                prev_lines = []
                for prev_ep in previous_episodes[-5:]:  # 最多取最近5集
                    synopsis_text = prev_ep.synopsis[:100] + "..." if prev_ep.synopsis and len(prev_ep.synopsis) > 100 else (prev_ep.synopsis or "")
                    prev_lines.append(f"第{prev_ep.number}集：{synopsis_text}")
                prev_summary = "\n".join(prev_lines)
            
            prev_section = f"""
【之前剧情回顾】
{prev_summary}
""" if prev_summary else ""

            plot_section = f"""
【重要剧情点】
{plot_points_str}
""" if plot_points_str else ""

            foreshadow_section = f"""
【伏笔追踪】
{foreshadow_str}
""" if foreshadow_str else ""
            
            prompt = f"""请审核以下短剧剧本，重点检查【格式、连贯性、剧情逻辑】。

===== 世界观圣经 =====
【剧名】{bible.title}
【类型】{', '.join(bible.genre) if bible.genre else '未设定'}
【主题】{bible.theme or '未设定'}

【总体大纲】
{bible.overall_outline or '（未设定）'}

【角色设定】
{char_info}

【当前活跃冲突】{conflicts_str}
{plot_section}{foreshadow_section}
===== 本集信息 =====
【集数】第{episode.number}集（共{bible.total_episodes}集）
【本集大纲】{episode.synopsis}
{prev_section}

【角色名列表（人名必须与此一致）】
{char_names_str}

【剧本内容】
{episode.full_script}

【⚠️ 无论剧本内容如何，都必须直接输出 JSON，不要输出解释、提问或其它文字】
请严格以JSON格式返回（每个分数精确到0.1，必须附带reason说明原因）：
{{
    "rhythm": {{"score": "如7.5", "reason": "节奏评价原因，＜8.0分必须写具体问题"}},
    "hook": {{"score": "如8.2", "reason": "钩子评价原因"}},
    "ending_hook_type": "生死钩/秘密钩/反转钩/情感钩/无或弱",
    "climax": {{"score": "如7.8", "reason": "爽点评价原因，＜8.0分必须写具体问题"}},
    "hooks_found": [],
    "plot": {{"score": "如8.5", "reason": "剧情逻辑评价，是否有突然出现的人物、是否看得懂"}},
    "ai_tone": {{"score": "如9.0", "reason": "AI味评价，是否有不自然的表达"}},
    "dialogue": {{"score": "如8.7", "reason": "对话通顺度，＜8.5分必须指出哪句不通"}},
    "compliance": {{"score": "如10.0", "reason": "合规评价，是否有敏感内容"}},
    "character_consistency": {{"score": "如9.5", "reason": "角色言行是否符合人设（性格、身份、背景），不符合写出具体问题"}},
    "unclear_dialogues": ["不通顺的对话原句，无则[]"],
    "format_issues": ["格式问题，无则[]"],
    "overall_comment": "一句话总评"
}}

【⚠️ 打分标准 - 精确到0.1分】
- **分数范围**：1.0-10.0，精确到小数点后一位
- **及格线**：一般维度≥8.0分，对话≥8.5分
- **8.0分以上**：该维度没有问题，reason 写"无问题"
- **8.0分以下**：该维度有问题，reason **必须**写出具体问题是什么

【各维度说明】
1. **rhythm 节奏**：节奏是否紧凑，对话有来有回
2. **hook 钩子**：集尾是否有钩子，能否吸引观众看下一集
3. **climax 爽点**：是否有打脸、反转等爽点
4. **plot 剧情逻辑**：剧情是否看得懂，有没有突然冒出的人物/敌人
5. **ai_tone AI味**：对话是否自然，有没有AI腔
6. **dialogue 对话通顺**：每句话是否通顺、能让人听懂、意思表达清楚
7. **compliance 合规**：有没有敏感/违规内容
8. **character_consistency 角色一致性**：角色言行是否符合人设

【⚠️ rhythm 节奏评分标准】
- ✅ **短剧节奏本来就快**：快节奏是正常的，不要因为"节奏快"扣分
- ✅ 有冲突、有对话、有推进 → 8.0分以上
- ✅ 场景转换自然、不拖沓 → 高分
- ❌ 只有以下情况才扣分：
  - 大段独白、大段描写、没有对话推进
  - 剧情完全没有进展、原地踏步
  - 节奏混乱、看不懂在讲什么
- ⚠️ 短剧节奏快是正常的，不要因为"太快"、"转折太多"扣分

【⚠️ dialogue 对话评分标准 - 严格！】
✅ 高分（8.5+）的对话必须：
- 像人话：每句话读起来自然、通顺
- 意思清楚：读者能听懂在说什么
- 前后连贯：上下句有逻辑关系
- 完整表达：不省略关键信息

❌ 必须扣分的情况（低于8.5）：
- 莫名其妙：突然提到没交代过的事物（如"马上要收到的短信"但没说什么短信）
- 语法不通："一块破旧箱子"应该是"一个破旧箱子"
- 逻辑跳跃：上一句和下一句没有关系
- 残缺不全：省略主语或关键信息，让人摸不着头脑
- 角色乱入：提到角色设定里没有的人物（如突然出现"客服"）

⚠️ 口语化是好的，但必须是"通顺的口语"，不是"残缺的口语"
⚠️ 如果有任何一句话让人看不懂，dialogue 分数必须 < 8.5

【⚠️ 不要给这类反馈】
- 不要建议"增加环境描写"、"丰富场景氛围"
- 不要建议"增加情绪描写"、"深化人物内心"
- 不要批评"对话太口语化"、"不够书面"
- 没有问题的维度 reason 写"无问题"，不要硬凑"""

            def _num(v, default=0):
                if isinstance(v, (int, float)):
                    return max(0, min(10, v))
                if isinstance(v, str):
                    try:
                        return max(0, min(10, float(v.strip())))
                    except ValueError:
                        return default
                return default

            try:
                # 打印审核提示词
                print("\n" + "=" * 80)
                print(f"【审稿 - 第{episode.number}集提示词】")
                print("=" * 80)
                print(prompt)
                print("=" * 80 + "\n")
                
                # 增加max_tokens确保输出不被截断
                ai_result = self._chat_json(prompt, temperature=0.3, max_tokens=4000, print_prompt=False)  # 已手动打印
                
                # 解析新的 {score, reason} 格式
                def parse_score_reason(data, key):
                    """解析 {score, reason} 格式，返回 (score, reason)"""
                    if isinstance(data, dict):
                        return _num(data.get("score"), 0), data.get("reason", "")
                    return _num(data, 0), ""
                
                # 解析各维度分数和原因
                result["rhythm_score"], rhythm_reason = parse_score_reason(ai_result.get("rhythm"), "rhythm")
                result["hook_score"], hook_reason = parse_score_reason(ai_result.get("hook"), "hook")
                result["ending_hook_type"] = (ai_result.get("ending_hook_type") or "").strip()
                result["climax_score"], climax_reason = parse_score_reason(ai_result.get("climax"), "climax")
                result["hooks_found"] = ai_result.get("hooks_found") if isinstance(ai_result.get("hooks_found"), list) else []
                result["plot_score"], plot_reason = parse_score_reason(ai_result.get("plot"), "plot")
                result["ai_tone_score"], ai_tone_reason = parse_score_reason(ai_result.get("ai_tone"), "ai_tone")
                result["dialogue_score"], dialogue_reason = parse_score_reason(ai_result.get("dialogue"), "dialogue")
                compliance_score, compliance_reason = parse_score_reason(ai_result.get("compliance"), "compliance")
                result["compliance_ok"] = compliance_score >= 8.0
                char_consistency_score, char_consistency_reason = parse_score_reason(ai_result.get("character_consistency"), "character_consistency")
                result["character_consistency_score"] = char_consistency_score
                result["character_consistency_ok"] = char_consistency_score >= 8.0
                
                result["unclear_dialogues"] = ai_result.get("unclear_dialogues") or []
                ai_format_issues = ai_result.get("format_issues") if isinstance(ai_result.get("format_issues"), list) else []
                result["format_issues"] = result.get("format_issues", []) + ai_format_issues
                result["overall_comment"] = ai_result.get("overall_comment", "")
                
                # AI 审结果仅写入 result 供输出给人参考，不参与通过/驳回（通过仅由算法审决定）
                    
            except Exception as e:
                self.log(f"  AI审核调用异常：{e}，仅按硬性规则判定")
        
        hooks_found_str = "、".join(result.get("hooks_found", [])[:3]) or "无"
        extra_issues = []
        if result.get("has_english"):
            extra_issues.append(f"英文:{','.join(result.get('english_words', [])[:2])}")
        if result.get("has_meta"):
            extra_issues.append("meta信息")
        if not result.get("character_consistency_ok", True):
            extra_issues.append(f"角色不一致:{result.get('character_consistency_score', 0)}分")
        extra_str = f" [{', '.join(extra_issues)}]" if extra_issues else ""
        
        self.log(
            f"  第{episode.number}集：字{result['word_count']}{'✓' if result['word_ok'] else '✗'} "
            f"场{result['scene_count']}{'✓' if result['scene_ok'] else '✗'} "
            f"△{'✓' if result.get('triangle_ok', True) else '✗'} 场景人物{'✓' if result.get('scene_character_ok', True) else '✗'} "
            f"节奏{result['rhythm_score']} 钩子{result['hook_score']}({result.get('ending_hook_type', '')}) "
            f"爽点{result['climax_score']}[{hooks_found_str}] 剧情{result['plot_score']} AI味{result['ai_tone_score']} "
            f"对话{result.get('dialogue_score', 0)} "
            f"合规{'✓' if result.get('compliance_ok', True) else '✗'}{extra_str} "
            f"{'通过' if result['passed'] else '驳回'}"
        )
        
        return result
    
    def review_episodes_batch(
        self,
        episodes: List[Episode],
        bible: Bible,
        all_episodes: List[Episode] = None,
        format_only: bool = False
    ) -> List[Tuple[Episode, Dict[str, Any]]]:
        """
        批量审核剧集
        
        Args:
            episodes: 要审核的剧集列表
            bible: 世界观圣经
            all_episodes: 所有已生成的剧集（用于获取之前集的上下文）
            format_only: 仅做格式类检查（台词、人名、称谓、AI味、三角号等），不限制字数/场景
        Returns:
            (剧集, 审核结果) 元组列表
        """
        self.log(f"开始批量审核{len(episodes)}集..." + ("（仅格式）" if format_only else ""))
        
        # 构建按集数排序的全部剧集列表
        all_eps_sorted = sorted(all_episodes or [], key=lambda e: e.number) if all_episodes else []
        
        results = []
        for episode in episodes:
            # 保存审核时的原文
            original_script = episode.full_script
            
            # 获取当前集之前的所有集
            previous_episodes = [ep for ep in all_eps_sorted if ep.number < episode.number]
            
            review = self.review_episode(episode, bible, previous_episodes, format_only=format_only)
            episode.hook_score = review.get("hook_score")
            
            # 把审稿反馈存到 episode 里，包含原文（通过仅由算法审决定，AI 结果仅供参考）
            episode.review_feedback = {
                "original_script": original_script,
                "passed": review.get("passed", False),
                "word_count": review.get("word_count", 0),
                "word_ok": review.get("word_ok", True),
                "scene_count": review.get("scene_count", 0),
                "scene_ok": review.get("scene_ok", True),
                "triangle_ok": review.get("triangle_ok", True),
                "scene_character_ok": review.get("scene_character_ok", True),
                "has_english": review.get("has_english", False),
                "english_words": review.get("english_words", []),
                "has_meta": review.get("has_meta", False),
                "meta_found": review.get("meta_found", []),
                "rhythm_score": review.get("rhythm_score", 0),
                "hook_score": review.get("hook_score", 0),
                "climax_score": review.get("climax_score", 0),
                "plot_score": review.get("plot_score", 0),
                "ai_tone_score": review.get("ai_tone_score", 0),
                "dialogue_score": review.get("dialogue_score", 0),
                "character_consistency_score": review.get("character_consistency_score", 0),
                "character_consistency_ok": review.get("character_consistency_ok", True),
                "unclear_dialogues": review.get("unclear_dialogues", []),
                "format_issues": review.get("format_issues", []),
                "weaknesses": review.get("weaknesses", []),
                "rewrite_suggestions": review.get("rewrite_suggestions", ""),
                "overall_comment": review.get("overall_comment", ""),
            }
            
            results.append((episode, review))
        
        passed_count = sum(1 for _, r in results if r.get("passed", False))
        self.log(f"批量审核完成：{passed_count}/{len(episodes)}集通过")
        
        return results
    
    def check_consistency(
        self,
        bible: Bible,
        new_episodes: List[Episode],
        is_rewrite: bool = False
    ) -> Dict[str, Any]:
        """
        检查新剧集与已有内容的一致性
        
        Args:
            bible: 世界观圣经
            new_episodes: 新生成的剧集（或重写后的剧集）
            is_rewrite: 若为 True 表示当前是重写稿审稿，检查时不要将「与已有同集数内容不同」判为重复/时间线问题
        
        Returns:
            一致性检查结果
        """
        self.log("正在检查剧情一致性..." + ("（重写稿）" if is_rewrite else ""))
        
        rewrite_numbers = {ep.number for ep in new_episodes} if is_rewrite else set()
        
        # 已有剧集摘要（重写时排除被重写的集数，避免模型误报「第X集重复」）
        existing_summary = ""
        if bible.episodes:
            recent = bible.episodes[-10:]
            if is_rewrite and rewrite_numbers:
                recent = [ep for ep in recent if ep.number not in rewrite_numbers]
            existing_summary = "\n".join([
                f"第{ep.number}集：{ep.synopsis}"
                for ep in recent
            ]) if recent else ""
        
        # 待检查的剧集摘要
        new_summary = "\n".join([
            f"第{ep.number}集：{ep.synopsis}\n{ep.full_script[:500]}..."
            for ep in new_episodes
        ])
        
        if is_rewrite:
            prompt = f"""请检查**重写稿**与前后剧情、人设的一致性（这些是重写后的内容，将替换已有剧情中同集数的旧内容）。

【剧名】{bible.title}

【角色设定】
{bible.get_summary()}

【已有剧情（前后集，不含本集）】
{existing_summary if existing_summary else "无其他集"}

【重写剧集（待检查）】
{new_summary}

注意：这是重写稿审稿，不要将「与旧版第X集内容不同」或「替换同集」视为时间线问题或重复。只检查：角色言行是否符合人设、与前后集剧情是否衔接、有无剧情漏洞。

请以JSON格式返回检查结果：
{{
    "is_consistent": true/false,
    "character_issues": ["角色行为与设定不符的问题"],
    "timeline_issues": ["与前后集时间线或衔接矛盾"],
    "plot_holes": ["剧情漏洞"],
    "suggestions": ["修改建议"]
}}"""
        else:
            prompt = f"""请检查新剧集与已有剧情的一致性。

【剧名】{bible.title}

【角色设定】
{bible.get_summary()}

【已有剧情】
{existing_summary if existing_summary else "这是第一批剧集"}

【新增剧集】
{new_summary}

请以JSON格式返回检查结果：
{{
    "is_consistent": true/false,
    "character_issues": ["角色行为与设定不符的问题"],
    "timeline_issues": ["时间线矛盾"],
    "plot_holes": ["剧情漏洞"],
    "suggestions": ["修改建议"]
}}"""

        # 增加max_tokens确保输出不被截断
        # 添加错误处理，一致性检查失败不应阻断整个流程
        try:
            result = self._chat_json(prompt, temperature=0.2, max_tokens=4000)
            
            issues_count = (
                len(result.get("character_issues", [])) +
                len(result.get("timeline_issues", [])) +
                len(result.get("plot_holes", []))
            )
            
            self.log(f"  一致性检查完成：{'通过' if result.get('is_consistent', True) else f'发现{issues_count}个问题'}")
            
            return result
        except Exception as e:
            self.log(f"  ⚠️ 一致性检查失败（JSON解析错误），跳过检查：{str(e)[:100]}")
            # 返回默认的"通过"结果，不阻断流程
            return {
                "is_consistent": True,
                "character_issues": [],
                "timeline_issues": [],
                "plot_holes": [],
                "suggestions": [],
                "_skipped": True,
                "_error": str(e)[:200]
            }
    
    def run(
        self,
        episodes: List[Episode],
        bible: Bible,
        is_rewrite: bool = False,
        format_only: bool = False
    ) -> Tuple[List[Episode], List[Episode], Dict[str, Any]]:
        """
        执行审稿任务
        
        Args:
            episodes: 要审核的剧集列表
            bible: 世界观圣经
            is_rewrite: 若为 True 表示当前是重写后的再次审稿，一致性检查会按「重写稿」处理，不误报同集重复
            format_only: 若为 True 仅做格式检查（台词通顺、人名、称谓、AI味、三角号等），不限制字数/场景
        
        Returns:
            (通过的剧集, 需要重写的剧集, 审核报告)
        """
        self.log("=" * 50)
        self.log(f"开始审稿流程，共{len(episodes)}集" + ("（仅格式）" if format_only else "") + ("（重写稿）" if is_rewrite else ""))
        self.log("=" * 50)
        
        # 1. 逐集审核（AI 打分 + 算法项仅记录）：只做 AI 审与一致性，结果全部不卡通过，仅作人审参考
        review_results = self.review_episodes_batch(episodes, bible, all_episodes=episodes, format_only=format_only)
        
        # 2. 一致性检查（重写时用不同 prompt，避免报「第X集与已有第X集重复」）
        consistency = self.check_consistency(bible, episodes, is_rewrite=is_rewrite)
        
        # 3. 全部视为通过，审稿结果仅挂到 episode.review_feedback 供人审参考
        passed_episodes = []
        all_reviews = []
        
        for episode, review in review_results:
            key_scores = [
                review.get("rhythm_score") or 0,
                review.get("hook_score") or 0,
                review.get("climax_score") or 0,
                review.get("plot_score") or 0,
                review.get("ai_tone_score") or 0,
            ]
            composite = sum(key_scores) / len(key_scores) if key_scores else review.get("hook_score") or 0
            all_reviews.append({
                "episode": episode.number,
                "score": composite,
                "passed": review.get("passed"),
                "comment": review.get("overall_comment"),
                "word_ok": review.get("word_ok"),
                "scene_ok": review.get("scene_ok"),
                "rhythm_score": review.get("rhythm_score"),
                "hook_score": review.get("hook_score"),
                "ending_hook_type": review.get("ending_hook_type"),
                "climax_score": review.get("climax_score"),
                "hooks_found": review.get("hooks_found"),
                "plot_score": review.get("plot_score"),
                "ai_tone_score": review.get("ai_tone_score"),
                "compliance_ok": review.get("compliance_ok"),
                "logic_issues": review.get("logic_issues"),
                "strengths": review.get("strengths"),
                "weaknesses": review.get("weaknesses"),
                "format_issues": review.get("format_issues"),
                "rewrite_suggestions": review.get("rewrite_suggestions"),
            })
            episode.review_feedback = review
            passed_episodes.append(episode)
        
        report = {
            "total_reviewed": len(episodes),
            "passed_count": len(passed_episodes),
            "failed_count": 0,
            "average_score": sum(r["score"] or 0 for r in all_reviews) / len(all_reviews) if all_reviews else 0,
            "reviews": all_reviews,
            "consistency_check": consistency,
        }
        
        self.log("=" * 50)
        self.log(f"审稿完成：{len(passed_episodes)}集（全部作为参考意见，不卡通过）")
        self.log(f"平均评分：{report['average_score']:.1f}")
        self.log("=" * 50)
        
        return passed_episodes, [], report
    
    def review_ideation(self, bible: Bible) -> Dict[str, Any]:
        """
        审核梗概和人设：
        1. 检查是否使用了参考样本中的人名（禁止）
        2. 检查大纲中的人名是否都有对应的人设（需要补充）
        
        Args:
            bible: 世界观圣经（包含梗概、大纲、人设）
        
        Returns:
            审核结果，包含 passed, forbidden_names_found, missing_characters, suggestions
        """
        import re
        from ..config import get_config
        get_config().current_stage_name = "05_审核"
        self.log("开始审核梗概和人设...")
        
        # 禁止使用的参考样本人名（来自常见参考剧本）
        forbidden_names = [
            # 《十八岁太奶奶》
            '容遇', '纪舜英', '纪止渊', '容若瑶', '蓝柔雪',
            # 其他常见参考剧本
            '林浅', '宋婉清', '夏知星', '顾墨轩', '沈清雅',
            '霍庭深', '陆景琛', '苏暖', '叶倾城', '萧战',
            '慕容云', '上官月', '司马青', '诸葛风'
        ]
        
        result = {
            "passed": True,
            "forbidden_names_found": [],
            "missing_characters": [],  # 大纲中有但人设中没有的人名
            "locations": [],
            "suggestions": ""
        }
        
        # 1. 检查梗概中是否有禁用人名
        if bible.synopsis:
            found_in_synopsis = [name for name in forbidden_names if name in bible.synopsis]
            if found_in_synopsis:
                result["forbidden_names_found"].extend(found_in_synopsis)
                result["locations"].append(f"梗概中发现：{', '.join(found_in_synopsis)}")
        
        # 2. 检查总体大纲中是否有禁用人名
        if bible.overall_outline:
            found_in_outline = [name for name in forbidden_names if name in bible.overall_outline]
            if found_in_outline:
                for name in found_in_outline:
                    if name not in result["forbidden_names_found"]:
                        result["forbidden_names_found"].append(name)
                result["locations"].append(f"总体大纲中发现：{', '.join(found_in_outline)}")
        
        # 3. 检查人设中是否有禁用人名
        existing_char_names = list(bible.characters.keys()) if bible.characters else []
        for name in existing_char_names:
            if name in forbidden_names:
                if name not in result["forbidden_names_found"]:
                    result["forbidden_names_found"].append(name)
                result["locations"].append(f"人设角色名：{name}")
        
        # 判断是否通过（只检查禁用人名，人设完整性由生成阶段保证）
        if result["forbidden_names_found"]:
            result["passed"] = False
            result["suggestions"] = f"使用了参考样本人名：{', '.join(result['forbidden_names_found'])}，必须重新起名"
            self.log(f"  ❌ 发现禁用人名：{result['forbidden_names_found']}")
        else:
            self.log(f"  ✅ 审核通过：人名合规")
        
        return result
