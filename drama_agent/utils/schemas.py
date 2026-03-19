"""
JSON Schema 定义
用于 Claude 结构化输出约束

参考文档：https://platform.claude.com/docs/zh-CN/build-with-claude/structured-outputs
"""
from typing import Dict, Any


# ========== 故事梗概 Schema ==========
SYNOPSIS_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "剧名（要吸引眼球）"
        },
        "genre": {
            "type": "array",
            "items": {"type": "string"},
            "description": "类型标签列表"
        },
        "target_audience": {
            "type": "string",
            "enum": ["女频", "男频"],
            "description": "目标受众"
        },
        "synopsis": {
            "type": "string",
            "description": "故事梗概，80字左右，包含主角姓名、目标、阻碍、亮点"
        },
        "theme": {
            "type": "string",
            "description": "核心主题"
        },
        "hook_points": {
            "type": "array",
            "items": {"type": "string"},
            "description": "主要爽点列表"
        },
        "total_episodes": {
            "type": "integer",
            "description": "总集数，80-100之间"
        },
        "production_notes": {
            "type": "string",
            "description": "制作说明：主要场景和制作难度"
        }
    },
    "required": ["title", "genre", "target_audience", "synopsis", "total_episodes"],
    "additionalProperties": False
}


# ========== 角色设定 Schema ==========
CHARACTER_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "description": "角色名"
        },
        "archetype": {
            "type": "string",
            "enum": ["protagonist", "love_interest", "antagonist", "supporting", "minor"],
            "description": "角色原型"
        },
        "identity": {
            "type": "string",
            "description": "身份（一句话）"
        },
        "age": {
            "type": "string",
            "description": "年龄（数字字符串，如18）"
        },
        "personality": {
            "type": "string",
            "description": "性格（几个词）"
        },
        "background": {
            "type": "string",
            "description": "背景（一两句）"
        },
        "core_goal": {
            "type": "string",
            "description": "核心目标（一句话）"
        },
        "memory_point": {
            "type": "string",
            "description": "记忆点（观众能记住的特点）"
        },
        "skills": {
            "type": "array",
            "items": {"type": "string"},
            "description": "技能列表"
        },
        "secrets": {
            "type": "array",
            "items": {"type": "string"},
            "description": "隐藏秘密（用于反转）"
        },
        "arc": {
            "type": "string",
            "description": "成长弧线（一句话）"
        }
    },
    "required": ["name", "archetype", "identity", "age", "personality", "background"],
    "additionalProperties": False
}


# 角色关系 Schema
RELATIONSHIP_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "character1": {
            "type": "string",
            "description": "角色A"
        },
        "character2": {
            "type": "string",
            "description": "角色B"
        },
        "relation_type": {
            "type": "string",
            "description": "关系类型"
        },
        "dynamic": {
            "type": "string",
            "description": "关系发展（一句话）"
        }
    },
    "required": ["character1", "character2", "relation_type", "dynamic"],
    "additionalProperties": False
}


# 完整的角色设定响应 Schema
CHARACTERS_RESPONSE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "characters": {
            "type": "array",
            "items": CHARACTER_SCHEMA,
            "description": "角色列表"
        },
        "relationships": {
            "type": "array",
            "items": RELATIONSHIP_SCHEMA,
            "description": "角色关系列表"
        }
    },
    "required": ["characters", "relationships"],
    "additionalProperties": False
}


# ========== 分集大纲 Schema ==========
BEAT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "episode": {
            "type": "integer",
            "description": "集数"
        },
        "synopsis": {
            "type": "string",
            "description": "本集剧情概要，30-60字一小段，只写爆点/关键动作，不要写小说"
        },
        "ending_hook": {
            "type": "string",
            "description": "本集结尾钩子，一句话20字内，留悬念/爆点"
        },
        "hook_type": {
            "type": "string",
            "enum": [
                "face_slap", "identity_reveal", "reversal", "cliffhanger",
                "resolution", "betrayal", "reunion", "confrontation",
                "discovery", "sacrifice", "revenge", "romance"
            ],
            "description": "钩子类型"
        },
        "key_conflict": {
            "type": "string",
            "description": "本集核心冲突"
        }
    },
    "required": ["episode", "synopsis", "ending_hook", "hook_type"],
    "additionalProperties": False
}


