"""
样本选择器 - Agent智能选择要参考的样本
"""
from typing import List, Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass

from .sample_manager import SampleManager, SampleMetadata
from ..utils.llm_client import get_llm_client

# 写死的格式参考：摘自《十八岁太奶奶驾到》，只学格式
FORMAT_REFERENCE_SNIPPET = """1-1 礼堂 日 内
人物：容遇，颁奖人，纪舜英、主持人

△颁奖人给台上的容遇戴上红绸，所有人鼓掌。
主持人 VO: 容遇教授，5年间为我国突破了8个世界级难题，现颁发国家终身成就奖。
△容遇胸前戴着大红花，走到舞台中央。纪舜英走上台，将奖状递给容遇。
纪舜英：妈妈，你永远是我的骄傲。
△容遇摸了摸纪舜英的头。
容遇：谢谢英宝。
△容遇一惊，抬头望向屋顶。
容遇：英宝，小心!

1-2 宴会 夜 内
人物：容遇，宾客数名，容若瑶

△坐在沙发上的容遇打着盹突然醒过来，一脸疑惑地环顾四周。
容遇OS: 嗯?我刚不是死了吗?这是哪?
△容遇站起来，望向在议论她的人。
男宾客：你看，这就是容总和前妻生的女儿容遇。
△容遇转身，看到镜子中的自己。
容遇OS: 所以，我魂穿到了这同名同姓的少女身上。
△容若瑶笑容满面地迎上来。
容若瑶：姐姐，原来你在这啊。
△容若瑶将红酒递给容遇，假装不小心洒在容遇身上。
容若瑶（阴阳怪气）：诶，手滑了。
△容遇冷眼看着容若瑶，从服务生托盘中拿起一杯红酒，浇在容若瑶身上。
容遇：不好意思，我也手滑。"""


class SelectStrategy(Enum):
    """选择策略"""
    AUTO = "auto"           # Agent自动匹配
    MANUAL = "manual"       # 用户手动指定
    HYBRID = "hybrid"       # Agent推荐 + 用户确认
    NONE = "none"           # 不使用样本


@dataclass
class SelectionResult:
    """选择结果"""
    selected_ids: List[str]
    strategy_used: SelectStrategy
    reasoning: str
    format_reference: str


class SampleSelector:
    """
    样本选择器
    
    根据用户创意智能选择最合适的参考样本。
    注意：选择的样本仅用于格式/风格参考，不影响创意内容。
    """
    
    def __init__(self, sample_manager: SampleManager):
        self.sample_manager = sample_manager
        self.llm = get_llm_client()
    
    def select(
        self,
        user_idea: str,
        strategy: SelectStrategy = SelectStrategy.AUTO,
        manual_picks: Optional[List[str]] = None,
        top_k: int = 2
    ) -> SelectionResult:
        """
        选择参考样本
        
        Args:
            user_idea: 用户的创意概念
            strategy: 选择策略
            manual_picks: 手动指定的样本ID列表
            top_k: 自动选择时返回的样本数量
        
        Returns:
            SelectionResult
        """
        if strategy == SelectStrategy.NONE:
            return SelectionResult(
                selected_ids=[],
                strategy_used=SelectStrategy.NONE,
                reasoning="用户选择不使用样本参考",
                format_reference=""
            )
        
        if strategy == SelectStrategy.MANUAL:
            if not manual_picks:
                return SelectionResult(
                    selected_ids=[],
                    strategy_used=SelectStrategy.MANUAL,
                    reasoning="未指定样本",
                    format_reference=""
                )
            
            # 验证样本存在
            valid_ids = [
                sid for sid in manual_picks
                if self.sample_manager.get_metadata(sid) is not None
            ]
            
            format_ref = self._get_format_reference_for_selection(valid_ids)
            
            return SelectionResult(
                selected_ids=valid_ids,
                strategy_used=SelectStrategy.MANUAL,
                reasoning="用户手动指定",
                format_reference=format_ref
            )
        
        # AUTO 或 HYBRID 策略
        all_samples = self.sample_manager.list_samples()
        
        if not all_samples:
            return SelectionResult(
                selected_ids=[],
                strategy_used=strategy,
                reasoning="样本库为空",
                format_reference=""
            )
        
        # 使用LLM进行智能匹配
        selected_ids, reasoning = self._auto_select(user_idea, all_samples, top_k)
        
        format_ref = self._get_format_reference_for_selection(selected_ids)
        
        return SelectionResult(
            selected_ids=selected_ids,
            strategy_used=strategy,
            reasoning=reasoning,
            format_reference=format_ref
        )
    
    def _get_format_reference_for_selection(self, selected_ids: List[str]) -> str:
        """格式参考写死为太奶奶风格的一小段，不读文件、不依赖选中样本。"""
        return FORMAT_REFERENCE_SNIPPET
    
    def _auto_select(
        self,
        user_idea: str,
        available_samples: List[SampleMetadata],
        top_k: int
    ):
        """
        自动选择最匹配的样本
        
        Returns:
            (选中的样本ID列表, 选择理由)
        """
        # 构建样本列表描述
        samples_desc = "\n".join([
            f"- ID: {s.id}, 标题: 《{s.title}》, 类型: {','.join(s.genre) if s.genre else '未分类'}, "
            f"受众: {s.target_audience}, 风格: {s.style_notes}"
            for s in available_samples
        ])
        
        prompt = f"""请根据用户的创意概念，从样本库中选择最适合作为【格式和风格参考】的样本。

【用户创意】
{user_idea}

【可用样本】
{samples_desc}

【重要说明】
- 选择的样本仅用于参考其【格式规范】和【写作风格】
- 不会参考样本的创意内容，用户的创意保持原创
- 选择与用户创意类型相近的样本，有助于学习该类型的写作套路

请返回JSON格式：
{{
    "selected_ids": ["样本ID1", "样本ID2"],
    "reasoning": "选择这些样本的理由（与用户创意的相关性）"
}}

最多选择{top_k}个样本。"""

        try:
            from ..config import get_config
            get_config().current_stage_name = "00_样本选择"
            result = self.llm.chat_json(
                "你是一个短剧样本匹配专家，负责为用户创意选择最合适的格式参考样本。",
                prompt,
                temperature=0.5
            )
            
            selected_ids = result.get("selected_ids", [])[:top_k]
            reasoning = result.get("reasoning", "自动匹配")
            
            # 验证ID有效性
            valid_ids = [
                sid for sid in selected_ids
                if any(s.id == sid for s in available_samples)
            ]
            
            return valid_ids, reasoning
            
        except Exception as e:
            # 如果LLM调用失败，返回第一个样本作为默认
            print(f"自动选择失败：{e}，使用默认样本")
            default_id = available_samples[0].id if available_samples else None
            return [default_id] if default_id else [], "默认选择第一个样本"
    
    def recommend(
        self,
        user_idea: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        推荐样本（用于HYBRID模式，让用户确认）
        
        Args:
            user_idea: 用户创意
            top_k: 推荐数量
        
        Returns:
            推荐列表，包含样本信息和推荐理由
        """
        all_samples = self.sample_manager.list_samples()
        
        if not all_samples:
            return []
        
        selected_ids, reasoning = self._auto_select(user_idea, all_samples, top_k)
        
        recommendations = []
        for sid in selected_ids:
            meta = self.sample_manager.get_metadata(sid)
            if meta:
                recommendations.append({
                    "id": meta.id,
                    "title": meta.title,
                    "genre": meta.genre,
                    "target_audience": meta.target_audience,
                    "style_notes": meta.style_notes,
                    "recommendation_reason": reasoning
                })
        
        return recommendations
