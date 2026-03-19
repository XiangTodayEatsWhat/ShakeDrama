"""
短剧生成工作流
"""
import os
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from ..agents import (
    ShowrunnerAgent,
    ScreenwriterAgent,
    EditorAgent,
    MemoryManagerAgent
)
from ..models import Bible, Episode
from ..sample_library import SampleManager, SampleSelector, SelectStrategy
from ..config import get_config


class WorkflowState(Enum):
    """工作流状态"""
    IDLE = "idle"                         # 空闲
    IDEATION = "ideation"                 # 创意阶段
    BEAT_SHEET = "beat_sheet"             # 分集大纲
    SCRIPTING = "scripting"               # 剧本撰写
    REVIEWING = "reviewing"               # 审核中
    REWRITING = "rewriting"               # 重写中
    MEMORY_UPDATE = "memory_update"       # 更新记忆
    SCRIPT_REVIEW = "script_review"       # 剧本批审稿卡点（等人审）
    FORMATTING = "formatting"             # 格式化输出
    COMPLETED = "completed"               # 完成
    ERROR = "error"                       # 错误


@dataclass
class WorkflowContext:
    """工作流上下文"""
    state: WorkflowState = WorkflowState.IDLE
    bible: Optional[Bible] = None
    current_batch_start: int = 1
    current_batch_end: int = 5
    pending_episodes: List[Episode] = field(default_factory=list)
    completed_episodes: List[Episode] = field(default_factory=list)
    failed_episodes: List[Episode] = field(default_factory=list)
    rewrite_attempts: Dict[int, int] = field(default_factory=dict)  # episode_num -> attempts
    format_reference: str = ""
    selected_sample_ids: List[str] = field(default_factory=list)
    error_message: str = ""
    # 进入剧本审稿卡点时，本批范围（供 API 显示「第 X-Y 集」，避免用 current_batch_start 已变成下一批起始而错成「第6-5集」）
    review_batch_start: int = 0
    review_batch_end: int = 0

    def load_from_file(self, filepath: str) -> None:
        """从文件加载 Bible 并同步到上下文（兼容旧调用方）"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"找不到Bible文件：{filepath}")
        bible = Bible.load(filepath)
        self.bible = bible
        self.completed_episodes = bible.episodes.copy()
        self.current_batch_start = bible.current_episode + 1
        if bible.current_episode >= bible.total_episodes:
            self.state = WorkflowState.COMPLETED
        else:
            self.state = WorkflowState.SCRIPTING


class DramaWorkflow:
    """
    短剧生成工作流
    
    协调多个Agent完成从创意到剧本的全流程。
    """
    
    def __init__(self):
        self.config = get_config()
        
        # 初始化Agents
        self.showrunner = ShowrunnerAgent()
        self.screenwriter = ScreenwriterAgent()
        self.editor = EditorAgent()
        self.memory_manager = MemoryManagerAgent()
        
        # 初始化样本库
        self.sample_manager = SampleManager()
        self.sample_selector = SampleSelector(self.sample_manager)
        
        # 工作流上下文
        self.context = WorkflowContext()
    
    def _log(self, message: str):
        """日志输出"""
        print(f"[工作流] {message}")
    
    def _save_rewrite_log(self, episode_num: int, history_feedback: list, conversation_history: list):
        """
        保存重写日志到文件
        
        Args:
            episode_num: 集数
            history_feedback: 历史反馈列表
            conversation_history: 对话历史
        """
        import os
        from datetime import datetime
        
        # 确保日志目录存在
        log_dir = os.path.join(self.config.output_dir, "rewrite_logs")
        os.makedirs(log_dir, exist_ok=True)
        
        # 创建日志文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = os.path.join(log_dir, f"episode_{episode_num}_{timestamp}.log")
        
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(f"=" * 60 + "\n")
            f.write(f"第{episode_num}集 重写日志\n")
            f.write(f"时间：{datetime.now().isoformat()}\n")
            f.write(f"=" * 60 + "\n\n")
            
            # 写入历史反馈
            f.write("【审稿反馈历史】\n")
            f.write("-" * 40 + "\n")
            for fb in history_feedback:
                f.write(f"{fb}\n\n")
            
            # 写入对话历史
            f.write("\n【重写对话历史】\n")
            f.write("-" * 40 + "\n")
            for i, msg in enumerate(conversation_history):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                f.write(f"\n[{role.upper()}]\n{content[:1000]}{'...(truncated)' if len(content) > 1000 else ''}\n")
        
        self._log(f"重写日志已保存：{log_path}")
    
    def _build_rewrite_prompt(self, bible, episode, feedback: str, history_feedback: list, all_episodes: list = None, unclear_dialogues: list = None) -> str:
        """
        构建重写提示词
        
        Args:
            bible: 世界观圣经
            episode: 需要重写的剧集
            feedback: 当前反馈
            history_feedback: 历史反馈列表
            all_episodes: 所有已生成的剧集（用于获取前情）
            unclear_dialogues: 审稿指出的不通顺台词列表，必须逐句改掉
        
        Returns:
            构建好的提示词
        """
        unclear_dialogues = unclear_dialogues or (episode.review_feedback or {}).get('unclear_dialogues') or []
        beat = (bible.beat_sheet.get_beat(episode.number) if bible.beat_sheet else None) or {}
        # 批量生成模式下不强制字数要求，保持当前长度即可
        from ..utils.script_validator import count_script_chars_include_punctuation
        current_length = count_script_chars_include_punctuation(episode.full_script)
        
        # 构建角色信息
        char_info = "\n".join([
            f"- {name}: {char.identity}，{char.personality}"
            for name, char in bible.characters.items()
        ])
        char_names = list(bible.characters.keys())
        char_names_str = "、".join(char_names) if char_names else "（未设定）"
        
        # 构建前情提要（之前集的摘要）
        prev_summary = ""
        if all_episodes:
            prev_eps = sorted([ep for ep in all_episodes if ep.number < episode.number], key=lambda e: e.number)
            if prev_eps:
                prev_lines = []
                for prev_ep in prev_eps[-5:]:  # 最多取最近5集
                    synopsis_text = prev_ep.synopsis[:100] + "..." if prev_ep.synopsis and len(prev_ep.synopsis) > 100 else (prev_ep.synopsis or "")
                    prev_lines.append(f"第{prev_ep.number}集：{synopsis_text}")
                prev_summary = "\n".join(prev_lines)
        
        prev_section = f"""
