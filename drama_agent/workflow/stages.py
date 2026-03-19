"""
工作流阶段与卡点定义
用于进度条展示和卡点暂停/继续。
"""
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class StageStep:
    """单个阶段步骤"""
    id: str
    name: str
    weight: float  # 占整体进度权重 (0~1)，创意阶段总和建议 0.18，剧本阶段 0.82
    is_checkpoint: bool = False  # 是否为卡点（可在此暂停，需用户确认后继续）


# 创意策划阶段步骤（约占总进度 18%）
IDEATION_STAGES: List[StageStep] = [
    StageStep("sample", "选择参考样本", 0.01),
    StageStep("trend", "搜索红果短剧趋势", 0.01),
    StageStep("inspiration", "生成创作灵感", 0.02),
    StageStep("synopsis", "生成故事梗概", 0.02),
    StageStep("outline", "生成总体大纲", 0.02),
    StageStep("characters", "创建人物设定", 0.03),
    StageStep("review_ideation", "审核梗概与人设", 0.02),
    StageStep("multi_outline", "生成多集大纲", 0.02),
    StageStep("beat_sheet", "生成分集大纲", 0.02, is_checkpoint=True),  # 卡点：创意完成后可暂停
]

# 剧本撰写阶段：按“批”推进，每批占 (0.82 / 总批次数)
def get_scripting_stage_weight(batch_index: int, total_batches: int) -> float:
    """剧本阶段每批权重。batch_index 从 0 开始。"""
    if total_batches <= 0:
        return 0.0
    return 0.82 / total_batches


def ideation_progress_for_step(step_id: str) -> float:
    """创意阶段完成到 step_id 时的累计进度 (0~0.18)。"""
    total = 0.0
    for s in IDEATION_STAGES:
        total += s.weight
        if s.id == step_id:
            return total
    return 0.18


def get_checkpoint_steps() -> List[str]:
    """返回所有卡点 step id 列表。"""
    return [s.id for s in IDEATION_STAGES if s.is_checkpoint]


def total_ideation_weight() -> float:
    return sum(s.weight for s in IDEATION_STAGES)
