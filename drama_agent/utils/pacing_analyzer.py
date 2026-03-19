"""
节奏分析器 - 基于《短剧编剧第一课》第05期
实现节奏密度检测和三段式结构校验
"""
from typing import List, Dict, Tuple
from dataclasses import dataclass
import re


@dataclass
class PacingIssue:
    """节奏问题"""
    issue_type: str
    severity: str       # critical/warning
    description: str
    location: str       # 问题位置
    suggestion: str


class PacingAnalyzer:
    """
    节奏分析器
    
    核心公式：节奏 = 信息量 / 时间
    短剧要求在1.5分钟内包含3-5个有效信息点
    """
    
    # 三段式结构时间点（按90秒单集计算）
    STRUCTURE = {
        "起": (0, 30),      # 0-30秒：衔接上集，交代新冲突
        "承转": (30, 80),   # 30-80秒：冲突升级或反转
        "合": (80, 120),    # 80秒-结尾：高潮断点，抛出钩子
    }
    
    # 每集理想字数范围（800-1200字约等于90-120秒）
    IDEAL_WORD_COUNT = (800, 1200)
    
    # 对话占比要求
    IDEAL_DIALOGUE_RATIO = 0.7  # 70%以上应该是对话
    
    # 动作描写符号
    ACTION_MARKER = "△"
    
    def analyze_episode(self, script: str) -> Dict:
        """
        分析单集的节奏
        
        Returns:
            节奏分析报告
        """
        analysis = {
            "word_count": len(script),
            "dialogue_count": 0,
            "action_count": 0,
            "conflict_points": 0,
            "reversal_points": 0,
            "dialogue_ratio": 0,
            "pacing_score": 0,
            "issues": [],
        }
        
        # 统计字数
        word_count = len(script.replace("\n", "").replace(" ", ""))
        analysis["word_count"] = word_count
        
        # 检测对话（非动作、非场景头的内容）
        lines = script.split("\n")
        dialogue_words = 0
        action_count = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 动作描写
            if line.startswith(self.ACTION_MARKER):
                action_count += 1
            # 场景头（如 1-1 客厅 日 内）
            elif re.match(r'^\d+-\d+\s+', line):
                continue
            # 对话
            else:
                dialogue_words += len(line)
        
        analysis["action_count"] = action_count
        if word_count > 0:
            analysis["dialogue_ratio"] = dialogue_words / word_count
        
        # 检测冲突点（通过关键词）
        conflict_keywords = ["但是", "突然", "没想到", "居然", "竟然", "怎么可能", "不可能"]
        for keyword in conflict_keywords:
            analysis["conflict_points"] += script.count(keyword)
        
        # 检测反转点
        reversal_keywords = ["原来", "真相是", "其实", "万万没想到", "震惊"]
        for keyword in reversal_keywords:
            analysis["reversal_points"] += script.count(keyword)
        
        # 检测问题
        issues = self._detect_issues(analysis)
        analysis["issues"] = issues
        
        # 计算节奏分数
        analysis["pacing_score"] = self._calculate_score(analysis)
        
        return analysis
    
    def _detect_issues(self, analysis: Dict) -> List[PacingIssue]:
        """检测节奏问题"""
        issues = []
        
        # 字数检查
        min_words, max_words = self.IDEAL_WORD_COUNT
        if analysis["word_count"] < min_words:
            issues.append(PacingIssue(
                issue_type="字数不足",
                severity="warning",
                description=f"当前{analysis['word_count']}字，建议{min_words}-{max_words}字",
                location="全集",
                suggestion="增加冲突场景或对话"
            ))
        elif analysis["word_count"] > max_words:
            issues.append(PacingIssue(
                issue_type="字数超标",
                severity="warning",
                description=f"当前{analysis['word_count']}字，超过{max_words}字上限",
                location="全集",
                suggestion="删减冗余描写和过渡"
            ))
        
        # 对话比例检查
        if analysis["dialogue_ratio"] < self.IDEAL_DIALOGUE_RATIO:
            issues.append(PacingIssue(
                issue_type="对话比例不足",
                severity="warning",
                description=f"对话占比{analysis['dialogue_ratio']:.0%}，建议70%以上",
                location="全集",
                suggestion="增加对话，减少描写和旁白"
            ))
        
        # 动作描写检查
        if analysis["action_count"] < 3:
            issues.append(PacingIssue(
                issue_type="动作描写不足",
                severity="warning",
                description=f"仅有{analysis['action_count']}处动作描写",
                location="全集",
                suggestion="增加△动作指令，让剧本更有画面感"
            ))
        
        # 冲突点检查
        if analysis["conflict_points"] < 2:
            issues.append(PacingIssue(
                issue_type="冲突密度不足",
                severity="critical",
                description="单集冲突点少于2个",
                location="全集",
                suggestion="每集应有3-5个冲突或转折点"
            ))
        
        return issues
    
    def _calculate_score(self, analysis: Dict) -> float:
        """计算节奏分数"""
        score = 5.0  # 基础分
        
        # 字数合理性 (+/-2分)
        min_words, max_words = self.IDEAL_WORD_COUNT
        if min_words <= analysis["word_count"] <= max_words:
            score += 2
        elif analysis["word_count"] < min_words * 0.7 or analysis["word_count"] > max_words * 1.3:
            score -= 2
        
        # 对话比例 (+2分)
        if analysis["dialogue_ratio"] >= self.IDEAL_DIALOGUE_RATIO:
            score += 2
        
        # 冲突密度 (+3分)
        if analysis["conflict_points"] >= 3:
            score += 3
        elif analysis["conflict_points"] >= 2:
            score += 1
        else:
            score -= 2
        
        # 反转点 (+1分)
        if analysis["reversal_points"] >= 1:
            score += 1
        
        return min(10, max(0, score))
    
    def get_pacing_prompt(self) -> str:
        """获取节奏设计提示词"""
        return """
【节奏设计密码 - 三段式结构】

每集（90-120秒，800-1200字）必须遵循以下结构：

1. 起（0-30秒，约200字）：
   - 衔接上一集的钩子
   - 迅速交代本集新冲突
   - 禁止慢悠悠的空镜头

2. 承/转（30-80秒，约500字）：
   - 冲突升级或意想不到的反转
   - 例：本以为要被打，结果主角亮出真实身份
   - 包含2-3个小高潮

3. 合（80秒-结尾，约300字）：
   - 冲突暂时解决或陷入更大危机
   - 精准卡在"最高潮处"断掉
   - 抛出让观众必须看下一集的钩子

【节奏要求】
- 对话占比70%以上
- 每集3-5个有效信息点/冲突点
- 动作描写至少3处（用△标记）
- 禁止一个人连续说超过3行台词（抛球式对白）
- 任何不推动剧情的内容都是"废戏"
"""
    
    def check_dialogue_rhythm(self, script: str) -> List[PacingIssue]:
        """
        检查对白节奏
        
        规则：禁止一个人连续说超过3行
        """
        issues = []
        lines = script.split("\n")
        
        current_speaker = None
        consecutive_lines = 0
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith(self.ACTION_MARKER) or re.match(r'^\d+-\d+', line):
                current_speaker = None
                consecutive_lines = 0
                continue
            
            # 检测说话人（假设格式为"角色名\n对话内容"）
            if re.match(r'^[\u4e00-\u9fff]{2,4}$', line):  # 2-4个汉字可能是角色名
                if current_speaker == line:
                    consecutive_lines += 1
                else:
                    current_speaker = line
                    consecutive_lines = 1
            else:
                if consecutive_lines > 3:
                    issues.append(PacingIssue(
                        issue_type="对白拖沓",
                        severity="warning",
                        description=f"角色{current_speaker}连续说了{consecutive_lines}行以上",
                        location=f"第{i}行附近",
                        suggestion="拆分为抛球式对白，增加互动"
                    ))
        
        return issues


# 全局实例
_pacing_analyzer = None

def get_pacing_analyzer() -> PacingAnalyzer:
    global _pacing_analyzer
    if _pacing_analyzer is None:
        _pacing_analyzer = PacingAnalyzer()
    return _pacing_analyzer