【前情提要】
{prev_summary}
""" if prev_summary else ""
        
        # 上一集结尾：重写时也要保持本集开头与上集结尾衔接
        prev_ending_section = ""
        if all_episodes:
            prev_ep = next((ep for ep in all_episodes if ep.number == episode.number - 1), None)
            if prev_ep and (prev_ep.full_script or "").strip():
                prev_script = prev_ep.full_script.strip()
                prev_ending = prev_script[-500:] if len(prev_script) > 500 else prev_script
                prev_ending_section = f"""
【上一集结尾（重写时本集开头必须保持与下面这段衔接，不要断档）】
{prev_ending}
"""
        
        # 活跃冲突
        conflicts_str = "、".join(bible.active_conflicts[:5]) if bible.active_conflicts else "无"
        
        # 不通顺台词块：重写时必须逐句改掉
        unclear_block = ""
        if unclear_dialogues:
            lines = ["【⚠️ 必须逐句改掉的不通顺台词】以下每一句都必须改成人话，不能保留原句、不能跳过："]
            for u in unclear_dialogues[:15]:
                lines.append(f"  - 「{u}」")
            unclear_block = "\n".join(lines) + "\n\n"
        
        prompt = f"""请根据审稿反馈，重写《{bible.title}》第{episode.number}集。

===== 世界观圣经 =====
【故事梗概】
{bible.synopsis or '（未设定）'}

