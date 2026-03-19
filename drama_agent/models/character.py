"""
数据模型 - 人物角色
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class CharacterArchetype(Enum):
    """角色原型"""
    PROTAGONIST = "protagonist"          # 主角（大女主/大男主）
    LOVE_INTEREST = "love_interest"      # 男主/女主
    ANTAGONIST = "antagonist"            # 反派
    SUPPORTING = "supporting"            # 配角
    MINOR = "minor"                      # 次要角色
    COMIC_RELIEF = "comic_relief"        # 搞笑担当
    MENTOR = "mentor"                    # 导师
    SIDEKICK = "sidekick"                # 跟班


class CharacterStatus(Enum):
    """角色状态"""
    ACTIVE = "active"                    # 活跃
    INACTIVE = "inactive"                # 暂时离场
    DECEASED = "deceased"                # 已死亡
    REFORMED = "reformed"                # 已洗白
    EXPOSED = "exposed"                  # 已被揭穿


@dataclass
class CharacterRelationship:
    """人物关系"""
    target: str                          # 关系对象
    relation_type: str                   # 关系类型（儿子、情敌、闺蜜等）
    sentiment: str                       # 情感倾向（正面/负面/中立）
    notes: str = ""                      # 备注


@dataclass
class Character:
    """角色定义"""
    name: str                            # 角色名
    identity: str                        # 身份描述
    archetype: CharacterArchetype        # 角色原型
    age: Optional[int] = None            # 年龄
    appearance: str = ""                 # 外貌描述
    personality: str = ""                # 性格特点
    background: str = ""                 # 背景故事
    skills: List[str] = field(default_factory=list)           # 技能列表
    relationships: List[CharacterRelationship] = field(default_factory=list)  # 人物关系
    status: CharacterStatus = CharacterStatus.ACTIVE          # 当前状态
    secrets: List[str] = field(default_factory=list)          # 隐藏秘密（用于后续揭示）
    arc: str = ""                        # 角色弧线描述
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "name": self.name,
            "identity": self.identity,
            "archetype": self.archetype.value,
            "age": self.age,
            "appearance": self.appearance,
            "personality": self.personality,
            "background": self.background,
            "skills": self.skills,
            "relationships": [
                {
                    "target": r.target,
                    "relation_type": r.relation_type,
                    "sentiment": r.sentiment,
                    "notes": r.notes
                }
                for r in self.relationships
            ],
            "status": self.status.value,
            "secrets": self.secrets,
            "arc": self.arc
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Character":
        """从字典创建"""
        relationships = [
            CharacterRelationship(**r) for r in data.get("relationships", [])
        ]
        return cls(
            name=data["name"],
            identity=data["identity"],
            archetype=CharacterArchetype(data["archetype"]),
            age=data.get("age"),
            appearance=data.get("appearance", ""),
            personality=data.get("personality", ""),
            background=data.get("background", ""),
            skills=data.get("skills", []),
            relationships=relationships,
            status=CharacterStatus(data.get("status", "active")),
            secrets=data.get("secrets", []),
            arc=data.get("arc", "")
        )
    
    def get_relationship_with(self, character_name: str) -> Optional[CharacterRelationship]:
        """获取与特定角色的关系"""
        for rel in self.relationships:
            if rel.target == character_name:
                return rel
        return None
    
    def add_relationship(self, relationship: CharacterRelationship):
        """添加人物关系"""
        # 如果已存在关系，更新它
        for i, rel in enumerate(self.relationships):
            if rel.target == relationship.target:
                self.relationships[i] = relationship
                return
        self.relationships.append(relationship)
    
    def update_status(self, new_status: CharacterStatus):
        """更新角色状态"""
        self.status = new_status
