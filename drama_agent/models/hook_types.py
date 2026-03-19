"""
数据模型 - 爽点类型
"""
from dataclasses import dataclass
from typing import List, Dict
from enum import Enum


class HookType(Enum):
    """爽点类型枚举"""
    FACE_SLAP = "face_slap"                          # 打脸
    IDENTITY_REVEAL = "identity_reveal"              # 身份揭示
    REVERSAL = "reversal"                            # 反转
    PRETEND_PIG_EAT_TIGER = "pretend_pig_eat_tiger"  # 扮猪吃虎
    FAMILY_REUNION = "family_reunion"                # 认亲
    TEAR_GREEN_TEA = "tear_green_tea"                # 手撕绿茶
    CLIFFHANGER = "cliffhanger"                      # 悬念收尾
    REVENGE = "revenge"                              # 复仇成功
    LEVEL_UP = "level_up"                            # 实力升级
    TREASURE = "treasure"                            # 获得宝物/资源
    CONFESSION = "confession"                        # 表白/情感突破
    RESCUE = "rescue"                                # 英雄救美/救场
    BETRAYAL_EXPOSED = "betrayal_exposed"            # 揭露背叛
    POWER_DISPLAY = "power_display"                  # 实力展示
    RESOLUTION = "resolution"                        # 大结局/完结


@dataclass
class HookDefinition:
    """爽点定义"""
    hook_type: HookType
    name_cn: str                          # 中文名称
    description: str                      # 描述
    weight: int                           # 权重（1-10）
    keywords: List[str]                   # 关键词（用于识别）
    example: str                          # 示例
    
    def to_dict(self) -> dict:
        return {
            "hook_type": self.hook_type.value,
            "name_cn": self.name_cn,
            "description": self.description,
            "weight": self.weight,
            "keywords": self.keywords,
            "example": self.example
        }