【总体大纲】
{bible.overall_outline or '（未设定）'}

【角色设定】
{char_info}

【当前活跃冲突】{conflicts_str}

===== 本集信息 =====
【集数】第{episode.number}集（共{bible.total_episodes}集）
【本集大纲】{beat.get('synopsis', '')}
【结尾钩子】{beat.get('ending_hook', '')}
【角色名列表】{char_names_str}
{prev_section}
{prev_ending_section}
===== 重写要求 =====
【原剧本】
{episode.full_script}

【⚠️ 审稿反馈 - 必须修正】
{feedback}
{unclear_block}
【⚠️⚠️⚠️ 台词质量 - 最最重要！要爆！】

1. **称呼要正确**：
   - 人物之间的称呼要符合关系（夫妻、上下级、朋友、仇人）
   - 不能乱叫，如老婆不能叫老公"先生"
   - 称呼要前后一致，不能一会儿叫"老公"一会儿叫"林总"

2. **上下文要连贯**：
   - 上一句话和下一句话要有逻辑关系
   - 不能突然跳到另一个话题
   - 如果A说了一个问题，B的回答要针对这个问题

3. **像人话**：
   - 每句话读起来要通顺、自然
   - 不能省略关键信息让人听不懂
   - 不能出现莫名其妙的内容（如突然提到没交代过的事物）

【⚠️ 如果需要调整字数】
- 删减：优先整行删「△」开头的动作行（整行删掉），其次再简化整段动作
- 增加：增加完整的对话或场景，每句话都要推进剧情，不要写无意义的废话

【⚠️⚠️ 格式铁律（违反即乱版）】
- 动作描写一律用「△」开头。动作行可以删、可以改内容、可以新增，但**不能改格式**。
- 禁止把「△ 他甩开手」改成「他甩开手」——不能只删三角号却保留后面文字，否则格式全乱。
- 删动作 = 整行删（△和文字一起删）；改动作 = 改△后面的文字，行首△必须保留；加动作 = 新行用△开头。

【⚠️ 禁止】
- 不要在最后写"（全剧本共XXX字）"或任何字数统计
- 不要写"第X集完"、"END"等标记
- 全中文，禁止出现英文字母
- 直接输出剧本即可

