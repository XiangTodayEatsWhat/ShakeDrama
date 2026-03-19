"""
数据模型 - 世界观圣经 (Bible)
"""
import json
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime

from .character import Character
from .episode import Episode, BeatSheet


def _parse_episode_value(value) -> Optional[int]:
    """解析集数，兼容 35 / "35" / "35-50" / "第35集" / "第35-50集"。"""
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return int(value)

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None

        # 单集写法：35 / 第35集
        single_match = re.match(r"^第?\s*(\d+)\s*集?$", text)
        if single_match:
            return int(single_match.group(1))

        # 区间写法：35-50 / 第35-50集 / 35~50 / 35到50
        range_match = re.match(r"^第?\s*(\d+)\s*[-~～到至]\s*(\d+)\s*集?$", text)
        if range_match:
            return int(range_match.group(1))

        # 尝试直接转数字字符串
        try:
            return int(text)
        except ValueError:
            return None

    return None




@dataclass
class PlotPoint:
    """重要剧情点"""
    episode: int                          # 发生集数
    description: str                      # 描述
    importance: str                       # 重要性：major/minor
    characters_involved: List[str]        # 涉及角色
    consequences: List[str] = field(default_factory=list)  # 后续影响
    
    def to_dict(self) -> dict:
        return {
            "episode": self.episode,
            "description": self.description,
            "importance": self.importance,
            "characters_involved": self.characters_involved,
            "consequences": self.consequences
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "PlotPoint":
        return cls(
            episode=data["episode"],
            description=data["description"],
            importance=data["importance"],
            characters_involved=data["characters_involved"],
            consequences=data.get("consequences", [])
        )


@dataclass
class Foreshadow:
    """伏笔"""
    planted_episode: int                  # 埋设集数
    description: str                      # 伏笔内容
    expected_payoff_episode: Optional[int] = None  # 预期回收集数
    actual_payoff_episode: Optional[int] = None    # 实际回收集数
    is_resolved: bool = False             # 是否已回收
    resolution: str = ""                  # 回收方式
    
    def to_dict(self) -> dict:
        return {
            "planted_episode": self.planted_episode,
            "description": self.description,
            "expected_payoff_episode": self.expected_payoff_episode,
            "actual_payoff_episode": self.actual_payoff_episode,
            "is_resolved": self.is_resolved,
            "resolution": self.resolution
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Foreshadow":
        return cls(
            planted_episode=int(data.get("planted_episode", 0) or 0),
            description=data.get("description", ""),
            expected_payoff_episode=_parse_episode_value(data.get("expected_payoff_episode")),
            actual_payoff_episode=_parse_episode_value(data.get("actual_payoff_episode")),
            is_resolved=data.get("is_resolved", False),
            resolution=data.get("resolution", "")
        )


@dataclass
class Bible:
    """
    世界观圣经 - 记录剧本的所有核心设定
    用于确保长文本的一致性
    """
    # 基本信息
    title: str                            # 剧名
    genre: List[str]                      # 类型标签（重生/豪门/爽文等）
    target_audience: str                  # 目标受众（女频/男频）
    synopsis: str                         # 故事梗概（主角+目标+阻碍+亮点，约80字）
    inspiration: str = ""                 # 创作灵感（头脑风暴，关键集数爆点）
    overall_outline: str = ""             # 总体大纲（故事背景、出场人物、阶段核心事件、关键悬念冲突与高光卡点）
    multi_episode_outline: str = ""       # 多集大纲（1-10, 10-30, 30-60, 60-end分段）
    theme: str = ""                       # 主题
    
    # 角色
    characters: Dict[str, Character] = field(default_factory=dict)
    protagonist_name: str = ""            # 主角名
    
    # 剧情进度
    total_episodes: int = 80              # 总集数
    current_episode: int = 0              # 当前已完成集数
    
    # 大纲
    beat_sheet: Optional[BeatSheet] = None
    
    # 已生成的剧集
    episodes: List[Episode] = field(default_factory=list)
    
    # 剧情追踪
    plot_points: List[PlotPoint] = field(default_factory=list)    # 重要剧情点
    foreshadowing: List[Foreshadow] = field(default_factory=list)  # 伏笔追踪
    
    # 当前状态
    current_location: str = ""            # 当前主要场景
    active_conflicts: List[str] = field(default_factory=list)     # 活跃冲突
    resolved_conflicts: List[str] = field(default_factory=list)   # 已解决冲突
    
    # 参考样本
    reference_samples: List[str] = field(default_factory=list)    # 参考的样本ID
    
    # 元数据
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
    
    def add_character(self, character: Character):
        """添加角色"""
        self.characters[character.name] = character
        self.updated_at = datetime.now().isoformat()
    
    def get_character(self, name: str) -> Optional[Character]:
        """获取角色"""
        return self.characters.get(name)
    
    def add_episode(self, episode: Episode):
        """添加已完成的剧集"""
        self.episodes.append(episode)
        self.current_episode = max(self.current_episode, episode.number)
        self.updated_at = datetime.now().isoformat()
    
    def add_plot_point(self, plot_point: PlotPoint):
        """添加重要剧情点"""
        self.plot_points.append(plot_point)
        self.updated_at = datetime.now().isoformat()
    
    def add_foreshadow(self, foreshadow: Foreshadow):
        """添加伏笔"""
        self.foreshadowing.append(foreshadow)
        self.updated_at = datetime.now().isoformat()
    
    def resolve_foreshadow(self, description: str, episode: int, resolution: str):
        """回收伏笔"""
        for fs in self.foreshadowing:
            if fs.description == description and not fs.is_resolved:
                fs.is_resolved = True
                fs.actual_payoff_episode = episode
                fs.resolution = resolution
                self.updated_at = datetime.now().isoformat()
                return
    
    def get_unresolved_foreshadows(self) -> List[Foreshadow]:
        """获取未回收的伏笔"""
        return [fs for fs in self.foreshadowing if not fs.is_resolved]
    
    def get_foreshadows_due(self, episode: int) -> List[Foreshadow]:
        """获取需要在指定集数回收的伏笔"""
        ep_int = int(episode)
        result = []
        for fs in self.foreshadowing:
            if fs.is_resolved:
                continue
            exp_int = _parse_episode_value(fs.expected_payoff_episode)
            if exp_int is not None and exp_int <= ep_int:
                result.append(fs)
        return result
    
    def update_conflict(self, conflict: str, resolved: bool = False):
        """更新冲突状态"""
        if resolved:
            if conflict in self.active_conflicts:
                self.active_conflicts.remove(conflict)
            if conflict not in self.resolved_conflicts:
                self.resolved_conflicts.append(conflict)
        else:
            if conflict not in self.active_conflicts:
                self.active_conflicts.append(conflict)
        self.updated_at = datetime.now().isoformat()
    
    # 编剧上下文里「活跃冲突」「需回收伏笔」最多各展示条数，避免 prompt 只增不减
    CONTEXT_MAX_ACTIVE_CONFLICTS = 8
    CONTEXT_MAX_DUE_FORESHADOWS = 8

    def get_context_for_episode(self, episode_num: int) -> dict:
        """获取写作指定集数时需要的上下文（活跃冲突与需回收伏笔做数量上限，避免越来越多）"""
        # 获取前几集的内容摘要
        recent_episodes = [
            ep for ep in self.episodes 
            if ep.number >= episode_num - 3 and ep.number < episode_num
        ]
        
        # 获取需要回收的伏笔，按预计回收集数排序，只取最近/最该回收的 N 条
        due_foreshadows = self.get_foreshadows_due(episode_num)
        def _ep_num(x):
            return _parse_episode_value(x) or 0

        due_foreshadows = sorted(
            due_foreshadows,
            key=lambda fs: (_ep_num(fs.expected_payoff_episode), _ep_num(fs.planted_episode))
        )[: self.CONTEXT_MAX_DUE_FORESHADOWS]
        
        # 活跃冲突只取最近 N 条（列表为 append 顺序，末尾为最近）
        active_conflicts_capped = self.active_conflicts[-self.CONTEXT_MAX_ACTIVE_CONFLICTS :] if self.active_conflicts else []
        
        # 获取当前节拍
        current_beat = self.beat_sheet.get_beat(episode_num) if self.beat_sheet else None
        
        return {
            "current_episode": episode_num,
            "recent_episodes": [ep.to_dict() for ep in recent_episodes],
            "due_foreshadows": [fs.to_dict() for fs in due_foreshadows],
            "current_beat": current_beat,
            "active_conflicts": active_conflicts_capped,
            "character_statuses": {
                name: char.status.value 
                for name, char in self.characters.items()
            }
        }
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "title": self.title,
            "genre": self.genre,
            "target_audience": self.target_audience,
            "inspiration": self.inspiration,
            "synopsis": self.synopsis,
            "overall_outline": self.overall_outline,
            "multi_episode_outline": self.multi_episode_outline,
            "theme": self.theme,
            "characters": {
                name: char.to_dict() 
                for name, char in self.characters.items()
            },
            "protagonist_name": self.protagonist_name,
            "total_episodes": self.total_episodes,
            "current_episode": self.current_episode,
            "beat_sheet": self.beat_sheet.to_dict() if self.beat_sheet else None,
            "episodes": [ep.to_dict() for ep in self.episodes],
            "plot_points": [pp.to_dict() for pp in self.plot_points],
            "foreshadowing": [fs.to_dict() for fs in self.foreshadowing],
            "current_location": self.current_location,
            "active_conflicts": self.active_conflicts,
            "resolved_conflicts": self.resolved_conflicts,
            "reference_samples": self.reference_samples,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Bible":
        """从字典创建"""
        characters = {
            name: Character.from_dict(char_data)
            for name, char_data in data.get("characters", {}).items()
        }
        
        episodes = [
            Episode.from_dict(ep_data) 
            for ep_data in data.get("episodes", [])
        ]
        
        beat_sheet = BeatSheet.from_dict(data["beat_sheet"]) if data.get("beat_sheet") else None
        
        plot_points = [
            PlotPoint.from_dict(pp_data)
            for pp_data in data.get("plot_points", [])
        ]
        
        foreshadowing = [
            Foreshadow.from_dict(fs_data)
            for fs_data in data.get("foreshadowing", [])
        ]
        
        bible = cls(
            title=data["title"],
            genre=data.get("genre", []),
            target_audience=data.get("target_audience", "通用"),
            inspiration=data.get("inspiration", ""),
            synopsis=data.get("synopsis", ""),
            overall_outline=data.get("overall_outline", ""),
            multi_episode_outline=data.get("multi_episode_outline", ""),
            theme=data.get("theme", ""),
            characters=characters,
            protagonist_name=data.get("protagonist_name", ""),
            total_episodes=data.get("total_episodes", 80),
            current_episode=data.get("current_episode", 0),
            beat_sheet=beat_sheet,
            episodes=episodes,
            plot_points=plot_points,
            foreshadowing=foreshadowing,
            current_location=data.get("current_location", ""),
            active_conflicts=data.get("active_conflicts", []),
            resolved_conflicts=data.get("resolved_conflicts", []),
            reference_samples=data.get("reference_samples", []),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", "")
        )
        
        return bible
    
    def save(self, filepath: str):
        """保存到文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load(cls, filepath: str) -> "Bible":
        """从文件加载"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def get_summary(self) -> str:
        """获取剧本摘要（用于提示词）"""
        char_summaries = []
        for name, char in self.characters.items():
            char_summaries.append(f"- {name}：{char.identity}，{char.archetype.value}")
        
        return f"""
【剧名】{self.title}
【类型】{', '.join(self.genre)}
【梗概】{self.synopsis}
【主角】{self.protagonist_name}
【主要角色】
{chr(10).join(char_summaries)}
【当前进度】第{self.current_episode}集 / 共{self.total_episodes}集
【活跃冲突】{', '.join(self.active_conflicts) if self.active_conflicts else '无'}
"""