# 预定义的爽点库
HOOK_DEFINITIONS: Dict[HookType, HookDefinition] = {
    HookType.FACE_SLAP: HookDefinition(
        hook_type=HookType.FACE_SLAP,
        name_cn="打脸",
        description="主角用实力让对手闭嘴，通常是对方先嘲讽/看不起主角，然后被现实打脸",
        weight=10,
        keywords=["打脸", "震惊", "不可能", "怎么会", "你竟然", "闭嘴"],
        example="容若瑶嘲笑容遇数学不好，结果容遇3分钟解出竞赛题"
    ),
    HookType.IDENTITY_REVEAL: HookDefinition(
        hook_type=HookType.IDENTITY_REVEAL,
        name_cn="身份揭示",
        description="隐藏身份曝光，周围人态度巨变",
        weight=9,
        keywords=["真实身份", "原来是", "您就是", "失敬", "跪下"],
        example="众人发现容遇就是传说中的容院士"
    ),
    HookType.REVERSAL: HookDefinition(
        hook_type=HookType.REVERSAL,
        name_cn="反转",
        description="情节急转直下，出乎意料",
        weight=8,
        keywords=["没想到", "居然", "原来", "竟然是", "万万没想到"],
        example="以为是敌人，实际上是盟友"
    ),
    HookType.PRETEND_PIG_EAT_TIGER: HookDefinition(
        hook_type=HookType.PRETEND_PIG_EAT_TIGER,
        name_cn="扮猪吃虎",
        description="装弱后反杀，先让对手轻敌再一击制胜",
        weight=9,
        keywords=["装作", "以为", "示弱", "其实", "真正实力"],
        example="容遇假装不懂经商，实际上是商业天才"
    ),
    HookType.FAMILY_REUNION: HookDefinition(
        hook_type=HookType.FAMILY_REUNION,
        name_cn="认亲",
        description="失散亲人相认，情感爆发",
        weight=7,
        keywords=["儿子", "女儿", "父母", "相认", "亲生", "血脉"],
        example="纪舜英发现容遇就是自己失踪的太奶奶"
    ),
    HookType.TEAR_GREEN_TEA: HookDefinition(
        hook_type=HookType.TEAR_GREEN_TEA,
        name_cn="手撕绿茶",
        description="揭穿伪善者的真面目",
        weight=8,
        keywords=["装", "伪善", "真面目", "揭穿", "别装了", "看清"],
        example="容遇当众揭穿容若瑶的阴谋"
    ),
    HookType.CLIFFHANGER: HookDefinition(
        hook_type=HookType.CLIFFHANGER,
        name_cn="悬念收尾",
        description="留下钩子，让观众想看下一集",
        weight=6,
        keywords=["怎么办", "接下来", "突然", "这时", "门开了"],
        example="正当众人庆祝时，门外传来一个声音..."
    ),
    HookType.REVENGE: HookDefinition(
        hook_type=HookType.REVENGE,
        name_cn="复仇成功",
        description="主角成功复仇，恶人得到报应",
        weight=9,
        keywords=["报应", "活该", "终于", "还", "报仇"],
        example="害死主角的人被送进监狱"
    ),
    HookType.LEVEL_UP: HookDefinition(
        hook_type=HookType.LEVEL_UP,
        name_cn="实力升级",
        description="主角获得新能力或地位提升",
        weight=7,
        keywords=["突破", "升级", "晋升", "获得", "掌握"],
        example="主角成为公司CEO"
    ),
    HookType.TREASURE: HookDefinition(
        hook_type=HookType.TREASURE,
        name_cn="获得宝物",
        description="获得重要资源或宝贝",
        weight=6,
        keywords=["遗产", "宝贝", "财产", "股份", "秘籍"],
        example="发现祖传的财富"
    ),
    HookType.CONFESSION: HookDefinition(
        hook_type=HookType.CONFESSION,
        name_cn="情感突破",
        description="表白或情感关系突破",
        weight=7,
        keywords=["喜欢", "爱", "在一起", "表白", "心动"],
        example="男女主终于确定关系"
    ),
    HookType.RESCUE: HookDefinition(
        hook_type=HookType.RESCUE,
        name_cn="英雄救场",
        description="关键时刻有人来救场",
        weight=8,
        keywords=["救", "帮", "出现", "及时", "挺身而出"],
        example="主角危难时，神秘人物出手相助"
    ),
    HookType.BETRAYAL_EXPOSED: HookDefinition(
        hook_type=HookType.BETRAYAL_EXPOSED,
        name_cn="揭露背叛",
        description="发现被信任的人背叛",
        weight=8,
        keywords=["背叛", "出卖", "不敢相信", "原来你", "卧底"],
        example="发现多年好友一直在暗中算计自己"
    ),
    HookType.POWER_DISPLAY: HookDefinition(
        hook_type=HookType.POWER_DISPLAY,
        name_cn="实力展示",
        description="展示强大实力，震慑全场",
        weight=8,
        keywords=["厉害", "强大", "高手", "大佬", "不敢惹"],
        example="主角一招制敌，全场震惊"
    ),
    HookType.RESOLUTION: HookDefinition(
        hook_type=HookType.RESOLUTION,
        name_cn="大结局",
        description="故事完结，主要冲突解决，主角命运明确",
        weight=10,
        keywords=["终于", "完结", "结束", "圆满", "从此", "幸福"],
        example="主角战胜所有敌人，获得幸福生活（可留小伏笔暗示续集）"
    ),
}


def get_hook_definition(hook_type: HookType) -> HookDefinition:
    """获取爽点定义"""
    return HOOK_DEFINITIONS.get(hook_type)


def get_all_hook_types() -> List[HookType]:
    """获取所有爽点类型"""
    return list(HookType)


def get_hook_keywords() -> Dict[HookType, List[str]]:
    """获取所有爽点关键词映射"""
    return {ht: hd.keywords for ht, hd in HOOK_DEFINITIONS.items()}


# ========== 集尾钩子四大分类（基于《短剧编剧第一课》第06期）==========

class CliffhangerType(Enum):
    """集尾钩子类型（断章点分类）"""
    LIFE_DEATH = "life_death"      # 生死钩：主角面临生命危险的瞬间
    SECRET = "secret"              # 秘密钩：惊人秘密即将揭开
    REVERSAL = "reversal"          # 反转钩：反派以为稳操胜券时主角反杀
    EMOTION = "emotion"            # 情感钩：感情重大突破或误解


@dataclass
class CliffhangerDefinition:
    """集尾钩子定义"""
    cliffhanger_type: CliffhangerType
    name_cn: str
    description: str
    examples: List[str]
    best_use_case: str             # 最佳使用场景