请直接输出修改后的剧本，不要加说明。"""
        
        return prompt
    
    def import_sample(
        self,
        filepath: str,
        genre: Optional[List[str]] = None,
        target_audience: str = "女频"
    ) -> str:
        """
        导入样本剧本
        
        Args:
            filepath: 剧本文件路径
            genre: 类型标签
            target_audience: 目标受众
        
        Returns:
            样本ID
        """
        return self.sample_manager.import_sample(filepath, genre, target_audience)
    
    def list_samples(self) -> List[Dict[str, Any]]:
        """列出所有样本"""
        samples = self.sample_manager.list_samples()
        return [
            {
                "id": s.id,
                "title": s.title,
                "genre": s.genre,
                "target_audience": s.target_audience,
                "total_episodes": s.total_episodes,
                "style_notes": s.style_notes
            }
            for s in samples
        ]
    
    def scan_and_import_all(
        self,
        default_genre: Optional[List[str]] = None,
        default_audience: str = "女频",
        recursive: bool = True
    ) -> List[str]:
        """
        自动扫描samples_dir目录下的所有文档并导入
        
        Args:
            default_genre: 默认类型标签（如果无法从文件名推断）
            default_audience: 默认目标受众
            recursive: 是否递归扫描子目录
        
        Returns:
            成功导入的样本ID列表
        """
        return self.sample_manager.scan_and_import_all(
            default_genre=default_genre,
            default_audience=default_audience,
            recursive=recursive
        )
    
    def run_ideation(
        self,
        user_idea: str,
        sample_strategy: SelectStrategy = SelectStrategy.AUTO,
        manual_sample_ids: Optional[List[str]] = None,
        total_episodes: Optional[int] = None
    ) -> Bible:
        """
        执行创意阶段
        
        Args:
            user_idea: 用户创意概念
            sample_strategy: 样本选择策略
            manual_sample_ids: 手动指定的样本ID
        
        Returns:
            初始化的Bible
        """
        self._log("=" * 60)
        self._log("[工作流] 开始创意策划阶段")
        self._log("=" * 60)
        
        # 若未设置 run_log_dir（如 CLI 直接跑），则用 output_dir/run_logs，保证 01-07 阶段日志会写入
        if not getattr(self.config, 'run_log_dir', None):
            run_log_dir = os.path.join(self.config.output_dir, "run_logs")
            os.makedirs(run_log_dir, exist_ok=True)
            self.config.run_log_dir = run_log_dir
        
        self.context.state = WorkflowState.IDEATION
        
        # 1. 选择参考样本
        selection = self.sample_selector.select(
            user_idea,
            strategy=sample_strategy,
            manual_picks=manual_sample_ids
        )
        
        self.context.selected_sample_ids = selection.selected_ids
        self.context.format_reference = selection.format_reference
        
        if selection.selected_ids:
            self._log(f"[工作流] 已选择参考样本（共{len(selection.selected_ids)}个）")
            # 选择理由已经被过滤掉，不需要显示
        else:
            self._log("[工作流] 未使用参考样本，将进行纯原创创作")
        
        # 2. 执行策划Agent（带审核重试机制）
        max_ideation_attempts = 3
        for attempt in range(1, max_ideation_attempts + 1):
            # 生成梗概、大纲、人设
            bible = self.showrunner.run(
                user_idea,
                reference_style=selection.format_reference if self.config.sample_library.use_for_style else None,
                total_episodes=total_episodes
            )
            
            # 3. 审核梗概和人设（检查是否使用了参考样本人名）
            review_result = self.editor.review_ideation(bible)
            
            if review_result["passed"]:
                self._log("[工作流] ✅ 梗概和人设审核通过")
                break
            else:
                if attempt < max_ideation_attempts:
                    self._log(f"[工作流] ⚠️ 梗概/人设审核未通过（第{attempt}次），正在重新生成...")
                else:
                    self._log(f"[工作流] ⚠️ 警告：梗概/人设经过{max_ideation_attempts}次尝试仍有问题，保留当前版本")
        
        # 记录使用的样本
        bible.reference_samples = selection.selected_ids
        
        self.context.bible = bible
        self.context.state = WorkflowState.BEAT_SHEET
        
        # 保存Bible
        bible.save(self.config.bible_path)
        self._log("[工作流] ✅ 创意策划内容已保存")
        
        return bible
    
    def run_scripting_batch(
        self,
        start_episode: Optional[int] = None,
        end_episode: Optional[int] = None,
        format_only_review: bool = False,
        stop_after_batch_for_human: bool = False,
        on_episode_done: Optional[Callable[[int, Episode], None]] = None,
    ) -> List[Episode]:
        """
        执行一批剧本撰写。一集一集：写（格式在 screenwriter 内闭环：算法不过则重写）→ 直接入 bible 写下一集；
        本批写完后统一 AI 审 + 一致性检查，意见挂到各集供人审（不卡通过）。
        format_only_review: 批审时只做格式类检查（台词、人名、称谓、AI味、三角号等），不限制字数/场景。
        stop_after_batch_for_human: 本批完成后进入剧本审稿卡点，等人审稿后再继续下一批。
        on_episode_done: 每集完成后回调 (ep_num, episode)，用于保存历史版本等。
        
        Args:
            start_episode: 起始集数（默认续接上次）
            end_episode: 结束集数
            format_only_review: 是否仅做格式审稿
            stop_after_batch_for_human: 是否本批完成后卡点等人审稿
            on_episode_done: 单集完成回调
        
        Returns:
            本批通过的剧集列表
        """
        if self.context.bible is None:
            raise ValueError("请先执行创意阶段 (run_ideation)")
        
        bible = self.context.bible
        
        # 确定集数范围
        if start_episode is None:
            start_episode = self.context.current_batch_start
        
        if end_episode is None:
            end_episode = min(
                start_episode + self.config.drama.episodes_per_batch - 1,
                bible.total_episodes
            )
        
        self._log("=" * 60)
        self._log(f"开始撰写第{start_episode}集到第{end_episode}集")
        self._log("=" * 60)
        
        self.context.state = WorkflowState.SCRIPTING
        self.context.current_batch_start = start_episode
        self.context.current_batch_end = end_episode
        
        format_ref = self.context.format_reference if self.config.sample_library.use_for_format else None
        passed: List[Episode] = []
        
        # 一集一集：写（格式在 screenwriter 内闭环：run_algorithm_checks 不过则重写，最多 5 次）→ 直接入 bible 写下一集
        for ep_num in range(start_episode, end_episode + 1):
            self._log("=" * 50)
            self._log(f"第{ep_num}集：撰写")
            self.context.state = WorkflowState.SCRIPTING
            episode = self.screenwriter.write_episode(bible, ep_num, format_reference=format_ref)
            bible.add_episode(episode)
            passed.append(episode)
            if on_episode_done:
                try:
                    on_episode_done(ep_num, episode)
                except Exception as e:
                    self._log(f"  on_episode_done 回调异常: {e}")
            self._log(f"  第{ep_num}集 已入 bible，进入下一集")
        
        # 5集写完：AI审 + 一致性检查，所有意见挂到各集供人审（不卡通过）
        self.context.state = WorkflowState.REVIEWING
        _, _, report = self.editor.run(passed, bible, format_only=format_only_review)
        if report.get("consistency_check"):
            self._log(f"一致性检查：{report['consistency_check']}")
        
        # 三角号后处理
        from ..utils.script_validator import ensure_action_triangles
        for ep in passed:
            if ep.full_script:
                ep.full_script = ensure_action_triangles(ep.full_script)
        self._log("已对通过审核的剧本执行三角号后处理")
        
        # 输出本批每集字数 + AI审意见供人参考（字数与 editor 统一用 count_script_chars_include_punctuation）
        from ..utils.script_validator import count_script_chars_include_punctuation
        self._log("---------- 本批字数与AI审意见（供参考） ----------")
        for ep in passed:
            wc = count_script_chars_include_punctuation(ep.full_script) if ep.full_script else 0
            comment = (ep.review_feedback or {}).get("overall_comment", "") or ""
            self._log(f"  第{ep.number}集 字数：{wc} 【AI参考】{comment}")
        self._log("----------------------------------------------")
        
        # 记忆官改在人审之后执行（人审通过、继续下一批时再更新本批记忆），此处不再调用
        
        # 5. 记录完成状态
        self.context.completed_episodes.extend(passed)
        self.context.current_batch_start = end_episode + 1
        
        # 检查是否全部完成；若需卡点等人审稿则进入 SCRIPT_REVIEW
        if end_episode >= bible.total_episodes:
            self.context.state = WorkflowState.COMPLETED
            self._log("全部剧集撰写完成！")
        elif stop_after_batch_for_human:
            self.context.state = WorkflowState.SCRIPT_REVIEW
            self.context.review_batch_start = start_episode
            self.context.review_batch_end = end_episode
            self._log(f"本批第{start_episode}-{end_episode}集已完成，等待人工审稿后继续下一批")
        else:
            self.context.state = WorkflowState.SCRIPTING
        
        return passed
    
    def apply_human_script_feedback(
        self,
        batch_start: int,
        batch_end: int,
        feedback: str
    ) -> None:
        """
        根据人工审稿意见重写本批剧本（多轮审稿中的一轮）。
        会逐集用 feedback 重写并更新 bible 中的剧集，不改变 state。
        """
        if not self.context.bible or not feedback.strip():
            return
        bible = self.context.bible
        episodes = [ep for ep in bible.episodes if batch_start <= ep.number <= batch_end]
        if not episodes:
            return
        from ..agents.screenwriter import clean_script
        from ..utils.script_validator import ensure_action_triangles
        self.screenwriter.clear_conversation()
        for episode in sorted(episodes, key=lambda e: e.number):
            current_script = episode.full_script or ""
            rewrite_prompt = f"""用户对本批剧本（第{batch_start}-{batch_end}集）的审稿意见：
{feedback}

