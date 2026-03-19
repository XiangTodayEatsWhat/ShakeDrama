"""
记忆官Agent (Memory Manager) - 负责管理长文本一致性
"""
import json
import re
from typing import Optional, List, Dict, Any

from .base_agent import BaseAgent
from ..models import Bible, Episode, PlotPoint, Foreshadow, Character
from ..config import get_config


def _normalize_payoff_episode(value) -> Optional[int]:
    """把 LLM 产出的回收集数归一为单集数；区间时取起始集。"""
    if value is None:
        return None

    if isinstance(value, (int, float)):
        num = int(value)
        return num if num > 0 else None

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None

        single_match = re.match(r"^第?\s*(\d+)\s*集?$", text)
        if single_match:
            num = int(single_match.group(1))
            return num if num > 0 else None

        range_match = re.match(r"^第?\s*(\d+)\s*[-~～到至]\s*(\d+)\s*集?$", text)
        if range_match:
            start = int(range_match.group(1))
            return start if start > 0 else None

        try:
            num = int(text)
            return num if num > 0 else None
        except ValueError:
            return None

    return None


class MemoryManagerAgent(BaseAgent):
    """
    记忆官Agent
    职责：
    1. 维护世界观圣经（Bible）
    2. 追踪伏笔的埋设和回收
    3. 更新人物状态和关系
    4. 确保长文本的一致性
    """
    
    def __init__(self):
        super().__init__("记忆官Agent")
        self.config = get_config()
    
    @property
    def system_prompt(self) -> str:
        return """你是一位细心的短剧记忆管理员。你的职责是追踪剧情发展，确保前后一致。

【核心职责】
1. 记录剧情中的重要事件
2. 追踪埋下的伏笔
3. 提醒何时需要回收伏笔
4. 更新角色状态变化
5. 维护人物关系图谱

【伏笔管理原则】
- 不要埋太多伏笔！控制在少而精，每10-15集最多埋设1-2个新伏笔
- 重要的伏笔通常在15-30集后回收
- 不要让伏笔悬置太久（超过40集要回收）
- 每个伏笔回收时要有"恍然大悟"的感觉
- 小伏笔可以快速回收（5-10集），大伏笔要铺垫

【状态更新原则】
- 角色死亡/离场要明确标记
- 关系变化（敌变友、友变敌）要记录
- 秘密揭露后要更新
- 地点转换要追踪"""

    def analyze_episode(
        self,
        episode: Episode,
        bible: Bible
    ) -> Dict[str, Any]:
        """
        分析剧集内容，提取需要记录的信息
        
        Args:
            episode: 要分析的剧集
            bible: 世界观圣经
        
        Returns:
            分析结果
        """
        self.log(f"正在分析第{episode.number}集...")
        
        prompt = f"""请分析以下剧集内容，提取需要记录的信息。

【剧名】{bible.title}
【集数】第{episode.number}集

【剧本内容】
{episode.full_script}

【当前角色状态】
{json.dumps({name: char.status.value for name, char in bible.characters.items()}, ensure_ascii=False)}

【未回收的伏笔】
{json.dumps([fs.to_dict() for fs in bible.get_unresolved_foreshadows()], ensure_ascii=False)}

请以JSON格式返回分析结果：

【⚠️ JSON格式要求】
- 字符串中不要使用双引号"，用『』或「」代替
- 每个对象最后一个字段后不要加逗号
- 对象之间要有逗号（最后一个除外）
- 不要用markdown代码块包裹（不要```json）

{{
    "plot_points": [
        {{
            "description": "重要剧情点描述",
            "importance": "major/minor",
            "characters_involved": ["涉及的角色"],
            "consequences": ["可能的后续影响"]
        }}
    ],
    "new_foreshadows": [
        {{
            "description": "新埋下的伏笔（注意：控制数量，不要每集都埋伏笔！平均每10-15集埋1-2个即可）",
            "expected_payoff_episode": 预计回收集数（必须是单个整数，如35；禁止写35-50）
        }}
    ],
    "resolved_foreshadows": [
        {{
            "description": "回收的伏笔（要与之前的伏笔描述匹配）",
            "resolution": "回收方式"
        }}
    ],
    "character_updates": [
        {{
            "name": "角色名",
            "status_change": "新状态（如dead/inactive/reformed，没有变化则填null）",
            "relationship_changes": [
                {{
                    "target": "对方角色名",
                    "new_relation": "新关系类型",
                    "sentiment": "positive/negative/neutral"
                }}
            ]
        }}
    ],
    "new_conflicts": ["新产生的冲突"],
    "resolved_conflicts": ["已解决的冲突"],
    "location_change": "如果主要场景变化，填写新地点"
}}

【重要】
1. 确保JSON完整，所有数组和对象都要有完整的闭合括号！
2. 务必识别本批剧本中已解决的冲突、已回收的伏笔，填入 resolved_conflicts 与 resolved_foreshadows，避免活跃冲突和待回收伏笔只增不减。"""

        # 先拿原始回复，若大量英文或非 JSON（如模型拒绝/身份声明），则追加「好的，请继续生成」再要一次
        from ..utils.script_validator import is_mostly_english
        from ..utils.json_fixer import safe_json_loads

        self.log(f"正在调用LLM（尝试 1/3）...")
        raw = self.llm.chat_with_system(self.system_prompt, prompt, temperature=0.2, max_tokens=8000)
        need_followup = is_mostly_english(raw) or not (raw.strip().startswith("{") and "plot_points" in raw)
        if need_followup:
            self.log("  检测到回复大量英文或非JSON，追加「好的，请继续生成」...")
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": raw[:4000] + ("..." if len(raw) > 4000 else "")},
                {"role": "user", "content": "好的，请继续生成。请直接输出上述格式的JSON，不要其他说明。"},
            ]
            raw = self.llm.chat(messages, temperature=0.2, max_tokens=8000)
        result = safe_json_loads(raw, max_attempts=3)
        self.log(f"  分析完成：{len(result.get('plot_points', []))}个剧情点")
        return result
    
    def update_bible(
        self,
        bible: Bible,
        analysis: Dict[str, Any],
        episode_num: int
    ) -> Bible:
        """
        根据分析结果更新世界观圣经
        
        Args:
            bible: 世界观圣经
            analysis: 剧集分析结果
            episode_num: 集数
        
        Returns:
            更新后的Bible
        """
        self.log(f"正在更新世界观圣经...")
        
        # 1. 添加剧情点
        for pp in analysis.get("plot_points", []):
            plot_point = PlotPoint(
                episode=episode_num,
                description=pp["description"],
                importance=pp.get("importance", "minor"),
                characters_involved=pp.get("characters_involved", []),
                consequences=pp.get("consequences", [])
            )
            bible.add_plot_point(plot_point)
        
        # 2. 添加新伏笔
        for fs in analysis.get("new_foreshadows", []):
            normalized_payoff_episode = _normalize_payoff_episode(
                fs.get("expected_payoff_episode")
            )

            if fs.get("expected_payoff_episode") is not None and normalized_payoff_episode is None:
                self.log(
                    f"  伏笔回收集数格式无效，已忽略：{fs.get('expected_payoff_episode')}"
                )

            foreshadow = Foreshadow(
                planted_episode=episode_num,
                description=fs["description"],
                expected_payoff_episode=normalized_payoff_episode
            )
            bible.add_foreshadow(foreshadow)
        
        # 3. 回收伏笔
        for fs in analysis.get("resolved_foreshadows", []):
            bible.resolve_foreshadow(
                fs["description"],
                episode_num,
                fs.get("resolution", "")
            )
        
        # 4. 更新角色状态
        for update in analysis.get("character_updates", []):
            char = bible.get_character(update["name"])
            if char:
                # 更新状态
                if update.get("status_change"):
                    from ..models.character import CharacterStatus
                    try:
                        new_status = CharacterStatus(update["status_change"])
                        char.update_status(new_status)
                    except ValueError:
                        pass
                
                # 更新关系
                for rel_change in update.get("relationship_changes", []):
                    from ..models.character import CharacterRelationship
                    char.add_relationship(CharacterRelationship(
                        target=rel_change["target"],
                        relation_type=rel_change["new_relation"],
                        sentiment=rel_change.get("sentiment", "neutral")
                    ))
        
        # 5. 更新冲突
        for conflict in analysis.get("new_conflicts", []):
            bible.update_conflict(conflict, resolved=False)
        
        for conflict in analysis.get("resolved_conflicts", []):
            bible.update_conflict(conflict, resolved=True)
        
        # 6. 更新地点
        if analysis.get("location_change"):
            bible.current_location = analysis["location_change"]
        
        self.log(f"  世界观圣经更新完成")
        return bible
    
    def get_context_summary(
        self,
        bible: Bible,
        episode_num: int
    ) -> str:
        """
        获取写作特定集数的上下文摘要
        
        Args:
            bible: 世界观圣经
            episode_num: 目标集数
        
        Returns:
            上下文摘要文本
        """
        # 获取需要回收的伏笔
        due_foreshadows = bible.get_foreshadows_due(episode_num)
        
        # 获取最近的剧情点
        recent_plots = [
            pp for pp in bible.plot_points
            if pp.episode >= episode_num - 5 and pp.importance == "major"
        ]
        
        summary = f"""
【当前状态】第{episode_num}集
【主要场景】{bible.current_location or '未设定'}
【活跃冲突】{', '.join(bible.active_conflicts) if bible.active_conflicts else '无'}

【近期重要事件】
{chr(10).join([f'- 第{pp.episode}集：{pp.description}' for pp in recent_plots]) if recent_plots else '无'}

【待回收伏笔】
{chr(10).join([f'- {fs.description}（预计第{fs.expected_payoff_episode}集回收）' for fs in due_foreshadows]) if due_foreshadows else '无'}

【角色状态】
{chr(10).join([f'- {name}：{char.status.value}' for name, char in bible.characters.items()])}
"""
        return summary
    
    def run(
        self,
        episodes: List[Episode],
        bible: Bible
    ) -> Bible:
        """
        处理新剧集，更新世界观圣经
        
        Args:
            episodes: 新完成的剧集列表
            bible: 世界观圣经
        
        Returns:
            更新后的Bible
        """
        self.log("=" * 50)
        self.log(f"开始更新记忆，处理{len(episodes)}集")
        self.log("=" * 50)
        
        for episode in episodes:
            # 分析剧集
            analysis = self.analyze_episode(episode, bible)
            
            # 更新Bible
            bible = self.update_bible(bible, analysis, episode.number)
        
        # 保存Bible
        bible_path = self.config.bible_path
        bible.save(bible_path)
        self.log(f"世界观圣经已保存至：{bible_path}")
        
        self.log("=" * 50)
        self.log("记忆更新完成")
        self.log(f"  剧情点：{len(bible.plot_points)}个")
        self.log(f"  伏笔：{len(bible.foreshadowing)}个（{len(bible.get_unresolved_foreshadows())}个待回收）")
        self.log("=" * 50)
        
        return bible