# 分集大纲响应 Schema
BEAT_SHEET_RESPONSE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "beats": {
            "type": "array",
            "items": BEAT_SCHEMA,
            "description": "分集大纲列表"
        }
    },
    "required": ["beats"],
    "additionalProperties": False
}


# ========== 剧本审核 Schema ==========
REVIEW_FEEDBACK_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "passed": {
            "type": "boolean",
            "description": "是否通过审核"
        },
        "hook_score": {
            "type": "number",
            "description": "钩子/爆点评分（0-10）"
        },
        "rhythm_score": {
            "type": "number",
            "description": "节奏评分（0-10）"
        },
        "climax_score": {
            "type": "number",
            "description": "爆点评分（0-10）"
        },
        "plot_score": {
            "type": "number",
            "description": "剧情评分（0-10）"
        },
        "dialogue_score": {
            "type": "number",
            "description": "对话评分（0-10）"
        },
        "ai_tone_score": {
            "type": "number",
            "description": "AI味评分（0-10，越高越好）"
        },
        "hooks_found": {
            "type": "array",
            "items": {"type": "string"},
            "description": "发现的爽点类型"
        },
        "ending_hook_type": {
            "type": "string",
            "description": "结尾钩子类型"
        },
        "weaknesses": {
            "type": "array",
            "items": {"type": "string"},
            "description": "缺点列表"
        },
        "rewrite_suggestions": {
            "type": "string",
            "description": "重写建议"
        },
        "format_issues": {
            "type": "array",
            "items": {"type": "string"},
            "description": "格式问题"
        },
        "word_count": {
            "type": "integer",
            "description": "字数"
        },
        "word_ok": {
            "type": "boolean",
            "description": "字数是否符合要求"
        },
        "scene_count": {
            "type": "integer",
            "description": "场景数"
        },
        "scene_ok": {
            "type": "boolean",
            "description": "场景数是否符合要求"
        }
    },
    "required": ["passed", "hook_score"],
    "additionalProperties": False
}


# ========== 辅助函数 ==========

def get_schema_for_task(task_name: str) -> Dict[str, Any]:
    """
    根据任务名称获取对应的 JSON Schema
    
    Args:
        task_name: 任务名称
            - "synopsis": 故事梗概
            - "characters": 角色设定
            - "beat_sheet": 分集大纲
            - "review": 审核反馈
    
    Returns:
        对应的 JSON Schema
    """
    schemas = {
        "synopsis": SYNOPSIS_SCHEMA,
        "characters": CHARACTERS_RESPONSE_SCHEMA,
        "beat_sheet": BEAT_SHEET_RESPONSE_SCHEMA,
        "review": REVIEW_FEEDBACK_SCHEMA,
    }
    
    if task_name not in schemas:
        raise ValueError(f"未知的任务名称：{task_name}，可用的任务：{list(schemas.keys())}")
    
    return schemas[task_name]


def validate_schema_compatibility(schema: Dict[str, Any]) -> bool:
    """
    验证 Schema 是否符合 Claude 结构化输出的要求
    
    限制：
    - 不支持递归 schema
    - 不支持枚举中的复杂类型
    - 不支持外部 $ref
    - 不支持数值约束（minimum, maximum 等）
    - additionalProperties 必须为 False
    
    Returns:
        是否兼容
    """
    # 基本检查
    if schema.get("type") != "object":
        return True  # 非对象类型暂不检查
    
    # 检查 additionalProperties
    if schema.get("additionalProperties") is not False:
        print(f"[Schema警告] additionalProperties 应该设置为 False")
        return False
    
    # 检查 required
    if "required" not in schema:
        print(f"[Schema警告] 缺少 required 字段")
    
    # 递归检查嵌套的 properties
    properties = schema.get("properties", {})
    for name, prop in properties.items():
        if prop.get("type") == "object":
            if not validate_schema_compatibility(prop):
                return False
        elif prop.get("type") == "array":
            items = prop.get("items", {})
            if items.get("type") == "object":
                if not validate_schema_compatibility(items):
                    return False
    
    return True

