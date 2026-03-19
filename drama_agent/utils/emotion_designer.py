"""
情绪设计模块 - 基于《短剧编剧第一课》第07期
实现"欲扬先抑"的极致应用和高唤醒情绪词库
"""
from typing import List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum


class EmotionType(Enum):
    """情绪类型"""
    ANGER = "anger"              # 愤怒（观众对反派的怒气）
    SATISFACTION = "satisfaction" # 爽感（打脸后的满足）
    ANXIETY = "anxiety"          # 紧张（危机时刻）
    TOUCHED = "touched"          # 感动（亲情/爱情）
    PRIDE = "pride"              # 自豪（主角展示实力）
    GRIEVANCE = "grievance"      # 委屈（主角受辱）


@dataclass
class EmotionBeat:
    """情绪节拍"""
    emotion_type: EmotionType
    intensity: int              # 强度1-10
    description: str
    trigger: str                # 触发点


class EmotionDesigner:
    """
    情绪设计器
    
    核心原则：情绪大于逻辑，先抑后扬，爽点后置
    """
    
    # 高唤醒情绪词库（用于台词和动作描写）
    HIGH_AROUSAL_WORDS = {
        "权力词": ["跪下", "滚", "蝼蚁", "废物", "畜生", "卑微", "匍匐"],
        "财富词": ["百亿", "全资", "股权", "遗产", "帝国", "财阀"],
        "身份词": ["大佬", "首富", "总裁", "院士", "战神", "继承人"],
        "情绪词": ["震惊", "颤抖", "瘫软", "目瞪口呆", "如遭雷击", "血液倒流"],
        "动作词": ["甩出", "猛地", "反手", "一把", "狠狠", "径直"],
        "反击词": ["闭嘴", "你不配", "看清楚", "记住今天", "等着瞧"],
    }
    
    # 欲扬先抑模板
    SUPPRESS_ELEVATE_PATTERNS = [
        {
            "name": "受辱反击",
            "suppress": ["被当众羞辱", "被泼脏水", "被冤枉"],
            "elevate": ["亮出真实身份", "拿出证据反杀", "一句话让对方跪下"]
        },
        {
            "name": "弱势逆转",
            "suppress": ["被看不起", "被断言失败", "被嘲笑没本事"],
            "elevate": ["秒杀难题", "实力碾压", "让质疑者闭嘴"]
        },
        {
            "name": "孤立反包围",
            "suppress": ["众叛亲离", "无人相信", "被陷害"],
            "elevate": ["真相大白", "所有人道歉", "反派被群嘲"]
        },
    ]
    
    # 集尾金句模板（用于制造传播点）
    GOLDEN_LINE_TEMPLATES = [
        "就凭{证据}，你觉得你还有资格{动作}吗？",
        "从今天起，{反派}的一切，都将属于我。",
        "你以为的{错误认知}，不过是我让你看到的。",
        "跪下，叫{称呼}。",
        "这只是开始，接下来，我会让你知道什么叫{概念}。",
        "你没有资格知道我是谁。",
        "{时间}后，你会后悔今天说的每一个字。",
    ]
    
    def design_emotion_curve(self, episode_count: int) -> List[Dict]:
        """
        设计全剧情绪曲线
        
        原则：
        - 前3集快速建立情绪基底（抑->扬）
        - 每10集一个大爽点
        - 付费点前情绪达到峰值
        """
        curve = []
        
        for ep in range(1, episode_count + 1):
            beat = {
                "episode": ep,
                "suppress_level": 0,   # 压抑程度
                "elevate_level": 0,    # 释放程度
                "hook_intensity": 0,   # 钩子强度
            }
            
            # 前3集：黄金开场
            if ep <= 3:
                beat["suppress_level"] = 9 if ep == 1 else 7
                beat["elevate_level"] = 3 if ep == 1 else 6
                beat["hook_intensity"] = 10  # 前三集钩子必须最强
            
            # 每10集一个大高潮
            elif ep % 10 == 0:
                beat["suppress_level"] = 8
                beat["elevate_level"] = 10
                beat["hook_intensity"] = 9
            
            # 付费点前夕（10-15集）
            elif 10 <= ep <= 15:
                beat["suppress_level"] = 8
                beat["elevate_level"] = 7
                beat["hook_intensity"] = 10  # 刺激付费
            
            # 常规集
            else:
                beat["suppress_level"] = 5
                beat["elevate_level"] = 6
                beat["hook_intensity"] = 7
            
            curve.append(beat)
        
        return curve
    
    def get_suppress_elevate_prompt(self) -> str:
        """获取欲扬先抑的提示词"""
        return """
【情绪设计原则 - 欲扬先抑】

1. 极致的"抑"（压抑阶段）：
   - 让主角受到社会地位打压、言语羞辱、亲情背叛
   - 反派行为必须触及大众底线（欺负老人小孩、背信弃义）
   - 目标：让观众产生"代入式愤怒"，恨不得自己冲进去打反派

2. 爆发的"扬"（释放阶段）：
   - 反击不能拖泥带水，必须在观众愤怒顶点瞬间爆发
   - 反击力度要数倍于受到的伤害
   - 使用高唤醒情绪词：跪下、蝼蚁、滚、百亿、战神等

3. 身份反转的视觉表现：
   - 使用道具承载情绪：黑卡、项链、勋章
   - 通过群演的"震惊脸"侧面烘托
   - 反派的瘫倒、颤抖、目瞪口呆

4. 每集必须有一句"金句"：
   - 适合剪辑传播
   - 让观众"头皮发麻"或"爽到起鸡皮疙瘩"
   - 例："就凭你马上要收到的手机短信。"
"""
    
    def get_high_arousal_words(self, category: str = None) -> List[str]:
        """获取高唤醒情绪词"""
        if category:
            return self.HIGH_AROUSAL_WORDS.get(category, [])
        
        all_words = []
        for words in self.HIGH_AROUSAL_WORDS.values():
            all_words.extend(words)
        return all_words
    
    def generate_golden_line(self, context: Dict) -> str:
        """
        生成金句
        
        Args:
            context: 包含证据、反派、动作等上下文
        """
        import random
        template = random.choice(self.GOLDEN_LINE_TEMPLATES)
        
        # 填充模板（简单实现）
        for key, value in context.items():
            template = template.replace(f"{{{key}}}", str(value))
        
        return template
    
    def analyze_emotion_intensity(self, script: str) -> Dict:
        """
        分析剧本的情绪强度
        
        Returns:
            情绪分析报告
        """
        analysis = {
            "high_arousal_word_count": 0,
            "suppress_keywords": 0,
            "elevate_keywords": 0,
            "has_golden_line": False,
            "emotion_score": 0,
        }
        
        # 统计高唤醒词
        for words in self.HIGH_AROUSAL_WORDS.values():
            for word in words:
                if word in script:
                    analysis["high_arousal_word_count"] += script.count(word)
        
        # 检测压抑关键词
        suppress_words = ["羞辱", "欺负", "看不起", "嘲笑", "冤枉", "委屈", "泼脏水"]
        for word in suppress_words:
            if word in script:
                analysis["suppress_keywords"] += 1
        
        # 检测释放关键词
        elevate_words = ["震惊", "跪下", "道歉", "闭嘴", "打脸", "反杀", "真相"]
        for word in elevate_words:
            if word in script:
                analysis["elevate_keywords"] += 1
        
        # 检测金句特征
        golden_patterns = ["就凭", "你不配", "从今天起", "记住今天"]
        for pattern in golden_patterns:
            if pattern in script:
                analysis["has_golden_line"] = True
                break
        
        # 计算情绪分数
        analysis["emotion_score"] = min(10, (
            analysis["high_arousal_word_count"] * 0.5 +
            analysis["suppress_keywords"] * 1.5 +
            analysis["elevate_keywords"] * 2 +
            (3 if analysis["has_golden_line"] else 0)
        ))
        
        return analysis


# 全局实例
_emotion_designer = None

def get_emotion_designer() -> EmotionDesigner:
    global _emotion_designer
    if _emotion_designer is None:
        _emotion_designer = EmotionDesigner()
    return _emotion_designer
