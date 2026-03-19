"""
分步创作流程：每步展示 → 可编辑/多轮对话 → 确认后进入下一步。
流程：输入创意 → 灵感 → 梗概 → 总体大纲 → 人设(后台审核+自动修改) → 多集大纲 → 分集大纲(每5集一卡) → 剧本(每5集一卡，审稿/撰写简化)。
"""
from typing import Any, Dict, Optional, Callable
from pathlib import Path


# 步骤标识：next_step 取值，用于后台执行单步
STEP_FROM_IDEA = "from_idea"
STEP_FROM_INSPIRATION = "from_inspiration"
STEP_FROM_SYNOPSIS = "from_synopsis"
STEP_FROM_OUTLINE = "from_outline"
STEP_FROM_CHARACTERS = "from_characters"
STEP_FROM_MULTI_OUTLINE = "from_multi_outline"
STEP_FROM_BEAT_SHEET = "from_beat_sheet"
STEP_FROM_SCRIPTING_CHUNK = "from_scripting_chunk"

# 展示阶段：workflow_phase 取值（用户看到的当前步骤）
PHASE_IDEA_ENTERED = "idea_entered"
PHASE_INSPIRATION = "inspiration"
PHASE_SYNOPSIS = "synopsis"
PHASE_OUTLINE = "outline"
PHASE_CHARACTERS = "characters"
PHASE_MULTI_OUTLINE = "multi_outline"
PHASE_BEAT_SHEET = "beat_sheet"
PHASE_SCRIPTING = "scripting"
PHASE_COMPLETED = "completed"

# 阶段顺序（用于“下一步”映射）
PHASE_ORDER = [
    PHASE_IDEA_ENTERED,
    PHASE_INSPIRATION,
    PHASE_SYNOPSIS,
    PHASE_OUTLINE,
    PHASE_CHARACTERS,
    PHASE_MULTI_OUTLINE,
    PHASE_BEAT_SHEET,
    PHASE_SCRIPTING,
    PHASE_COMPLETED,
]

# 当前阶段 → 点击「确认并继续」后要执行的后台步骤
PHASE_TO_NEXT_STEP: Dict[str, str] = {
    PHASE_IDEA_ENTERED: STEP_FROM_IDEA,
    PHASE_INSPIRATION: STEP_FROM_INSPIRATION,
    PHASE_SYNOPSIS: STEP_FROM_SYNOPSIS,
    PHASE_OUTLINE: STEP_FROM_OUTLINE,
    PHASE_CHARACTERS: STEP_FROM_CHARACTERS,
    PHASE_MULTI_OUTLINE: STEP_FROM_MULTI_OUTLINE,
    PHASE_BEAT_SHEET: STEP_FROM_BEAT_SHEET,  # 仅当 beat_sheet 最后一 chunk 确认后才是 from_scripting_chunk，见 UI 逻辑
    PHASE_SCRIPTING: STEP_FROM_SCRIPTING_CHUNK,
}

# 每步展示名称（用于 UI 标题）
PHASE_LABELS: Dict[str, str] = {
    PHASE_IDEA_ENTERED: "输入创意",
    PHASE_INSPIRATION: "创作灵感",
    PHASE_SYNOPSIS: "故事梗概",
    PHASE_OUTLINE: "总体大纲",
    PHASE_CHARACTERS: "人物设定",
    PHASE_MULTI_OUTLINE: "多集大纲",
    PHASE_BEAT_SHEET: "分集大纲",
    PHASE_SCRIPTING: "剧本撰写",
    PHASE_COMPLETED: "已完成",
}

# 分步流程每批集数
STEPPED_BEAT_SHEET_CHUNK_SIZE = 5
STEPPED_SCRIPT_CHUNK_SIZE = 5


def get_beat_sheet_chunk_range(chunk_index: int, total_episodes: int):
    """分集大纲当前 chunk 的 [start, end] 集数（1-based）。"""
    start = chunk_index * STEPPED_BEAT_SHEET_CHUNK_SIZE + 1
    end = min(start + STEPPED_BEAT_SHEET_CHUNK_SIZE - 1, total_episodes)
    return start, end


def get_script_chunk_range(script_chunk_end: int, total_episodes: int):
    """剧本当前已写完的 chunk 对应的 [start, end]（script_chunk_end 为上一批结束集数，0 表示尚未写任何一集）。"""
    start = script_chunk_end + 1
    end = min(script_chunk_end + STEPPED_SCRIPT_CHUNK_SIZE, total_episodes)
    return start, end
