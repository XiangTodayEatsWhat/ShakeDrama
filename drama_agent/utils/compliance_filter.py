"""
内容合规过滤器 - 基于广电总局监管要求
"""
from typing import List, Dict, Tuple
from dataclasses import dataclass
import re


@dataclass
class ComplianceIssue:
    """合规问题"""
    category: str           # 问题类别
    severity: str           # 严重程度：critical/warning
    description: str        # 问题描述
    matched_content: str    # 匹配到的内容
    suggestion: str         # 修改建议


class ComplianceFilter:
    """
    内容合规过滤器
    
    基于广电总局审查标准，确保生成的剧本符合监管要求。
    参考《短剧编剧第一课》第01期：内容安全与合规红线
    """
    
    # 价值观偏差关键词
    VALUE_RED_FLAGS = [
        # 拜金主义
        (r"有钱就是大爷|钱能解决一切|没钱就是废物|穷人活该", "拜金主义", "修改为正向价值观表达"),
        # 极端复仇
        (r"杀光|灭门|血债血偿|不死不休|赶尽杀绝", "极端复仇", "改为合法维权或和解"),
        # 封建迷信
        (r"算命|占卜|神婆|附身|通灵|转世", "封建迷信", "删除相关情节"),
    ]
    
    # 暴力色情红线
    VIOLENCE_RED_FLAGS = [
        (r"鲜血喷涌|开膛破肚|血肉模糊|断肢|虐杀", "过度暴力", "使用隐晦表达或删除"),
        (r"脱光|裸体|床戏|性爱|做爱", "色情内容", "删除相关描写"),
        (r"自杀方法|割腕|跳楼细节", "自杀诱导", "改为被救或删除细节"),
    ]
    
    # 伦理禁忌
    ETHICS_RED_FLAGS = [
        (r"师生恋|未成年.*恋爱|老少恋", "伦理敏感", "修改角色年龄或关系"),
        (r"乱伦|兄妹恋|姐弟恋.*亲生", "伦理禁忌", "删除相关情节"),
        (r"家暴.*正当|打老婆.*应该", "美化家暴", "修改为反对家暴立场"),
    ]
    
    # 社会敏感
    SOCIAL_RED_FLAGS = [
        (r"贪官都是好人|警察.*坏人|政府.*腐败", "抹黑公权", "修改相关表述"),
        (r"穷人.*活该|农村人.*低等|外地人.*滚", "地域歧视", "删除歧视性表达"),
    ]
    
    def __init__(self):
        self.all_rules = [
            ("价值观偏差", self.VALUE_RED_FLAGS),
            ("暴力色情", self.VIOLENCE_RED_FLAGS),
            ("伦理禁忌", self.ETHICS_RED_FLAGS),
            ("社会敏感", self.SOCIAL_RED_FLAGS),
        ]
    
    def scan(self, content: str) -> List[ComplianceIssue]:
        """
        扫描内容是否存在合规问题
        
        Args:
            content: 剧本内容
        
        Returns:
            发现的合规问题列表
        """
        issues = []
        
        for category, rules in self.all_rules:
            for pattern, issue_type, suggestion in rules:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    for match in matches:
                        issues.append(ComplianceIssue(
                            category=category,
                            severity="critical" if category in ["暴力色情", "伦理禁忌"] else "warning",
                            description=f"检测到{issue_type}相关内容",
                            matched_content=match,
                            suggestion=suggestion
                        ))
        
        return issues
    
    def is_compliant(self, content: str) -> Tuple[bool, List[ComplianceIssue]]:
        """
        检查内容是否合规
        
        Returns:
            (是否合规, 问题列表)
        """
        issues = self.scan(content)
        critical_issues = [i for i in issues if i.severity == "critical"]
        return len(critical_issues) == 0, issues
    
    def get_compliance_prompt(self) -> str:
        """
        获取合规性提示词（用于LLM生成时）
        """
        return """
【内容合规要求 - 红线警示】
生成的剧本必须严格遵守以下规定：

1. 价值观正确：
   - 禁止宣扬拜金主义、极端复仇思想
   - 禁止封建迷信内容
   - 主角可以有缺点，但核心价值观必须正向

2. 内容健康：
   - 禁止露骨暴力描写（可用隐晦表达）
   - 禁止任何色情内容
   - 禁止渲染自杀方法

3. 伦理合规：
   - 禁止违背公序良俗的关系（如未成年恋爱、乱伦等）
   - 家庭矛盾可以激烈，但不能美化家暴

4. 社会责任：
   - 不抹黑公权力机关
   - 不包含地域歧视

违反以上任何一条都将导致剧本无法过审！
"""


# 全局实例
_compliance_filter = None

def get_compliance_filter() -> ComplianceFilter:
    global _compliance_filter
    if _compliance_filter is None:
        _compliance_filter = ComplianceFilter()
    return _compliance_filter