CLIFFHANGER_DEFINITIONS: Dict[CliffhangerType, CliffhangerDefinition] = {
    CliffhangerType.LIFE_DEATH: CliffhangerDefinition(
        cliffhanger_type=CliffhangerType.LIFE_DEATH,
        name_cn="生死钩",
        description="主角正处于被攻击或面临生命危险的一瞬间断掉",
        examples=[
            "架子掉落砸向主角的瞬间",
            "枪口对准主角的那一刻",
            "悬崖边失足的一瞬间"
        ],
        best_use_case="动作/悬疑场景结尾"
    ),
    CliffhangerType.SECRET: CliffhangerDefinition(
        cliffhanger_type=CliffhangerType.SECRET,
        name_cn="秘密钩",
        description="一个惊人的秘密即将被揭开，或关键证据被发现",
        examples=[
            "翻开文件看到真相的那一刻",
            "DNA报告结果出来的瞬间",
            "监控录像播放到关键画面"
        ],
        best_use_case="身份揭秘/真相大白前"
    ),
    CliffhangerType.REVERSAL: CliffhangerDefinition(
        cliffhanger_type=CliffhangerType.REVERSAL,
        name_cn="反转钩",
        description="反派以为稳操胜券时，主角突然拿出致命证据",
        examples=[
            "主角掏出手机播放录音",
            "一个电话打来改变局势",
            "关键证人突然出现"
        ],
        best_use_case="打脸/逆转场景"
    ),
    CliffhangerType.EMOTION: CliffhangerDefinition(
        cliffhanger_type=CliffhangerType.EMOTION,
        name_cn="情感钩",
        description="两人的感情出现重大突破或重大误解的瞬间",
        examples=[
            "表白被打断的那一刻",
            "撞见疑似出轨的场面",
            "突然的拥抱或亲吻"
        ],
        best_use_case="情感线高潮"
    ),
}


# ========== 钩子分级系统 ==========

class HookLevel(Enum):
    """钩子级别"""
    SMALL = "small"      # 小钩子：每集结尾，留住用户看下一集
    LARGE = "large"      # 大钩子：每10-15集，刺激用户付费
    ULTIMATE = "ultimate" # 终极钩子：全剧末尾，期待第二季


@dataclass
class HookPlacement:
    """钩子布局建议"""
    level: HookLevel
    recommended_episodes: List[int]  # 建议放置的集数
    description: str


def get_hook_placement_guide(total_episodes: int = 80) -> List[HookPlacement]:
    """
    获取钩子布局指南
    
    Args:
        total_episodes: 总集数
    
    Returns:
        钩子布局建议列表
    """
    placements = [
        HookPlacement(
            level=HookLevel.SMALL,
            recommended_episodes=list(range(1, total_episodes + 1)),
            description="每集结尾必须有小钩子，留住用户看下一集"
        ),
        HookPlacement(
            level=HookLevel.LARGE,
            recommended_episodes=[10, 15, 25, 35, 50, 65, 80],
            description="大钩子用于刺激付费，通常在付费点前夕（第10-15集）最强"
        ),
        HookPlacement(
            level=HookLevel.ULTIMATE,
            recommended_episodes=[total_episodes],
            description="终极钩子留在全剧结尾，为第二季铺垫"
        ),
    ]
    return placements


def get_cliffhanger_prompt() -> str:
    """获取集尾钩子设计提示词"""
    return """
【集尾钩子设计法则 - 四种断章类型】

1. 生死钩（最强冲击力）：
   - 用于：主角面临生命危险的瞬间
   - 断点：动作即将发生但未完成时
   - 例：架子掉落砸向主角→画面定格→"请看下集"

2. 秘密钩（最强悬念感）：
   - 用于：真相即将揭晓时
   - 断点：观众最想知道答案的瞬间
   - 例：打开DNA报告→看到结果→表情变化→断掉

3. 反转钩（最强爽感期待）：
   - 用于：打脸场景高潮前
   - 断点：主角刚亮出底牌的瞬间
   - 例：主角说"就凭这个"→掏出手机→断掉

4. 情感钩（最强情感牵引）：
   - 用于：情感线关键节点
   - 断点：关系即将发生变化时
   - 例：即将表白→被打断/突然亲吻→断掉

【钩子分级与布局】
- 小钩子（每集）：留住用户，完播率保障
- 大钩子（第10、15、25、50集）：刺激付费转化
- 终极钩子（大结局）：期待第二季
"""