请根据上述意见修改【第{episode.number}集】的剧本。只输出修改后的完整剧本，不要加任何说明。

【当前第{episode.number}集剧本】
{current_script}

【格式要求】
- 对话格式：角色名：台词（中文冒号）
- 动作描写一律用 △ 开头
- 场景头格式：如 1-1 客厅 日 内
- 全中文，禁止出现英文字母
请直接输出修改后的完整剧本。"""
            try:
                new_script = self.screenwriter._chat_multi_turn(
                    rewrite_prompt, temperature=0.7, continue_conversation=False, print_prompt=False
                )
                new_script = clean_script(new_script)
                if new_script:
                    episode.full_script = ensure_action_triangles(new_script)
            except Exception as e:
                self._log(f"第{episode.number}集根据审稿意见重写失败: {e}")
    
    def apply_human_script_feedback_for_episode(self, episode_number: int, feedback: str) -> bool:
        """
        根据人工审稿意见只重写指定的一集（按集多轮对话）。
        会更新 bible 中该集剧本，不改变 state。返回是否找到并重写了该集。
        """
        if not self.context.bible or not feedback.strip():
            return False
        bible = self.context.bible
        episode = next((ep for ep in bible.episodes if ep.number == episode_number), None)
        if not episode:
            return False
        from ..agents.screenwriter import clean_script
        from ..utils.script_validator import ensure_action_triangles
        current_script = episode.full_script or ""
        rewrite_prompt = f"""用户对【第{episode_number}集】的审稿意见：
{feedback}

