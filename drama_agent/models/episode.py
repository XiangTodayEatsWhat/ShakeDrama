"""
数据模型 - 剧集
"""
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class SceneTime(Enum):
    """场景时间"""
    DAY = "日"
    NIGHT = "夜"


class SceneLocation(Enum):
    """场景位置"""
    INTERIOR = "内"
    EXTERIOR = "外"


@dataclass
class Scene:
    """场景"""
    episode: int                         # 所属集数
    scene_number: int                    # 场景序号
    location: str                        # 地点
    time: SceneTime                      # 时间
    interior: SceneLocation              # 内/外
    content: str                         # 场景内容（包含对话、动作等）
    
    def get_header(self) -> str:
        """生成场景头"""
        return f"{self.episode}-{self.scene_number} {self.location} {self.time.value} {self.interior.value}"
    
    def to_dict(self) -> dict:
        return {
            "episode": self.episode,
            "scene_number": self.scene_number,
            "location": self.location,
            "time": self.time.value,
            "interior": self.interior.value,
            "content": self.content
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Scene":
        raw_time = data["time"]
        _time_compat = {"晨": "日", "暮": "夜"}
        return cls(
            episode=data["episode"],
            scene_number=data["scene_number"],
            location=data["location"],
            time=SceneTime(_time_compat.get(raw_time, raw_time)),
            interior=SceneLocation(data["interior"]),
            content=data["content"]
        )


@dataclass
class EpisodeHook:
    """集末钩子/爽点"""
    hook_type: str                       # 爽点类型
    description: str                     # 描述
    intensity: int                       # 强度 1-10
    cliffhanger: bool = False            # 是否是悬念
    
    def to_dict(self) -> dict:
        return {
            "hook_type": self.hook_type,
            "description": self.description,
            "intensity": self.intensity,
            "cliffhanger": self.cliffhanger
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "EpisodeHook":
        return cls(
            hook_type=data["hook_type"],
            description=data["description"],
            intensity=data["intensity"],
            cliffhanger=data.get("cliffhanger", False)
        )


@dataclass
class Episode:
    """剧集"""
    number: int                          # 集数
    title: str                           # 集标题（可选）
    synopsis: str                        # 本集梗概
    scenes: List[Scene] = field(default_factory=list)         # 场景列表
    hooks: List[EpisodeHook] = field(default_factory=list)    # 爽点列表
    ending_hook: Optional[EpisodeHook] = None                 # 结尾钩子
    full_script: str = ""                # 完整剧本文本
    hook_score: Optional[float] = None   # 爽点评分
    review_feedback: Optional[dict] = None  # 审稿反馈（包含原文、分数、意见等）
    
    def to_dict(self) -> dict:
        return {
            "number": self.number,
            "title": self.title,
            "synopsis": self.synopsis,
            "scenes": [s.to_dict() for s in self.scenes],
            "hooks": [h.to_dict() for h in self.hooks],
            "ending_hook": self.ending_hook.to_dict() if self.ending_hook else None,
            "full_script": self.full_script,
            "hook_score": self.hook_score,
            "review_feedback": self.review_feedback
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Episode":
        scenes = [Scene.from_dict(s) for s in data.get("scenes", [])]
        hooks = [EpisodeHook.from_dict(h) for h in data.get("hooks", [])]
        ending_hook = EpisodeHook.from_dict(data["ending_hook"]) if data.get("ending_hook") else None
        
        return cls(
            number=data["number"],
            title=data.get("title", ""),
            synopsis=data.get("synopsis", ""),
            scenes=scenes,
            hooks=hooks,
            ending_hook=ending_hook,
            full_script=data.get("full_script", ""),
            hook_score=data.get("hook_score"),
            review_feedback=data.get("review_feedback")
        )


@dataclass
class BeatSheet:
    """分集大纲（节拍表）"""
    episodes: List[dict] = field(default_factory=list)
    
    def add_beat(self, episode_num: int, synopsis: str, ending_hook: str, hook_type: str):
        """添加一个节拍"""
        self.episodes.append({
            "episode": episode_num,
            "synopsis": synopsis,
            "ending_hook": ending_hook,
            "hook_type": hook_type
        })
    
    def get_beat(self, episode_num: int) -> Optional[dict]:
        """获取指定集的节拍"""
        for beat in self.episodes:
            if beat["episode"] == episode_num:
                return beat
        return None
    
    def to_dict(self) -> dict:
        return {"episodes": self.episodes}
    
    @classmethod
    def from_dict(cls, data: dict) -> "BeatSheet":
        beat_sheet = cls()
        beat_sheet.episodes = data.get("episodes", [])
        return beat_sheet
