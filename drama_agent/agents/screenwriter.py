"""
编剧Agent (Screenwriter) - 负责撰写具体剧本
"""
import json
import re
from typing import Optional, List, Dict, Any

from .base_agent import BaseAgent
from ..models import Bible, Episode, Scene, EpisodeHook, HookType
from ..config import get_config


def clean_script(script: str) -> str:
    """
    后处理剧本内容：
    1. 去掉连续的空行（保留单个换行）
    2. 去掉行首行尾多余空格
    3. 去掉连续的空格
    
    Returns:
        清理后的剧本内容
    """
    if not script:
        return script
    
    # 1. 将多个连续换行替换为单个换行
    script = re.sub(r'\n\s*\n+', '\n\n', script)
    
    # 2. 去掉每行首尾的多余空格
    lines = script.split('\n')
    lines = [line.strip() for line in lines]
    script = '\n'.join(lines)
    
    # 3. 去掉连续的空格（保留单个）
    script = re.sub(r' +', ' ', script)
    
    # 4. 去掉开头和结尾的空白
    script = script.strip()
    
    return script


class ScreenwriterAgent(BaseAgent):
    """
    编剧Agent
    职责：
    1. 根据分集大纲撰写具体剧本
    2. 编写对话、动作、心理活动
    3. 确保每集结尾有钩子
    """
    
    def __init__(self):
        super().__init__("编剧Agent")
        self.config = get_config()
    
    @property
    def system_prompt(self) -> str:
        return """你是一位资深的国产爆款短剧编剧。

【⚠️⚠️⚠️ 第一优先级：像人话！去AI！】(红果短剧教程第9期)
这是最重要的要求，比字数、比格式都重要！

每一句对话必须：
1. **通顺**：读起来顺畅，是正常人会说的话
2. **清楚**：读者能立刻明白这句话的意思
3. **连贯**：上一句和下一句要有逻辑关系，A问什么B就答什么

❌ 错误示例（不像人话，绝对禁止）：
- "替代？你连自己都不配认" → 看不懂在说什么
- "就凭你马上要收到的手机短信" → 什么短信？莫名其妙
- "一块破旧箱子" → 语法不通，应该是"一个"
- A问"你来干什么"，B答"天色不早了" → 答非所问

✅ 正确示例（像人话）：
- "你算什么东西？一个替身也敢在这儿指手画脚？"
- "三年了，我一直在等这一天。今天，轮到你尝尝被人踩在脚下的滋味。"
- "你以为你是谁？没有我，你连这个门都进不了！"

【台词打磨实战方法】(红果短剧教程第9期)
1. **短句原则**：既要包含长句，也要包含短句，可以增加句子长度，减少句子数量，像真人吵架一样，长短句结合
   - 长句拆成短句的方法：不要"我觉得你这个人真的很过分，竟然在大家面前这样侮辱我"，可以改成："你过分！""当着这么多人的面侮辱我？"
2. **动词驱动**：多用动词，少用形容词
   - 不要："他是一个非常愤怒的人"
   - 改成："他冲上去，一把揪住对方的领子"
3. **情绪外显**：通过行为和对话展现情绪，不要说"我很生气"
   - 不要："我现在非常生气"
   - 改成："你给我滚！"（配合△动作：甩开对方的手）
4. **人物语言差异化**：不同角色说话风格不同
   - 老板：简短命令句"去办""不够"
   - 小职员：犹豫不决"这个...我觉得...可能..."
   - 反派：阴阳怪气"呵，你还真以为自己是个人物？"

【称呼要正确】
- 人物之间的称呼要符合关系：夫妻、上下级、朋友、仇人
- 不能乱叫：老婆不能叫老公"先生"，下属不能直呼老板名字
- 称呼要一致：同一个人对同一个人的称呼要统一

【短剧节奏设计密码】(红果短剧教程第5期)
1. **3秒定律**：每3秒必须有"信息增量"
   - 信息增量 = 新冲突/新信息/新转折/新爽点
   - 禁止无效对话："你好""我也好""天气不错"
2. **冲突密度**：一集500-700字必须有3-5个小冲突
   - 开场冲突：主角被欺负/被质疑/被陷害
   - 中段冲突：主角反击/真相浮现/意外发生
   - 结尾冲突：更大危机/反转/钩子抛出
3. **节奏变化**：快-慢-快
   - 快：对话密集、动作连贯（冲突高潮）
   - 慢：短暂铺垫、信息交代（为下次冲突蓄力）
   - 快：再次推向高潮（结尾钩子）

【情绪点设计实操】(红果短剧教程第7期)
1. **情绪目标明确**：每场戏都要有明确的情绪目标
   - 这场戏要让观众感受到什么？愤怒？爽感？紧张？心疼？
   - 所有台词和动作都为这个情绪服务
2. **情绪递进**：不要平铺直叙
   - 不要：主角一直被欺负，一直被欺负，一直被欺负
   - 要做：被欺负→忍耐→爆发→反击→爽感
3. **情绪对比**：强烈的情绪反差制造记忆点
   - 前一秒还在哭→下一秒冷笑反杀
   - 前一秒卑微求饶→下一秒亮出身份
4. **情绪具象化**：抽象情绪转化为具体行为
   - 不要："她很绝望" 
   - 改成："她跌坐在地，死死咬住嘴唇，指甲掐进掌心"

【剧本格式（简要，具体以当次任务要求为准）】
- 场景头：## 集数-场景号 地点 日/夜 内/外，下接人物列表
- 动作：△ 少用，每条一句短动作，台词另起行，绝对不允许连续两行△
- 对话：角色名：台词（中文冒号）；高情绪可用 角色名（情绪）：台词，情绪词要短
- 内心：角色名os：内心独白（不用括号）

【字数】500-700字/集（大结局可约800），每句话都要通顺。

【禁止】
- 英文：对白、旁白、动作描写一律用简体中文，禁止出现英文字母（A-Z/a-z）
- meta信息（如"第X集完"、字数统计）
- 抄袭参考样本的人名
- 诗意描写、堆砌四字词、环境/心理描写
- 无效对话、社交客套（"你好""再见"）
- △和台词写在同一行，连续两行△"""

    def write_episode(
        self,
        bible: Bible,
        episode_num: int,
        format_reference: Optional[str] = None
    ) -> Episode:
        """
        撰写单集剧本
        
        Args:
            bible: 世界观圣经
            episode_num: 要撰写的集数
            format_reference: 格式参考样本（仅参考格式，不参考创意）
        
        Returns:
            Episode对象
        """
        self.log(f"正在撰写第{episode_num}集...")
        
        # 获取剧情上下文
        context = bible.get_context_for_episode(episode_num)
        # 注意：context.get() 如果键存在但值为None，不会返回默认值，需要用 or {}
        beat = context.get("current_beat") or {}
        
        # 如果没有找到对应的beat，记录警告
        if not beat:
            self.log(f"  ⚠️ 第{episode_num}集没有对应的大纲，将根据前情发展剧情")
        
        # 构建角色简介
        char_intro = "\n".join([
            f"- {name}: {char.identity}，{char.personality}"
            for name, char in bible.characters.items()
        ])
        
        # 构建前情提要
        recent_summary = ""
        if context["recent_episodes"]:
            recent_summary = "【前情提要】\n" + "\n".join([
                f"第{ep['number']}集：{ep['synopsis']}"
                for ep in context["recent_episodes"]
            ])
        
        # 上一集结尾剧本片段（两集衔接最关键：本集开头必须接这段）
        prev_episode_ending = ""
        for ep in context["recent_episodes"]:
            if ep.get("number") == episode_num - 1:
                script = (ep.get("full_script") or "").strip()
                if script:
                    # 取上一集最后约 800 字，确保包含上一集最后一整场戏
                    prev_episode_ending = script[-800:] if len(script) > 800 else script
                    prev_episode_ending = f"""
【⚠️⚠️ 上一集结尾 - 最优先！本集必须紧接下面这段】
{prev_episode_ending}

【硬性要求】本集第一场戏、第一句动作或第一句对话必须自然接在上面这段后面，不能跳时间、不能换话题、不能换场景再切回，要像同一场戏的下一句。观众会连续看，不能断档。
"""
                break
        
        # 构建伏笔提醒
        foreshadow_reminder = ""
        if context["due_foreshadows"]:
            foreshadow_reminder = "【需要回收的伏笔】\n" + "\n".join([
                f"- {fs['description']}（埋设于第{fs['planted_episode']}集）"
                for fs in context["due_foreshadows"]
            ])
        
        # 格式参考说明（控制长度，避免挤占主提示）
        format_note = ""
        if format_reference:
            format_note = f"""
【格式参考（仅参考格式写法，创意保持原创）】
{format_reference[:1200]}
"""
        
        # 判断是否是最后一集
        is_final_episode = (episode_num == bible.total_episodes)
        # 判断是否是前三集（黄金开场期）
        is_opening_episode = (episode_num <= 3)
        # 判断是否是前10集（钩子强化期）
        is_hook_critical = (episode_num <= 10)
        
        # 字数要求（短剧快节奏）
        target_min = 500
        target_max = 700 if not is_final_episode else 800
        
        # 前三集强化提示（黄金开场期）
        opening_episode_note = ""
        if is_opening_episode and not is_final_episode:
            opening_episode_note = f"""
⚡⚡⚡ 【第{episode_num}集 - 黄金开场期！生死线！】
前三集决定观众是否付费！必须做到：

1. **开头就要让观众知道**：
   - 主角是谁、主角的困境/目标是什么
   - 主线冲突是什么（谁和谁斗？为什么斗？）
   - 观众应该期待什么（复仇？逆袭？真相？）

2. **开头抓人公式**：
   - 强冲突开场：主角正在被欺负/陷害/误解
   - 身份反差：看似弱小的主角其实是...
   - 悬念抛出：一个秘密即将揭晓

3. **钩子必须超强**：
   - 结尾必须让观众"睡不着觉"
   - 必须有身份揭露/反转/危机/秘密曝光
   - 禁止平淡收尾

记住：前三集不精彩 = 观众流失 = 项目失败！
"""
        
        # 前10集钩子强化提示
        hook_note = ""
        if is_hook_critical and not is_final_episode and not is_opening_episode:
            hook_note = f"""
⚡ 【第{episode_num}集 - 钩子强化期】
前10集是付费转化关键期！结尾钩子必须够强：
- 必须有悬念/反转/危机让观众想继续看
- 禁止"明天再说"、"我们走吧"这种弱结尾
- 最好是：身份揭露一半、危机降临、秘密快要曝光
"""
        
        final_episode_note = ""
        if is_final_episode:
            final_episode_note = """
⚠️ 【这是大结局！】
这是本剧的最后一集，必须做到：
1. **解决主线冲突**：主角与主要反派的矛盾必须有明确结果
2. **主角命运明确**：主角最终的状态要清晰交代
3. **完结感**：要让观众有"故事讲完了"的满足感
4. **字数**：大结局可适当放宽到约650字

结尾氛围：主基调应该是"尘埃落定"，而不是"未完待续"。
"""
        
        # 获取角色名列表
        char_names = list(bible.characters.keys())
        char_names_str = "、".join(char_names) if char_names else "（未设定）"
        
        prompt = f"""请撰写《{bible.title}》第{episode_num}集的完整剧本。

【剧情梗概】
{bible.synopsis}

【本集大纲】
剧情：{beat.get('synopsis', '请根据前情发展剧情')}
结尾钩子：{beat.get('ending_hook', '留下悬念')}
钩子类型：{beat.get('hook_type', 'cliffhanger')}
{prev_episode_ending}

【⚠️⚠️⚠️ 角色名 - 极重要！】
只能使用以下名字：{char_names_str}
绝对禁止使用参考样本中的人名！

【角色介绍】
{char_intro}

{recent_summary}

{foreshadow_reminder}

【当前活跃冲突】
{', '.join(context['active_conflicts']) if context['active_conflicts'] else '无'}

{final_episode_note}
{opening_episode_note}
{hook_note}
{format_note}

请直接输出剧本内容（遵守规则中的像人话、节奏、情绪等原则）。

【本集硬性要求 - 不符合=不合格】
- 语言：全中文，禁止出现任何英文字母
- 字数：严格 {target_min}-{target_max} 字（含标点），系统会校验
- 场景：2-3 个，场景头格式：
  ## {episode_num}-1 地点 日/夜 内/外
  人物：角色1、角色2、角色3
  场景编号为 {episode_num}-1、{episode_num}-2、{episode_num}-3
- 本集 1 个核心剧情点，结尾必须有钩子{'（大结局为圆满收尾）' if is_final_episode else ''}
- 开头：第一句就要有冲突/悬念/反转，禁止慢热、介绍、"天气真好"
- △：少用，每条一句短动作，不连续多行，台词另起行，绝对不允许连续两行△；内心用「角色名os：」
- 禁止：文末写字数/「第X集完」/END，直接输出剧本即可"""

        # 边写边算法审：除字数外，算法项（场景/英文/Meta/△/场景下人物/冒号）不过就重写，直到通过或达上限
        from ..utils.script_validator import (
            run_algorithm_checks,
            count_script_chars_include_punctuation,
            remove_separator_lines,
            is_mostly_english,
        )
        max_attempts = 5
        last_issues: List[str] = []
        last_collapsed = False  # 上一轮输出是否被判为崩盘（过半英文），下一轮用原始 prompt 重生成

        for attempt in range(1, max_attempts + 1):
            if attempt > 1:
                if last_collapsed:
                    self.log(f"  第{episode_num}集第{attempt}次生成（上次输出崩盘，继续对话并提示「你正常输出即可」）...")
                    # 崩盘重试：沿用上一轮 message，追加一句「你正常输出即可」，让模型在原有对话上纠正
                    collapse_prompt = f"""请撰写《{bible.title}》第{episode_num}集的完整剧本。

【剧情梗概】
{bible.synopsis}

【本集大纲】
剧情：{beat.get('synopsis', '请根据前情发展剧情')}
结尾钩子：{beat.get('ending_hook', '留下悬念')}
钩子类型：{beat.get('hook_type', 'cliffhanger')}
{prev_episode_ending}

【⚠️⚠️⚠️ 角色名 - 极重要！】
只能使用以下名字：{char_names_str}
绝对禁止使用参考样本中的人名！

【角色介绍】
{char_intro}

{recent_summary}

【当前活跃冲突】
无

{final_episode_note}
{opening_episode_note}
{hook_note}
{format_note}

请直接输出剧本内容（遵守规则中的像人话、节奏、情绪等原则）。

【本集硬性要求 - 不符合=不合格】
- 语言：全中文，禁止出现任何英文字母
- 字数：严格 {target_min}-{target_max} 字（含标点），系统会校验
- 场景：2-3 个，场景头格式：
  ## {episode_num}-1 地点 日/夜 内/外
  人物：角色1、角色2、角色3
  场景编号为 {episode_num}-1、{episode_num}-2、{episode_num}-3
- 本集 1 个核心剧情点，结尾必须有钩子{'（大结局为圆满收尾）' if is_final_episode else ''}
- 开头：第一句就要有冲突/悬念/反转，禁止慢热、介绍、"天气真好"
- △：少用，每条一句短动作，不连续多行，台词另起行，绝对不允许连续两行△；内心用「角色名os：」
- 禁止：文末写字数/「第X集完」/END，直接输出剧本即可"""
                    # 上一轮助理输出（崩盘内容）截断，避免超长
                    bad_output = script_content[:3500] + ("..." if len(script_content) > 3500 else "")
                    messages = [
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": collapse_prompt},
                        {"role": "assistant", "content": bad_output},
                        {"role": "user", "content": "你正常输出即可。请用中文输出完整剧本，不要解释。"},
                    ]
                    from ..utils.llm_client import clean_llm_output
                    script_content = clean_llm_output(self.llm.chat(messages, temperature=0.8))
                    last_collapsed = False
                else:
                    self.log(f"  第{episode_num}集第{attempt}次生成（上次格式/算法未通过）...")
                    retry_prompt = f"""上次生成的剧本有以下问题，请严格按下面修改后重新输出完整剧本：

【必须修改的问题】
{chr(10).join('- ' + i for i in last_issues)}

【原剧本（供参考，修改后直接输出新剧本）】
{script_content[:3500]}{'...' if len(script_content) > 3500 else ''}

请只输出修改后的完整剧本，不要解释。"""
                    script_content = self._chat(retry_prompt, temperature=0.6, print_prompt=False)
            else:
                print("\n" + "=" * 80)
                print(f"【编剧 - 第{episode_num}集提示词】")
                print("=" * 80)
                print(prompt)
                print("=" * 80 + "\n")
                script_content = self._chat(prompt, temperature=0.8, print_prompt=False)

            # 后处理
            script_content = clean_script(script_content)
            import re
            script_content = re.sub(r'[（(]全剧本共\d+字[）)]', '', script_content)
            script_content = re.sub(r'[（(]字数[：:]\s*\d+[）)]', '', script_content)
            script_content = re.sub(r'字数统计[：:]\s*\d+字?', '', script_content)
            script_content = re.sub(r'共计?\s*\d+字', '', script_content)
            script_content = script_content.strip()
            script_content = remove_separator_lines(script_content)  # 生成后处理：去掉 --- 分隔符行

            # 算法审（除字数外）：过了才写下一集
            algo_ok, last_issues = run_algorithm_checks(script_content, episode_num, max_scenes=3)
            if algo_ok:
                break
            # 过半英文视为崩盘，下一轮用原始 prompt 重生成，不走修改重写逻辑
            if not algo_ok and is_mostly_english(script_content):
                last_collapsed = True
                self.log(f"  ⚠️ 本轮输出过半英文，判定为崩盘，下次将用原始 prompt 重新生成")
            self.log(f"  ⚠️ 算法检查未通过：{'; '.join(last_issues[:3])}{'...' if len(last_issues) > 3 else ''}")
            if attempt == max_attempts:
                self.log(f"  ⚠️ 已重试{max_attempts}次，使用当前版本进入审稿")

        word_count = count_script_chars_include_punctuation(script_content.replace(' ', ''))
        self.log(f"  第{episode_num}集撰写完成，{word_count}字，等待审稿")
        
        # 构建Episode对象
        episode = Episode(
            number=episode_num,
            title=beat.get('synopsis', f'第{episode_num}集')[:20],
            synopsis=beat.get('synopsis', ''),
            full_script=script_content,
            ending_hook=EpisodeHook(
                hook_type=beat.get('hook_type', 'cliffhanger'),
                description=beat.get('ending_hook', ''),
                intensity=7
            )
        )
        
        return episode
    
    def write_episodes_batch(
        self,
        bible: Bible,
        start_episode: int,
        end_episode: int,
        format_reference: Optional[str] = None
    ) -> List[Episode]:
        """
        批量撰写多集剧本
        
        Args:
            bible: 世界观圣经
            start_episode: 起始集数
            end_episode: 结束集数
            format_reference: 格式参考
        
        Returns:
            Episode列表
        """
        from ..config import get_config
        get_config().current_stage_name = "08_写剧本"
        self.log(f"开始撰写第{start_episode}集到第{end_episode}集...")
        
        episodes = []
        for ep_num in range(start_episode, end_episode + 1):
            episode = self.write_episode(bible, ep_num, format_reference)
            episodes.append(episode)
            
            # 将已完成的剧集加入Bible（供后续剧集参考）
            bible.add_episode(episode)
        
        self.log(f"批量撰写完成，共{len(episodes)}集")
        return episodes
    
    
    def run_batch_mode(
        self,
        bible: Bible,
        start_episode: int = 1,
        end_episode: Optional[int] = None
    ) -> List[Episode]:
        """
        批量生成模式：一次生成多集，然后智能分割
        
        Args:
            bible: 世界观圣经
            start_episode: 起始集数
            end_episode: 结束集数
        
        Returns:
            生成的剧集列表
        """
        if end_episode is None:
            end_episode = start_episode + self.config.drama.episodes_per_batch - 1
        
        num_episodes = end_episode - start_episode + 1
        
        self.log(f"开始批量生成第{start_episode}到第{end_episode}集...")
        
        # 1. 一次性生成完整剧本
        from .batch_writer import generate_batch_script, smart_split_script, add_ending_hooks, update_scene_numbers
        
        full_script = generate_batch_script(self, bible, start_episode, end_episode)
        
        # 2. 智能分割成多集（严格按600字）
        self.log(f"开始智能分割（目标{num_episodes}集，每集约600字）...")
        split_scripts = smart_split_script(full_script, num_episodes, target_chars_per_ep=600)
        actual_num = len(split_scripts)
        self.log(f"分割完成：实际{actual_num}集，字数：{[len(s) for s in split_scripts]}")
        
        if actual_num < num_episodes:
            self.log(f"⚠️ 生成的内容只够{actual_num}集，少于预期的{num_episodes}集")
        
        # 3. 添加钩子
        self.log("添加结尾钩子...")
        enhanced_scripts = add_ending_hooks(split_scripts, bible, start_episode)
        
        # 4. 更新场景编号（添加 集数-场景号）
        self.log("添加场景编号...")
        final_scripts = update_scene_numbers(enhanced_scripts, start_episode)
        
        # 5. 创建Episode对象
        episodes = []
        for idx, script in enumerate(final_scripts):
            ep_num = start_episode + idx
            beat = (bible.beat_sheet.get_beat(ep_num) if bible.beat_sheet else None) or {}
            
            episode = Episode(
                number=ep_num,
                synopsis=beat.get('synopsis', ''),
                full_script=script
            )
            
            from ..utils.script_validator import count_script_chars
            word_count = count_script_chars(script)
            
            self.log(f"  第{ep_num}集完成，{word_count}字")
            episodes.append(episode)
        
        self.log(f"批量生成完成，共{len(episodes)}集")
        
        return episodes
    
    def run(
        self,
        bible: Bible,
        start_episode: int = 1,
        end_episode: Optional[int] = None,
        format_reference: Optional[str] = None
    ) -> List[Episode]:
        """
        执行编剧任务
        
        Args:
            bible: 世界观圣经
            start_episode: 起始集数
            end_episode: 结束集数（默认一次写5集）
            format_reference: 格式参考
        
        Returns:
            生成的Episode列表
        """
        if end_episode is None:
            end_episode = min(
                start_episode + self.config.drama.episodes_per_batch - 1,
                bible.total_episodes
            )
        
        return self.write_episodes_batch(
            bible, start_episode, end_episode, format_reference
        )