请根据上述意见修改第{episode_number}集的剧本。只输出修改后的完整剧本，不要加任何说明。

【当前第{episode_number}集剧本】
{current_script}

【格式要求】
- 对话格式：角色名：台词（中文冒号）
- 动作描写一律用 △ 开头
- 场景头格式：如 1-1 客厅 日 内
- 全中文，禁止出现英文字母
请直接输出修改后的完整剧本。"""
        self.screenwriter.clear_conversation()
        try:
            new_script = self.screenwriter._chat_multi_turn(
                rewrite_prompt, temperature=0.7, continue_conversation=False, print_prompt=False
            )
            new_script = clean_script(new_script)
            if new_script:
                episode.full_script = ensure_action_triangles(new_script)
                return True
        except Exception as e:
            self._log(f"第{episode_number}集根据审稿意见重写失败: {e}")
        return False
    
    def run_full(
        self,
        user_idea: str,
        sample_strategy: SelectStrategy = SelectStrategy.AUTO,
        manual_sample_ids: Optional[List[str]] = None,
        episodes_per_batch: Optional[int] = None,
        total_episodes: Optional[int] = None
    ) -> Bible:
        """
        执行完整的工作流
        
        Args:
            user_idea: 用户创意概念
            sample_strategy: 样本选择策略
            manual_sample_ids: 手动指定的样本ID
            episodes_per_batch: 每批生成的集数
        
        Returns:
            完成的Bible（包含所有剧集）
        """
        if episodes_per_batch:
            self.config.drama.episodes_per_batch = episodes_per_batch
        
        # 1. 创意阶段
        bible = self.run_ideation(
            user_idea,
            sample_strategy,
            manual_sample_ids,
            total_episodes=total_episodes
        )
        
        # 2. 循环撰写剧本
        while self.context.state != WorkflowState.COMPLETED:
            self.run_scripting_batch()
            
            if self.context.state == WorkflowState.ERROR:
                self._log(f"错误：{self.context.error_message}")
                break
        
        # 3. 最终保存
        if self.context.bible:
            self.context.bible.save(self.config.bible_path)
        
        return self.context.bible
    
    def export_script(
        self,
        output_path: Optional[str] = None,
        format: str = "markdown"
    ) -> str:
        """
        导出剧本
        
        Args:
            output_path: 输出路径
            format: 输出格式 (markdown/txt)
        
        Returns:
            输出文件路径
        """
        if self.context.bible is None:
            raise ValueError("没有可导出的剧本")
        
        bible = self.context.bible
        
        format = (format or "markdown").lower()

        if format == "docx":
            # DOCX导出
            from ..utils.docx_exporter import DocxExporter

            if output_path is None:
                output_path = os.path.join(
                    self.config.output_dir,
                    f"{bible.title}_剧本.docx"
                )

            self._log(f"正在导出DOCX剧本到：{output_path}")
            exporter = DocxExporter()
            exporter.export(bible, output_path)
            self._log(f"DOCX剧本已导出：{output_path}")
            return output_path

        if output_path is None:
            ext = ".md" if format == "markdown" else ".txt"
            output_path = os.path.join(
                self.config.output_dir,
                f"{bible.title}_剧本{ext}"
            )
        
        self._log(f"正在导出剧本到：{output_path}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            # 写入标题和梗概
            f.write(f"# {bible.title}\n\n")
            f.write(f"**类型**：{', '.join(bible.genre)}\n\n")
            f.write(f"**梗概**：{bible.synopsis}\n\n")
            f.write("---\n\n")
            
            # 写入角色介绍
            f.write("## 主要角色\n\n")
            for name, char in bible.characters.items():
                f.write(f"### {name}\n")
                f.write(f"- **身份**：{char.identity}\n")
                f.write(f"- **性格**：{char.personality}\n")
                f.write(f"- **技能**：{', '.join(char.skills)}\n\n")
            
            f.write("---\n\n")
            
            # 写入剧本
            f.write("## 剧本正文\n\n")
            for episode in sorted(bible.episodes, key=lambda x: x.number):
                f.write(f"### 第{episode.number}集\n\n")
                f.write(f"*{episode.synopsis}*\n\n")
                f.write(episode.full_script)
                f.write("\n\n---\n\n")
        
        self._log(f"剧本已导出：{output_path}")
        return output_path
    
    def get_progress(self) -> Dict[str, Any]:
        """获取当前进度"""
        bible = self.context.bible
        
        return {
            "state": self.context.state.value,
            "total_episodes": bible.total_episodes if bible else 0,
            "completed_episodes": len(self.context.completed_episodes),
            "current_batch": f"{self.context.current_batch_start}-{self.context.current_batch_end}",
            "selected_samples": self.context.selected_sample_ids,
            "title": bible.title if bible else "未开始"
        }
    
    def resume(self, bible_path: Optional[str] = None) -> Bible:
        """
        从保存的Bible恢复工作流
        
        Args:
            bible_path: Bible文件路径
        
        Returns:
            加载的Bible
        """
        if bible_path is None:
            bible_path = self.config.bible_path
        
        if not os.path.exists(bible_path):
            raise FileNotFoundError(f"找不到Bible文件：{bible_path}")
        
        self._log(f"正在恢复工作流：{bible_path}")
        
        bible = Bible.load(bible_path)
        self.context.bible = bible
        self.context.completed_episodes = bible.episodes.copy()
        self.context.current_batch_start = bible.current_episode + 1
        
        if bible.current_episode >= bible.total_episodes:
            self.context.state = WorkflowState.COMPLETED
        else:
            self.context.state = WorkflowState.SCRIPTING
        
        self._log(f"已恢复：《{bible.title}》，当前进度：{bible.current_episode}/{bible.total_episodes}集")
        
        return bible
