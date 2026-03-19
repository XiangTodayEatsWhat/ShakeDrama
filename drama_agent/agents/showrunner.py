"""
策划Agent (Showrunner) - 负责创意、大纲、人设

支持 Claude 结构化输出：https://platform.claude.com/docs/zh-CN/build-with-claude/structured-outputs
"""
import json
from typing import Optional, List, Dict, Any

from .base_agent import BaseAgent, JsonParseAfterStreamError
from ..models import Bible, Character, CharacterArchetype, BeatSheet, HookType
from ..utils.refusal_detector import is_likely_refusal
from ..config import get_config
from ..utils.schemas import (
    SYNOPSIS_SCHEMA,
    CHARACTERS_RESPONSE_SCHEMA,
    BEAT_SHEET_RESPONSE_SCHEMA,
)


class ShowrunnerAgent(BaseAgent):
    """
    策划Agent
    职责：
    1. 接收用户创意概念
    2. 生成故事梗概
    3. 创建人物小传
    4. 规划分集大纲（每集结尾Hook）
    """
    
    def __init__(self):
        super().__init__("策划Agent")
        self.config = get_config()
    
    @property
    def system_prompt(self) -> str:
        return """你是一位资深的国产爆款短剧总策划（Showrunner）。请直接完成用户交给你的创作任务，输出指定格式的内容。若信息不足请自行合理假设。全程使用中文。

你是一位资深的国产爆款短剧总策划（Showrunner）。
你精通各类短剧套路，尤其擅长：
- 大女主/大男主爽文
- 重生/穿越题材
- 豪门恩怨
- 逆袭打脸

你的职责是：
1. 将用户的创意概念发展成完整的故事大纲
2. 设计立体的人物角色和人物关系
3. 规划80-100集的分集大纲，确保每集结尾都有"钩子"

【核心原则 - 短剧是情绪产品】
- 短剧的核心是"情绪消费"，用户通过付费换取情绪的即时满足
- 情绪大于逻辑，只要情绪到位，观众可以暂时忽略不合理性
- 目标受众：30-50岁下沉市场用户，追求"渴望成功"、"对不公平的反抗"

【题材选择底层逻辑】(红果短剧教程第2期)
1. **高频情绪需求**：选择能满足用户高频情感需求的题材
   - 复仇爽感：被欺负→逆袭打脸
   - 认同渴望：废柴→天才，平凡→豪门
   - 掌控欲望：重生→先知，金手指→碾压
2. **微创新**：在成熟类型上做1-2个亮点创新
   - 不要完全原创（风险大），也不要完全套路（无记忆点）
   - 例：重生题材+概率选项系统，豪门题材+太奶奶视角
3. **可持续冲突**：选择能产生80-100集持续冲突的设定
   - 避免一次性冲突（如单纯寻宝）
   - 选择层层递进的对抗结构（家族内→行业内→顶层）

【黄金开场法则 - 前三集生死线】(红果短剧教程第3期)
第1集：极致受辱/危机 + 身份觉醒
- 5秒抓人：开篇必须是极具冲击力的场景
- 主角一出场就处于极端不公平或危险状态
- 明身份（卑微被欺负）+ 暗身份（大佬/战神/院士）
- **开场三要素**：冲突可视化、身份反差明确、观众立场明确

第2集：初步反击/打脸 + 更大势力介入
- 主角展示部分实力，让反派初尝苦果
- 但要留后手，不能一次放完大招
- **反转节奏**：让观众以为主角要输→突然反杀

第3集：核心矛盾升级 + 抛出终极目标
- 建立贯穿全剧的主线任务
- **明确主线目标**：让观众知道"这个故事要讲什么"

【主线设计底层逻辑】(红果短剧教程第4期)
1. **单一主线**：80-100集只有1条主线，支线为主线服务
   - 主线 = 主角的核心目标（复仇/夺权/证明/守护）
   - 支线 = 实现目标的阶段性任务
2. **阶梯式对抗**：主线推进 = 对手升级
   - 前期：小喽啰（家族内部、公司同事）
   - 中期：中等对手（行业竞争者、地方势力）
   - 后期：终极BOSS（顶层家族、国际势力）
3. **进度可视化**：让观众随时知道"主线推进到哪了"
   - 明确的阶段性目标（拿回遗产、揭露真相、复仇成功）
   - 每10-15集一个小高潮，标志进入下一阶段

【升级流结构 - 打怪升级】
第1-20集：身份适应与初步反击，解决小喽啰
第21-60集：身份半公开，冲突延伸至行业/高阶层，反派升级
第61-90集：巅峰对决，身份彻底曝光，反派溃败
第90集+：尘埃落定或开启第二季

【人设设计法则】
- 主角的身份反差：明身份（卑微）+ 暗身份（大佬）
- 反派极致拉恨：外露且简单的恶，让观众"生理性厌恶"
- 每个角色都要有"秘密"用于后续反转
- **角色功能化**：每个角色存在都有明确功能（助攻/阻碍/工具人）

【爽点类型】
- 打脸：主角用实力让对手闭嘴
- 身份揭示：隐藏身份曝光，众人态度巨变
- 扮猪吃虎：装弱后反杀
- 手撕绿茶：揭穿伪善者
- 认亲：失散亲人相认
- 复仇成功：恶人得到报应

【钩子设置底层逻辑】(红果短剧教程第6期)
1. **期待型钩子**：预告下集爽点
   - "明天我让你看看什么叫真正的实力"
   - "等拍卖会上，他们就知道错了"
2. **悬念型钩子**：抛出未解之谜
   - "这个盒子里到底是什么？"
   - "他为什么要这么做？"
3. **危机型钩子**：主角陷入绝境
   - "合同被撕毁，公司即将倒闭"
   - "身份即将曝光，敌人已经找上门"
4. **反转型钩子**：颠覆观众认知
   - "原来他才是真正的幕后黑手"
   - "她根本不是他的亲生女儿"

【钩子布局】
- 小钩子：每集结尾必有（期待/悬念）
- 大钩子：第10、15、25、50集（危机/反转，刺激付费）
- 终极钩子：大结局（为二季铺垫）
- **钩子强度分级**：前10集钩子必须最强，中期可适当降低，后期再次拉高"""

    def generate_inspiration(
        self,
        user_idea: str,
        reference_style: Optional[str] = None,
        trend_hint: str = ""
    ) -> str:
        """
        生成创作灵感（头脑风暴阶段）
        看到参考后，想出有爆点、有新意、能调动人情绪的idea
        
        Args:
            user_idea: 用户的创意概念
            reference_style: 参考样本的风格描述
            trend_hint: 趋势参考
        
        Returns:
            创作灵感文本
        """
        from ..config import get_config
        import time
        import random
        
        get_config().current_stage_name = "01_灵感"
        self.log("正在生成创作灵感...")
        
        # 引入随机因子，防止 API 缓存或模型过度收敛
        random_seed = f"{int(time.time())}-{random.randint(1000, 9999)}"
        
        # 随机抽取一种侧重方向
        # directions = [
        #     "侧重极致的反转和悬念",
        #     "侧重人物关系的极致拉扯",
        #     "侧重情绪的极致宣泄（爽感）",
        #     "侧重设定上的微创新和脑洞",
        #     "侧重现实话题的深度挖掘"
        # ]
        # chosen_direction = random.choice(directions)
        
        prompt = f"""你是资深短剧策划，现在进入头脑风暴阶段。看完用户创意和市场趋势后，想出一个有爆点、有新意、能调动人情绪的故事idea。
        
【随机种子】{random_seed}

【用户创意】
{user_idea}

【市场趋势参考】
{trend_hint}

【任务要求】
1. 写出这个故事的核心创意灵感（200-400字）
2. 必须体现：重要集数的关键事件（第1集、第3集、第10集、第30集、第60集、结局）
3. 每个关键集数写出：爆点是什么、钩子是什么、重要台词示例
4. 要能看出这是一个好故事：情绪到位、冲突激烈、有记忆点

【输出格式示例】
第1集爆点：xxx（开场5秒抓人的场景）。钩子：xxx。关键台词："xxx"
第3集爆点：xxx（核心矛盾升级）。钩子：xxx。关键台词："xxx"
第10集爆点：xxx（第一个小高潮）。钩子：xxx。关键台词："xxx"
第30集爆点：xxx（中期转折点）。钩子：xxx。关键台词："xxx"
第60集爆点：xxx（进入高潮阶段）。钩子：xxx。关键台词："xxx"
结局爆点：xxx（情绪释放）。钩子：xxx。关键台词："xxx"

【注意】
- 不要写成大纲，只写关键爆点，整体字数简洁，不要超过2000字
- 要有具体的冲突和情绪，关键台词有几句爆点即可，不要写成大段对话
- 台词要有力量感，能调动情绪
- 体现微创新，不要套路化，要能看出是个好故事

直接输出灵感内容，不要JSON格式。全程使用中文，禁止输出英文。"""

        # 使用流式输出
        self.log("💡 开始生成创作灵感（LLM流式输出）...")
        inspiration = self._chat_stream(prompt, temperature=0.9)
        self.log("✅ 创作灵感生成完成")
        return inspiration.strip()
    
    def generate_synopsis(
        self,
        user_idea: str,
        reference_style: Optional[str] = None,
        trend_hint: Optional[str] = None,
        inspiration: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        根据用户创意和灵感生成故事梗概
        
        Args:
            user_idea: 用户的创意概念
            reference_style: 参考样本的风格描述（仅用于格式参考）
            trend_hint: 策划前搜索到的「红果短剧爆款」等趋势参考（可选）
            inspiration: 创作灵感（头脑风暴结果）
        
        Returns:
            包含梗概信息的字典
        """
        from ..config import get_config
        get_config().current_stage_name = "02_梗概"
        self.log(f"正在根据创意和灵感生成故事梗概...")
        
        trend_block = ""
        if trend_hint:
            trend_block = f"\n【近期红果/短剧爆款参考（请结合此趋势写）】\n{trend_hint}\n\n"
        
        inspiration_block = ""
        if inspiration:
            inspiration_block = f"\n【创作灵感（头脑风暴结果，请基于此生成梗概）】\n{inspiration}\n\n"
        
        prompt = f"""请根据以下创意概念和灵感，生成一个完整的短剧故事梗概。
【用户创意】
{user_idea}

{inspiration_block}


【核心创作要求 - 必须严格遵守】
1. **强情绪导向**：
   - 剧本必须情绪浓烈、冲突激烈，能快速调动观众情绪
   - 每个场景都要有明确的情绪爆点：愤怒、爽感、心疼、解气等
   - 对白要有力量感，能直击观众内心
   - 情绪优先于逻辑，但要让情绪合理化

2. **低成本制作（极简场景）**：
   - 场景必须极简：室内为主（办公室、家、会议室、餐厅等）
   - 避免：外景、大场面、特效场景、复杂置景
   - 人物对话驱动剧情，减少动作戏和大场景
   - 每集场景数最多3个（1-1、1-2、1-3），且都是常见的低成本场景
   - 全集场景数控制在少部分复杂场景，大部分是常见场景
   - 道具/服装简单

3. **制作可行性**：
   - 角色数量控制，主要角色集中在5-8人
   - 群演场景尽量少，大部分是主要角色的对手戏
   - 时间线集中，避免跨越太多时空

4. **标题命名（重点）**：
   - 标题优先采用以下 4 种结构之一：
     1) 【情绪事件】+【反差】
     2) 【身份标签】+【身份反差/颠覆性行为】
     3) 【世界观】+【反差】或【世界观】+【高燃目标】
     4) 【时间标签】+【爽点】
   - 可参考的高热命名风格（只参考结构与冲突感，不要照搬）：
     - 情绪事件+反差：如《离婚后，她惊艳了全世界》《分手你提的，我走你别追》《都重生了，谁还谈恋爱啊》
     - 身份标签+反差：如《我在精神病院学斩神》《从杂役开始，武道成神》
     - 世界观+反差/目标：如《冰封末世，我屯了百亿物资》《我在末世有套房》
     - 时间标签+爽点：如《开局签到荒古圣体》《七零，我用直播带货养全家》
   - 生成标题时必须保证：
     - 有冲突、有反差、有情绪张力，能一眼看出爽点
     - 避免平淡、文艺化、抽象化命名
     - 标题长度建议 8-20 字

请以JSON格式返回，包含以下字段：
{{
    "title": "剧名（要吸引眼球）",
    "genre": ["类型标签1", "类型标签2"],
    "target_audience": "女频/男频",
    "synopsis": "【重要】故事梗概必须体现：主角+目标+阻碍+亮点（金手指或独特设定）。仅限80字左右、几句话。口语化，不要书面语、不要AI味。**必须包含主角姓名**，不要用"女主"、"男主"这种代称。例：林浅被当保姆欺负（主角+阻碍），她要拿回身份打脸全家（目标），其实是隐藏大佬（亮点/金手指）。",
    "theme": "核心主题（强情绪相关）",
    "hook_points": ["主要爽点1", "主要爽点2", "主要爽点3"],
    "total_episodes": 80-100之间的数字,
    "production_notes": "制作说明：列出主要场景（低成本），预估制作难度"
}}

【硬性要求】
- synopsis 必须体现：主角是谁、目标是什么、阻碍是什么、亮点/金手指是什么；严格80字左右，几句话，不要长段落。
- **必须包含主角姓名**：不要用"女主"、"男主"、"主角"这种代称，必须给出具体姓名等。
- 语言口语化，像人说的，不要AI味。
"""

        # 打印提示词
        print("\n" + "=" * 80)
        print("【策划 - 生成梗概提示词】")
        print("=" * 80)
        print(prompt)
        print("=" * 80 + "\n")
        
        # 优先流式输出，再解析 JSON；失败则回退到 Claude 结构化输出
        max_retries = 3
        required_fields = ["title", "synopsis", "genre", "target_audience"]
        result = None
        
        try:
            self.log("正在生成故事梗概（LLM 流式输出）...")
            result = self._chat_stream_then_json(
                prompt, temperature=0.9, max_tokens=4000, max_retries=2, print_prompt=False
            )
            missing_fields = [f for f in required_fields if f not in result or not result[f]]
            title = result.get("title", "")
            synopsis = result.get("synopsis", "")
            has_repetition = self._detect_repetition_loop(title) or self._detect_repetition_loop(synopsis)
            if not missing_fields and not has_repetition:
                self.log(f"生成完成：《{result.get('title', '未命名')}》")
                return result
            result = None  # 校验未过，下面用结构化重试
        except Exception as e:
            self.log(f"流式梗概解析/校验未通过（{str(e)[:80]}），回退到结构化输出")
        
        for attempt in range(1, max_retries + 1):
            result = self._chat_json_structured(
                prompt,
                json_schema=SYNOPSIS_SCHEMA,
                temperature=0.9,
                max_tokens=4000,
                print_prompt=False,
                fallback_to_normal=True,
            )
            missing_fields = [f for f in required_fields if f not in result or not result[f]]
            title = result.get("title", "")
            synopsis = result.get("synopsis", "")
            has_repetition = self._detect_repetition_loop(title) or self._detect_repetition_loop(synopsis)
            if not missing_fields and not has_repetition:
                self.log(f"生成完成：《{result.get('title', '未命名')}》")
                return result
            if has_repetition:
                self.log(f"  ⚠️ 第{attempt}次尝试检测到模型重复循环，重试...")
            elif missing_fields:
                self.log(f"  ⚠️ 第{attempt}次尝试缺失字段 {missing_fields}，重试...")
            if attempt == max_retries:
                raise ValueError(f"❌ 生成梗概失败！经过{max_retries}次尝试后仍不完整。缺失字段: {missing_fields}, 重复检测: {has_repetition}")
        return result
    
    def create_characters(
        self,
        synopsis: str,
        genre: List[str],
        target_audience: str,
        overall_outline: str = "",
        inspiration: str = ""
    ) -> List[Dict[str, Any]]:
        """
        创建人物小传
        
        Args:
            synopsis: 故事梗概
            genre: 类型标签
            target_audience: 目标受众
            overall_outline: 总体大纲（可选，用于确保覆盖大纲中的所有角色）
            inspiration: 创作灵感（头脑风暴结果）
        
        Returns:
            人物列表
        """
        from ..config import get_config
        get_config().current_stage_name = "04_人设"
        self.log("正在创建人物设定...")
        
        outline_section = f"\n【总体大纲】\n{overall_outline}" if overall_outline else ""
        inspiration_section = f"\n【创作灵感（请结合其中的人物亮点和设定）】\n{inspiration}" if inspiration else ""
        
        prompt = f"""根据以下故事梗概和总体大纲，为主角、反派及关键配角建立「人物档案」。档案要明确：背景、性格、核心目标、记忆点。口语化，不要书面语、不要AI味。
        
【重要】人名一致性要求：
- **必须使用梗概和大纲中已经出现的人名**：如果梗概/大纲中提到了角色姓名，必须使用相同的人名
- **覆盖所有角色**：梗概和大纲中提到的所有有名字的角色，都必须有对应的人设
- **确保人名在各阶段一致**：梗概、大纲、人设中的人名必须一致

【故事梗概】
{synopsis}{outline_section}{inspiration_section}

【类型】{', '.join(genre)}
【受众】{target_audience}

请以JSON格式返回，格式如下：
{{
    "characters": [
        {{
            "name": "角色名",
            "archetype": "protagonist/love_interest/antagonist/supporting/minor",
            "identity": "身份（一句话）",
            "age": "年龄数字字符串（只写数字，例如\"18\"）",
            "personality": "性格（几个词）",
            "background": "背景（一两句）",
            "core_goal": "核心目标（一句话）",
            "memory_point": "记忆点（观众能记住的特点，一句话）",
            "skills": ["技能1", "技能2"],
            "secrets": ["隐藏秘密（用于反转）"],
            "arc": "成长弧线（一句话）"
        }}
    ],
    "relationships": [
        {{
            "character1": "角色A",
            "character2": "角色B", 
            "relation_type": "关系类型",
            "dynamic": "关系发展（一句话）"
        }}
    ]
}}

【要求】
1. 人物小传：清晰、明确。每个角色 identity/background/personality 用一两句话说完，不要堆砌形容词、不要书面语。
2. 口语化：像人说话，不要「据悉」「综上所述」这类AI味。
3. 角色结构：主角1-2人、核心配角4-6人、次要2-4人、一共至少7人；有明确反派和CP线；主要角色要有秘密用于反转。
4. age 只能是数字字符串如 "18"，不要带括号说明。

【⚠️⚠️⚠️ JSON格式要求 - 必须严格遵守】
- archetype字段只能是以下值之一："protagonist", "love_interest", "antagonist", "supporting", "minor"
- age字段必须是字符串数字，只能包含数字字符，例如："18"（不要输出“18（重生后）/45（前世）”这类内容）
- 所有字符串使用双引号
- **数组和对象的每个元素后面都要加逗号，最后一个元素除外**
- **特别注意：relationships数组中每个对象的最后一个字段（dynamic）后面不要加逗号，但对象之间要加逗号**
- 不要在JSON中添加注释
- 确保所有的引号、括号、大括号都成对出现
- 确保JSON格式完全正确，可以被json.loads()解析

【⚠️ 极其重要的JSON格式要求】

1. **不要用markdown代码块包裹JSON**
   ❌ 错误：```json {{ ... }} ```
   ✅ 正确：直接输出 {{ ... }}

2. **字符串中不要使用双引号**
   ❌ 错误："说过"xxxxx"这样的话"
   ✅ 正确：说过『xxxxx』这样的话（用『』或「」代替引号）
   ✅ 正确：说过xxxxx这样的话（直接不用引号）
   
   【重要】如果内容中有对话或引用，使用：
   - 『』书名号代替双引号
   - 「」直角引号
   - 或者直接去掉引号

2. **对象必须完整闭合**
   每个对象的最后一个字段后：
   - 不要逗号
   - 必须有右大括号 }}
   
   ❌ 错误示例：
   {{
       "name": "张三",
       "dynamic": "朋友关系",  ← 最后一个字段
       {{  ← 错误！少了 }},
   
   ✅ 正确示例：
   {{
       "name": "张三",
       "dynamic": "朋友关系"  ← 最后一个字段没逗号
   }},  ← 必须有 }},

3. **完整的格式示例**
{{
    "characters": [
        {{"name": "张三", "age": "25"}},  ← 对象结束有 }},
        {{"name": "李四", "age": "30"}}   ← 最后一个对象结束有 }}
    ],
    "relationships": [
        {{
            "character1": "张三",
            "character2": "李四",
            "relation_type": "朋友",
            "dynamic": "从陌生到好友"  ← 对象内最后字段没逗号
        }},  ← 对象结束有 }},（注意：对象之间有逗号）
        {{
            "character1": "李四",
            "character2": "王五",
            "relation_type": "同事",
            "dynamic": "职场关系"  ← 对象内最后字段没逗号
        }}  ← 最后一个对象结束有 }}（注意：最后一个没逗号）
    ]
}}

【检查清单 - 生成前必须自检】
- [ ] 没有 ```json 标记
- [ ] 每个对象的最后一个字段后面没有逗号
- [ ] 每个对象后面都有 }}
- [ ] 对象之间有逗号（最后一个除外）
- [ ] 所有JSON键名和字符串值用英文双引号 "
- [ ] **字符串内容中没有双引号**（用『』或「」代替）
- [ ] 没有注释
- [ ] 没有换行符在字符串中间"""

        # 打印提示词
        print("\n" + "=" * 80)
        print("【策划 - 创建角色提示词】")
        print("=" * 80)
        print(prompt[:1000] + "..." if len(prompt) > 1000 else prompt)
        print("=" * 80 + "\n")
        
        # 优先流式输出再解析 JSON；失败则回退到 Claude 结构化输出
        try:
            self.log("正在创建人物设定（LLM 流式输出）...")
            result = self._chat_stream_then_json(
                prompt, temperature=0.8, max_tokens=24000, max_retries=2, print_prompt=False
            )
            self.log(f"创建了 {len(result.get('characters', []))} 个角色")
            return result
        except Exception as e:
            self.log(f"流式人设解析未通过（{str(e)[:80]}），回退到结构化输出")
        result = self._chat_json_structured(
            prompt,
            json_schema=CHARACTERS_RESPONSE_SCHEMA,
            temperature=0.8,
            max_tokens=24000,
            print_prompt=False,
            fallback_to_normal=True,
        )
        self.log(f"创建了 {len(result.get('characters', []))} 个角色")
        return result
    
    def generate_overall_outline(
        self,
        synopsis: str,
        title: str,
        genre: List[str],
        total_episodes: int = 80,
        inspiration: str = "",
        characters: List[Dict] = None  # 新增
    ) -> str:
        """
        生成总体大纲（故事背景、出场人物、阶段核心事件、关键悬念、冲突与高光卡点）。
        口语化，像短剧不像小说。
        """
        from ..config import get_config
        get_config().current_stage_name = "03_总体大纲"
        self.log("正在生成总体大纲...")
        
        inspiration_block = ""
        if inspiration:
            inspiration_block = f"""
【创作灵感（仅供参考，须尽量融合进大纲；若与梗概或已定角色矛盾，一律以梗概和已定角色为准）】
{inspiration}
"""
        
        char_block = ""
        if characters:
            char_list_str = json.dumps([{"name": c["name"], "identity": c["identity"]} for c in characters], ensure_ascii=False)
            char_block = f"\n【已定角色（请使用这些角色名，不得篡改）】\n{char_list_str}\n"

        prompt = f"""请根据以下剧名和梗概，写一份「总体大纲」。
        
【剧名】{title}
【类型】{', '.join(genre)}
【梗概】{synopsis}
【总集数】{total_episodes}集
{char_block}{inspiration_block}
【优先级】梗概与已定角色为绝对依据；灵感仅作参考。若灵感与梗概或人设冲突，必须以梗概和人设为准，不得采用灵感中的矛盾内容。

【格式要求】
1. **直接描述故事**，像在写故事简介，不要用"介绍"、"咱们聊聊"、"好嘞"、"我的故事背景是"这种口吻
2. **开头直接进入故事**：用时间、地点、人物直接开始，例如"1955年，xxx..."或"故事发生在xxx，主角xxx..."
3. **人物关系自然融入**：在描述事件时自然带出人物，例如"她的儿子xxx"、"继妹xxx与她针锋相对"
4. **事件描述具体且有亮点**：不要写"前期做什么"，而是具体描述"在校园里，xxx故意安排同学对xxx进行霸凌"，要突出**微创新**和**爽点**
5. **分段清晰**：按时间线或事件发展自然分段，每段2-3句，不要啰嗦
6. **字数控制**：整体200-350字，精炼有力，不要堆砌

【必须包含的内容】
- 故事背景：直接描述时代/环境/前提（1句，精炼）
- 出场人物：在描述事件时自然带出主要人物及其关系（融入在事件描述中，不要单独列）
- 阶段核心事件：具体描述前期/中期/后期发生了什么（每段2句，突出**微创新**和**爽点**）
- 关键悬念、冲突与高光卡点：描述具体的冲突场景和转折点（1-2句）

【微创新要求】
- 不要写"一步步揭开"、"一一化解"这种套话
- 要有具体的**微创新点**：比如"将校园霸凌转化为概率论教学现场"、"用选项系统精准选择避开陷阱"
- 突出**爽点**：打脸、反转、身份曝光等要有具体场景
- 避免"第X集"这种具体集数，用"关键时刻"、"转折点"等

【正确示例格式（⚠️注意：示例中的人名仅供格式参考，你必须使用本剧梗概中的角色名，绝对不能抄示例人名！）】
"1955年，容遇教授在国家大礼堂接受终身成就奖时，为保护年仅8岁的儿子纪舜英，不幸被坠落的金属架子砸中身亡。时光流转至2025年，容遇竟意外重生，附身到同名同姓的18岁高中少女身上。此时，她的儿子纪舜英已成为公司董事长，而她更是有了帅气的重孙子。重生后的容遇，面对家族中复杂的人际关系和诸多问题，决定凭借自己的智慧和前世记忆，着手整顿不孝子孙，开启了适应新生活、重振家族荣耀的征程。

在家族内部，容遇的继妹容若瑶与她针锋相对。容若瑶在父亲和继母的偏袒下，骄纵任性，时常设计陷害容遇。在校园里，容若瑶故意安排同学对容遇进行霸凌，试图让她出丑。然而，容遇凭借着自己的智慧和冷静，巧妙化解了一次次危机。她将容若瑶精心设计的校园霸凌场景，转化为概率论教学现场，让在场的人都对她刮目相看，也让容若瑶的阴谋一次次落空。

重孙子纪止渊为纪氏集团的继承人，但遇人不淑，女朋友蓝柔雪人品不当，为了钱而和纪止渊在一起，怕容遇阻碍自己处处陷害，容遇利用智慧巧妙的解决了她，并让纪止渊看清蓝柔雪的为人，与家族成员之间的关系变得更加和谐。"

⚠️⚠️⚠️【严重警告】上面示例中的"容遇、纪舜英、纪止渊、容若瑶、蓝柔雪"是其他剧本的人名，你绝对不能使用！你必须根据本剧的梗概，使用梗概中已经出现的角色名！

【错误写法（禁止）】
- "好嘞，咱们这阵子来聊聊《xxx》这剧的整体框架哈。先说背景：我的故事背景是xxx..."
- "故事背景：xxx。出场人物：xxx。阶段事件：前期xxx，中期xxx..."
- "这是一个关于xxx的故事，主角是xxx，他/她要xxx..."
- "一步步揭开"、"一一化解"、"第X集"这种套话和具体集数

要求：整体控制在200-350字，分段清晰（2-3段），精炼有力，突出微创新和爽点，口语化但直接描述。直接输出大纲正文，不要JSON，不要打招呼，不要用"介绍"口吻。"""

        self.log("正在生成总体大纲（LLM 流式输出）...")
        outline = self._chat_stream(prompt, temperature=0.8)
        self.log("总体大纲生成完成")
        return outline.strip()
    
    def generate_multi_episode_outline(
        self,
        synopsis: str,
        overall_outline: str,
        characters: List[Dict],
        total_episodes: int = 80,
        inspiration: str = ""
    ) -> str:
        """
        生成多集大纲（按阶段分段：1-10集、10-30集、30-60集、60-end集）
        
        Args:
            synopsis: 故事梗概
            overall_outline: 总体大纲
            characters: 角色列表
            total_episodes: 总集数
            inspiration: 创作灵感（关键爆点设计等）
        
        Returns:
            多集大纲文本
        """
        from ..config import get_config
        get_config().current_stage_name = "06_多集大纲"
        self.log("正在生成多集大纲（分段）...")
        
        inspiration_block = ""
        if inspiration:
            inspiration_block = f"\n【创作灵感（包含关键爆点设计，请务必融合进各阶段大纲）】\n{inspiration}\n"
        
        # 根据总集数动态计算分段
        if total_episodes <= 60:
            # 如果总集数<=60，调整分段
            seg1_end = min(10, total_episodes // 4)
            seg2_end = min(30, total_episodes * 2 // 3)
            seg3_end = total_episodes
            segments = [
                (1, seg1_end, "开局阶段"),
                (seg1_end + 1, seg2_end, "发展阶段"),
                (seg2_end + 1, seg3_end, "高潮/结局阶段")
            ]
        else:
            # 标准分段（80-100集）
            segments = [
                (1, 10, "开局阶段"),
                (11, 30, "前期发展阶段"),
                (31, 60, "中期升级阶段"),
                (61, total_episodes, "后期高潮/结局阶段")
            ]
        
        segments_desc = "\n".join([f"- 第{s[0]}-{s[1]}集：{s[2]}" for s in segments])
        
        prompt = f"""请根据故事梗概和总体大纲，生成多集大纲。将{total_episodes}集故事按阶段分段，每段确定核心故事。

【剧名与梗概】
{synopsis}

【总体大纲】
{overall_outline}
{inspiration_block}
【主要角色】
{json.dumps([{"name": c["name"], "identity": c["identity"]} for c in characters[:8]], ensure_ascii=False)}

【总集数】{total_episodes}集

【分段要求】
{segments_desc}

【输出格式】
按以下格式输出每个阶段的大纲：

**第X-Y集：阶段名**
核心故事：这个阶段讲什么故事（1-2个核心故事线，不要超过2个）
主要冲突：核心矛盾是什么
关键转折：本阶段的重要转折点
结尾钩子：本阶段结尾留什么悬念

【关键要求】
1. 每个阶段1-2个核心故事，不要堆叠太多
2. 控制单集字数：一个故事拆成10-30集，平均每集500-700字，所以每个故事不应该有太多事件
3. 明确各阶段的核心冲突，确保剧情递进
4. 口语化，精炼，不要AI味
5. 每段大纲100-200字，不要写太长

直接输出大纲文本，不要JSON格式。"""

        self.log("正在生成多集大纲（LLM 流式输出）...")
        multi_episode_outline = self._chat_stream(prompt, temperature=0.8)
        multi_episode_outline = multi_episode_outline.strip()
        # 显式写入阶段日志，确保 06_多集大纲.txt 里能看到正文（不依赖 _chat 的 RESPONSE 追加）
        self._append_stage_log("\n【多集大纲正文】\n" + multi_episode_outline)
        self.log("多集大纲生成完成")
        return multi_episode_outline
    
    def _get_structure_guide(self, start: int, end: int, total: int, is_near_end: bool, is_last_batch: bool) -> str:
        """
        根据当前批次位置，生成结构指导
        
        Args:
            start: 起始集数
            end: 结束集数
            total: 总集数
            is_near_end: 是否接近结尾（后30%）
            is_last_batch: 是否最后一批
        
        Returns:
            结构指导文本
        """
        progress = (start - 1) / total
        
        # 特殊处理：前三集（黄金开场期）
        if start <= 3:
            return """【⚠️⚠️⚠️ 结构指导 - 黄金开场期！生死线！】
前三集决定观众是否付费！必须做到：

第1集：极致受辱/危机 + 身份觉醒
- 开篇必须是极具冲击力的场景，5秒抓人
- 主角一出场就处于极端不公平或危险状态
- 明确主线：主角是谁、目标是什么、阻碍是什么
- 抛出身份反差（卑微表象 vs 隐藏实力）
- 钩子必须超强：让观众"睡不着觉"

第2集：初步反击/打脸 + 更大势力介入
- 主角展示部分实力，让反派初尝苦果
- 但要留后手，不能一次放完大招
- 钩子：新的危机或更强反派登场

第3集：核心矛盾升级 + 抛出终极目标
- 建立贯穿全剧的主线任务
- 让观众知道这个故事要讲什么
- 钩子：主线冲突正式展开

⚠️ 前三集不精彩 = 观众流失 = 项目失败！"""
        
        # 特殊处理：第4-10集（钩子强化期）
        if start <= 10 and start > 3:
            return """【结构指导 - 钩子强化期】
- 前10集是付费转化关键期！
- 每集结尾钩子都要够强
- 节奏：快速推进，每集都有爽点
- 重点：持续打脸、身份反差、支线展开
- 钩子：以"悬念"、"反转"、"危机"为主
- 禁止平淡结尾！"""
        
        if progress < 0.25:
            # 前25%：铺陈阶段（第10集之后）
            return """【结构指导 - 铺陈阶段】
- 当前处于故事前期，主要任务是建立冲突和角色关系
- 节奏：快速展开，抓住观众注意力
- 重点：身份反差、初步冲突、建立主线目标
- 钩子：以"悬念"和"打脸"为主"""
        
        elif progress < 0.70:
            # 中间45%：发展阶段
            return """【结构指导 - 发展阶段】
- 当前处于故事中期，主要任务是冲突升级和剧情推进
- 节奏：稳步发展，多线交织
- 重点：主角成长、反派升级、支线展开
- 钩子：多样化，包括"反转"、"身份揭示"、"新危机"等"""
        
        elif is_last_batch:
            # 最后一批：高潮+结局
            climax_start = max(1, total - 5)  # 倒数5集开始高潮
            final_episodes = total - 1  # 倒数2集
            
            return f"""【结构指导 - 高潮与结局阶段】⚠️ 这是最后一批！
- 当前处于故事收尾阶段，必须安排好结局
- 第{start}-{climax_start-1}集（如有）：收束支线，解决次要冲突
- 第{climax_start}-{total-2}集：主线冲突高潮对决
- 第{total-1}集：高潮决战，主要冲突接近解决
- 第{total}集：**大结局**
  * 必须解决主线冲突，给主角一个明确的结局
  * 主要角色的命运都要有交代
  * 可以留1-2个小伏笔暗示未来发展，但不能是核心冲突未解决
  * hook_type 应该是 "resolution"（结局）而不是 "cliffhanger"
  * 结尾要有完结感，让观众满意"""
        
        else:
            # 后30%但不是最后一批：收束准备阶段
            return """【结构指导 - 收束准备阶段】
- 当前进入故事后期，剧情应该逐步向高潮推进
- 节奏：开始收紧，减少新线索，聚焦主线
- 重点：开始解决支线冲突，为主线高潮做铺垫
- 次要角色的故事线要开始收尾
- 主线冲突进入白热化阶段
- 钩子：以"危机升级"和"决战前奏"为主"""
    
    def generate_beat_sheet(
        self,
        synopsis: str,
        characters: List[Dict],
        total_episodes: int = 80,
        multi_episode_outline: str = "",
        inspiration: str = ""
    ) -> Dict[str, Any]:
        """
        生成分集大纲（节拍表）
        
        Args:
            synopsis: 故事梗概
            characters: 人物列表
            total_episodes: 总集数
            multi_episode_outline: 多集大纲（分段）
            inspiration: 创作灵感（关键爆点设计等）
        
        Returns:
            分集大纲
        """
        from ..config import get_config
        get_config().current_stage_name = "07_分集大纲"
        self.log(f"正在生成{total_episodes}集分集大纲...")
        
        # 分批生成，每次10集（减小批次，降低截断风险）
        all_beats = []
        batch_size = 10
        max_retries_per_batch = 3  # 每批次最多重试次数
        
        for start in range(1, total_episodes + 1, batch_size):
            end = min(start + batch_size - 1, total_episodes)
            expected_count = end - start + 1
            
            # 带重试的批次生成
            for retry in range(max_retries_per_batch):
                retry_suffix = f"（重试{retry}）" if retry > 0 else ""
                self.log(f"  生成第{start}-{end}集大纲{retry_suffix}...")
                
                valid_beats = self._generate_beat_batch(
                    start, end, total_episodes, synopsis, characters, all_beats, multi_episode_outline, inspiration
                )
                
                # 检查是否获取到足够的beats（至少80%成功率）
                if len(valid_beats) >= expected_count * 0.8:
                    break
                elif retry < max_retries_per_batch - 1:
                    self.log(f"  ⚠️ 只获取到{len(valid_beats)}/{expected_count}集，重试...")
            
            all_beats.extend(valid_beats)
            self.log(f"  ✅ 已完成{len(all_beats)}/{total_episodes}集")
        
        # 检测并补充缺失的集数，确保每一集都有大纲
        all_beats = self._fill_missing_beats(all_beats, total_episodes, synopsis, characters, multi_episode_outline)
        
        # 按集数排序
        all_beats.sort(key=lambda x: x.get('episode', 0))
        
        self.log(f"分集大纲生成完成，共{len(all_beats)}集")
        return {"beats": all_beats}
    
    def generate_beat_sheet_batch(
        self,
        start: int,
        end: int,
        total_episodes: int,
        synopsis: str,
        characters: List[Dict],
        existing_beats: List[Dict],
        multi_episode_outline: str = "",
        inspiration: str = ""
    ) -> Dict[str, Any]:
        """
        只生成 [start, end] 这一批的分集大纲，用于「每批审核后再继续」流程。
        
        Returns:
            {"beats": 本批次的 beat 列表，按 episode 排序}
        """
        expected_count = end - start + 1
        batch_size = expected_count
        max_retries_per_batch = 3
        valid_beats: List[Dict] = []
        
        for retry in range(max_retries_per_batch):
            retry_suffix = f"（重试{retry}）" if retry > 0 else ""
            self.log(f"  生成第{start}-{end}集大纲{retry_suffix}...")
            valid_beats = self._generate_beat_batch(
                start, end, total_episodes, synopsis, characters,
                existing_beats, multi_episode_outline, inspiration
            )
            if len(valid_beats) >= expected_count * 0.8:
                break
            if retry < max_retries_per_batch - 1:
                self.log(f"  ⚠️ 只获取到{len(valid_beats)}/{expected_count}集，重试...")
        
        combined = list(existing_beats) + list(valid_beats)
        existing_episodes = {b.get("episode") for b in combined}
        missing_in_range = [i for i in range(start, end + 1) if i not in existing_episodes]
        if missing_in_range:
            self.log(f"  🔄 补充本批缺失集数：{missing_in_range}")
            filled = self._generate_specific_beats(
                missing_in_range, synopsis, characters, combined, multi_episode_outline
            )
            combined = combined + filled
        batch_only = [b for b in combined if start <= b.get("episode", 0) <= end]
        batch_only.sort(key=lambda x: x.get("episode", 0))
        self.log(f"  ✅ 第{start}-{end}集大纲生成完成（共{len(batch_only)}集）")
        return {"beats": batch_only}
    
    def _generate_beat_batch(
        self,
        start: int,
        end: int,
        total_episodes: int,
        synopsis: str,
        characters: List[Dict],
        existing_beats: List[Dict],
        multi_episode_outline: str = "",
        inspiration: str = ""
    ) -> List[Dict]:
        """
        生成单批次的分集大纲
        
        Args:
            start: 起始集数
            end: 结束集数
            total_episodes: 总集数
            synopsis: 故事梗概
            characters: 角色列表
            existing_beats: 已生成的beats（用于构建上下文）
            multi_episode_outline: 多集大纲（分段）
            inspiration: 创作灵感（关键爆点设计等）
        
        Returns:
            有效的beat列表
        """
        # 构建上下文（使用安全的字段访问方式）
        previous_beats = existing_beats[-10:] if existing_beats else []
        previous_context = ""
        last_episode_info = ""
        
        if previous_beats:
            previous_context = "【前情提要（最近10集剧情脉络）】\n" + "\n".join([
                f"第{b.get('episode', '?')}集：{b.get('synopsis', '（内容缺失）')} → 结尾钩子：{b.get('ending_hook', '（钩子缺失）')}"
                for b in previous_beats
            ])
            
            # 特别提取上一集的信息，用于强关联
            last_beat = previous_beats[-1]
            last_ep_num = last_beat.get('episode', start - 1)
            last_episode_info = f"""
【紧接上集（第{last_ep_num}集）状态 - 极其重要】
剧情：{last_beat.get('synopsis', '（内容缺失）')}
结尾钩子：{last_beat.get('ending_hook', '（钩子缺失）')}
👉 第{start}集开头必须紧接这个钩子！解决它或让危机升级！禁止跳跃时间线！
"""
        
        # 计算当前批次在整体中的位置
        progress_percentage = (start - 1) / total_episodes
        is_last_batch = end == total_episodes
        is_near_end = progress_percentage >= 0.7  # 后30%进入收束阶段
        
        # 构建结构指导
        structure_guide = self._get_structure_guide(start, end, total_episodes, is_near_end, is_last_batch)
        
        multi_ep_block = ""
        if multi_episode_outline:
            multi_ep_block = f"\n【多集大纲（分段规划，请严格遵循）】\n{multi_episode_outline}\n"
        
        # 分集大纲不注入灵感，以梗概+多集大纲+已有人设与历史分集为准
        prompt = f"""请为短剧生成第{start}集到第{end}集的分集大纲。
你的核心任务是：保证剧情极度连贯，集与集之间无缝衔接，就像一部连续的长电影被切开一样。

【整体信息】
- 总集数：{total_episodes}集
- 当前批次：第{start}-{end}集（整体进度：{progress_percentage*100:.0f}%）
{structure_guide}

【故事梗概】
{synopsis}
{multi_ep_block}
【主要角色】
{json.dumps([{"name": c["name"], "identity": c["identity"]} for c in characters], ensure_ascii=False)}

{previous_context}
{last_episode_info}

请以JSON格式返回，格式如下：
{{
    "beats": [
        {{
            "episode": 集数,
            "synopsis": "本集剧情（30-60字一小段，只写爆点）",
            "ending_hook": "本集结尾钩子（一句话20字内）",
            "hook_type": "face_slap/identity_reveal/reversal/cliffhanger/resolution/..."
        }}
    ]
}}

【⚠️⚠️⚠️ 连贯性要求 - 拒绝割裂！】
1. **强因果链**：第N集的事件必须导致第N+1集的开头。不要出现"第二天"、"转眼间"这种无意义的时间跳跃，除非剧情需要。
2. **钩子必接**：上一集结尾留的钩子，这一集开头必须马上有反应/处理。
3. **情绪流不断**：如果上一集结尾是情绪高点（如主角被打耳光），这一集开头必须承接这个情绪（如主角反手打回去或隐忍），不能突然跳到新场景。

【⚠️ 大纲写法 - 拒绝小说体】
每集梗概：30-60字一小段，只写爆点/关键动作。结尾钩子：一句话20字内，留悬念。
不要像写小说！不要长句、不要细节描写、不要心理和环境描写。

❌ 错误（写太长、像小说）：
synopsis 写一整段话、带对话、带"就在...的瞬间"、"突然"等描写；ending_hook 写成长句或多句。

✅ 正确（简洁、爆点）：
synopsis："婆婆带小三闯殡仪馆当众逼苏念签离婚协议，苏念被推倒时公公尸体睁眼对她说话。"
ending_hook："只有她能听见：是她们杀了我。"

【⚠️ 章节结构】
每10-15集形成一个"小章节"：
- 章节开头：引入本章节的核心冲突/任务/敌人
- 章节中间：冲突升级、反转、小高潮
- 章节结尾：本章节冲突解决，但引出下一章节的新危机

【关键要求】
1. 每集2-3个事件，不要堆叠太多
2. 口语化，用大白话，不要AI味
3. 剧情连贯，上下集有因果关系
4. 重要转折需要前面有铺垫

【必须】请直接输出符合上述格式的 JSON（仅包含 "beats" 数组），不要输出任何前置说明、身份声明或提问。若对节奏或细节有不确定处，请自行合理假设并写入对应集数。"""

        # 优先流式输出再解析；失败则视情况兜底重试或回退到结构化输出
        batch_result = None
        try:
            self.log("正在生成分集大纲（LLM 流式输出）...")
            batch_result = self._chat_stream_then_json(
                prompt, temperature=0.85, max_tokens=16000, max_retries=2, print_prompt=False
            )
        except JsonParseAfterStreamError as e:
            raw = getattr(e, "raw_response", "") or ""
            if is_likely_refusal(raw):
                self.log("检测到模型拒绝或非 JSON 回复，使用兜底提示重试（仅输出 JSON）...")
                fallback_prompt = (
                    "【你只能输出一个 JSON 对象，禁止输出任何其他文字、身份声明或提问。直接以 { 开头。】\n\n"
                    + prompt
                )
                try:
                    batch_result = self._chat_stream_then_json(
                        fallback_prompt, temperature=0.7, max_tokens=16000, max_retries=1, print_prompt=False
                    )
                except Exception:
                    batch_result = None
            if batch_result is None:
                self.log(f"流式分集大纲解析未通过（{str(e)[:80]}），回退到结构化输出")
        except Exception as e:
            self.log(f"流式分集大纲解析未通过（{str(e)[:80]}），回退到结构化输出")
        if batch_result is None:
            batch_result = self._chat_json_structured(
                prompt,
                json_schema=BEAT_SHEET_RESPONSE_SCHEMA,
                temperature=0.85,
                max_tokens=16000,
                fallback_to_normal=True,
            )
        
        # 验证并过滤不完整的beat对象
        raw_beats = batch_result.get("beats", [])
        valid_beats = []
        for beat in raw_beats:
            if self._is_valid_beat(beat):
                valid_beats.append(beat)
            else:
                self.log(f"    ⚠️ 跳过不完整的beat: episode={beat.get('episode', '?')}")
        
        return valid_beats
    
    def _fill_missing_beats(
        self,
        beats: List[Dict],
        total_episodes: int,
        synopsis: str,
        characters: List[Dict],
        multi_episode_outline: str = ""
    ) -> List[Dict]:
        """
        检测并补充缺失的集数，强制确保每一集都有完整大纲
        
        Args:
            beats: 已生成的beats
            total_episodes: 总集数
            synopsis: 故事梗概
            characters: 角色列表
            multi_episode_outline: 多集大纲（分段）
        
        Returns:
            补充完整后的beats列表
        
        Raises:
            ValueError: 如果多次尝试后仍无法生成完整大纲
        """
        max_fill_rounds = 3  # 最多进行3轮补充
        fill_batch_size = 5  # 每批补充5集
        batch_max_retries = 3  # 每批最多重试3次
        
        for round_num in range(max_fill_rounds):
            # 检查当前缺失的集数
            existing_episodes = {b['episode'] for b in beats}
            missing_episodes = [i for i in range(1, total_episodes + 1) if i not in existing_episodes]
            
            if not missing_episodes:
                self.log(f"  ✅ 大纲完整，所有{total_episodes}集均已生成")
                return beats
            
            round_suffix = f"（第{round_num + 1}轮）" if round_num > 0 else ""
            self.log(f"  ⚠️ 发现{len(missing_episodes)}集大纲缺失{round_suffix}：{missing_episodes[:10]}{'...' if len(missing_episodes) > 10 else ''}")
            self.log(f"  🔄 正在补充缺失的大纲...")
            
            # 分批补充缺失的集数
            for i in range(0, len(missing_episodes), fill_batch_size):
                batch = missing_episodes[i:i+fill_batch_size]
                
                # 单批次带重试的补充
                for retry in range(batch_max_retries):
                    retry_suffix = f"（重试{retry}）" if retry > 0 else ""
                    self.log(f"    补充第{batch}集{retry_suffix}...")
                    
                    new_beats = self._generate_specific_beats(batch, synopsis, characters, beats, multi_episode_outline)
                    
                    # 检查成功获取的集数
                    obtained_episodes = {b['episode'] for b in new_beats}
                    success_count = len(obtained_episodes & set(batch))
                    
                    if success_count >= len(batch) * 0.8:  # 至少80%成功率
                        beats.extend(new_beats)
                        self.log(f"    ✅ 成功补充{success_count}/{len(batch)}集")
                        break
                    elif retry < batch_max_retries - 1:
                        self.log(f"    ⚠️ 只获取{success_count}/{len(batch)}集，重试...")
                    else:
                        # 最后一次尝试，即使不完整也添加
                        beats.extend(new_beats)
                        self.log(f"    ⚠️ 最终获取{success_count}/{len(batch)}集，继续下一批")
                
                # 显示总体进度
                current_existing = {b['episode'] for b in beats}
                current_total = len(current_existing)
                self.log(f"    📊 当前进度：{current_total}/{total_episodes}集")
        
        # 最终强制检查
        final_existing = {b['episode'] for b in beats}
        final_missing = [i for i in range(1, total_episodes + 1) if i not in final_existing]
        
        if final_missing:
            error_msg = f"❌ 无法生成完整大纲！经过{max_fill_rounds}轮尝试后仍缺失{len(final_missing)}集：{final_missing}"
            self.log(f"  {error_msg}")
            raise ValueError(error_msg)
        
        self.log(f"  ✅ 所有{total_episodes}集大纲已完整")
        return beats
    
    def _generate_specific_beats(
        self,
        episode_numbers: List[int],
        synopsis: str,
        characters: List[Dict],
        existing_beats: List[Dict],
        multi_episode_outline: str = ""
    ) -> List[Dict]:
        """
        生成指定集数的大纲（用于补充缺失的集数）
        
        Args:
            episode_numbers: 需要生成的集数列表
            synopsis: 故事梗概
            characters: 角色列表
            existing_beats: 已有的beats（用于提供上下文）
            multi_episode_outline: 多集大纲（分段）
        
        Returns:
            生成的beat列表
        """
        # 为每个缺失的集数找前后文脉络
        context_lines = []
        sorted_existing = sorted(existing_beats, key=lambda x: x.get('episode', 0))
        
        for ep_num in episode_numbers:
            # 找前一集
            prev_beats = [b for b in sorted_existing if b.get('episode', 0) < ep_num]
            if prev_beats:
                prev = prev_beats[-1]
                context_lines.append(f"第{prev['episode']}集（前一集）：{prev.get('synopsis', '')} → 钩子：{prev.get('ending_hook', '')}")
            
            # 找后一集
            next_beats = [b for b in sorted_existing if b.get('episode', 0) > ep_num]
            if next_beats:
                next_b = next_beats[0]
                context_lines.append(f"第{next_b['episode']}集（后一集）：{next_b.get('synopsis', '')}")
        
        context = "\n".join(context_lines[:10]) if context_lines else "（无已有剧情）"
        episodes_str = ", ".join(str(e) for e in episode_numbers)
        
        multi_ep_block = ""
        if multi_episode_outline:
            multi_ep_block = f"\n【多集大纲（分段规划）】\n{multi_episode_outline}\n"
        
        prompt = f"""请为短剧补充以下缺失集数的大纲：第{episodes_str}集
你的任务是填补剧情真空，连接上下文，使剧情流畅过渡。

【故事梗概】
{synopsis}
{multi_ep_block}
【主要角色】
{json.dumps([{"name": c["name"], "identity": c["identity"]} for c in characters], ensure_ascii=False)}

{context}

请以JSON格式返回，格式如下：
{{
    "beats": [
        {{
            "episode": 集数,
            "synopsis": "本集剧情（30-60字一小段，只写爆点）",
            "ending_hook": "本集结尾钩子（一句话20字内）",
            "hook_type": "cliffhanger/reversal/face_slap/identity_reveal/...",
            "key_conflict": "本集核心冲突"
        }}
    ]
}}

【关键要求】
1. 必须生成以下集数：{episodes_str}
2. **无缝连接**：生成的剧情必须紧接"前一集"的钩子，并最终导向"后一集"的开头。
3. synopsis 与 ending_hook 都要简短：梗概30-60字、钩子20字内，突出爆点，不要写小说
4. 剧情承上启下，口语化，不要AI味"""

        # 优先流式输出再解析；失败则回退到结构化输出
        result = None
        try:
            result = self._chat_stream_then_json(
                prompt, temperature=0.7, max_tokens=8000, max_retries=2, print_prompt=False
            )
        except Exception as e:
            self.log(f"流式补充分集解析未通过（{str(e)[:80]}），回退到结构化输出")
        if result is None:
            result = self._chat_json_structured(
                prompt,
                json_schema=BEAT_SHEET_RESPONSE_SCHEMA,
                temperature=0.7,
                max_tokens=8000,
                fallback_to_normal=True,
            )
        
        try:
            raw_beats = result.get("beats", [])
            valid_beats = [b for b in raw_beats if self._is_valid_beat(b)]
            return valid_beats
        except Exception as e:
            self.log(f"    ❌ 补充生成失败：{str(e)[:100]}")
            return []
    
    def _is_valid_beat(self, beat: Dict) -> bool:
        """
        验证beat对象是否完整有效
        
        Args:
            beat: beat字典
        
        Returns:
            是否有效
        """
        required_fields = ["episode", "synopsis", "ending_hook"]
        
        for field in required_fields:
            if field not in beat:
                return False
            value = beat[field]
            if value is None:
                return False
            if isinstance(value, str):
                stripped = value.strip()
                # 只检查是否为空或过短（至少要有几个字）
                if len(stripped) < 5:
                    return False
        
        return True
    
    def _detect_repetition_loop(self, text: str, threshold: float = 0.5) -> bool:
        """
        检测文本是否存在重复循环（模型退化现象）
        
        Args:
            text: 待检测的文本
            threshold: 重复比例阈值，超过此比例视为重复循环
        
        Returns:
            是否检测到重复循环
        """
        if not text or len(text) < 20:
            return False
        
        # 方法1：检查是否有连续重复的短模式（如"满级满级满级"）
        for pattern_len in range(2, 6):
            if len(text) < pattern_len * 5:
                continue
            pattern = text[:pattern_len]
            repeat_count = text.count(pattern)
            if repeat_count > len(text) / (pattern_len * 2):
                return True
        
        # 方法2：检查前后部分是否高度相似
        mid = len(text) // 2
        first_half = text[:mid]
        second_half = text[mid:]
        
        # 如果前后两半完全相同或高度相似
        if first_half == second_half:
            return True
        
        # 方法3：检查是否有大量连续重复字符
        if len(text) > 50:
            # 统计最常见的2-gram
            bigrams = [text[i:i+2] for i in range(len(text)-1)]
            if bigrams:
                from collections import Counter
                most_common = Counter(bigrams).most_common(1)[0]
                if most_common[1] > len(text) * threshold:
                    return True
        
        return False
    
    def create_characters_for_names(
        self,
        names: List[str],
        synopsis: str,
        overall_outline: str,
        genre: List[str],
        target_audience: str
    ) -> Dict[str, Any]:
        """
        根据指定的人名列表补充人设
        用于处理大纲中出现但没有人设的角色
        
        Args:
            names: 需要补充人设的人名列表
            synopsis: 故事梗概
            overall_outline: 总体大纲
            genre: 类型标签
            target_audience: 目标受众
        
        Returns:
            包含 characters 列表的字典
        """
        if not names:
            return {"characters": []}
        
        self.log(f"正在为以下人名补充人设：{', '.join(names)}")
        
        prompt = f"""请为以下人名创建角色人设。这些角色在故事梗概和大纲中出现，但还没有详细的人设。

【需要补充人设的人名】
{', '.join(names)}

【故事梗概】
{synopsis}

【总体大纲】
{overall_outline[:1500] if overall_outline else '（无）'}

【类型】{', '.join(genre)}
【受众】{target_audience}

请根据梗概和大纲中对这些人物的描述，推断他们的身份、性格、背景等信息。

返回JSON格式：
{{
    "characters": [
        {{
            "name": "人名（必须使用给定的名字）",
            "archetype": "protagonist/antagonist/love_interest/supporting/minor",
            "identity": "身份，一句话概括",
            "age": 25,
            "personality": "性格特点",
            "background": "背景故事",
            "core_goal": "核心目标",
            "memory_point": "记忆点/标志性特征",
            "skills": ["技能1", "技能2"],
            "secrets": ["秘密1"],
            "arc": "角色成长弧线"
        }}
    ]
}}

【要求】
1. 人名必须使用给定的名字，不能改
2. 根据大纲中的描述推断角色定位
3. 如果大纲中信息不足，可以合理推断
4. 每个角色的信息要完整"""

        # 增加max_tokens确保输出不被截断
        result = self._chat_json(prompt, temperature=0.7, max_tokens=8000)
        
        self.log(f"补充了 {len(result.get('characters', []))} 个角色人设")
        return result
    
    def run(
        self,
        user_idea: str,
        reference_style: Optional[str] = None,
        total_episodes: Optional[int] = None
    ) -> Bible:
        """
        执行完整的策划流程
        
        Args:
            user_idea: 用户创意概念
            reference_style: 参考风格描述（仅用于格式参考）
        
        Returns:
            初始化的Bible对象
        """
        self.log("=" * 50)
        self.log("[策划Agent] 开始策划流程")
        self.log("=" * 50)
        
        # 0. 获取趋势总结
        try:
            self.log("[策划Agent] 正在获取短剧爆款趋势...")
            from ..utils.trend_search import search_short_drama_trends
            trend_hint = search_short_drama_trends(debug=False)
            self.log("[策划Agent] ✅ 趋势分析完成")
        except Exception as e:
            self.log(f"[策划Agent] ⚠️ 获取趋势失败，将跳过: {e}")
            trend_hint = ""

        # 1. 生成灵感（头脑风暴）
        self.log("[策划Agent] 正在生成创作灵感（头脑风暴阶段）...")
        inspiration = self.generate_inspiration(user_idea, reference_style, trend_hint)
        self.log("[策划Agent] ✅ 创作灵感生成完成")
        self.log(f"[策划Agent] 💡 灵感概要：{inspiration[:100]}..." if len(inspiration) > 100 else f"[策划Agent] 💡 灵感：{inspiration}")

        # 2. 生成故事梗概
        self.log("[策划Agent] 正在生成故事梗概...")
        synopsis_data = self.generate_synopsis(user_idea, reference_style, trend_hint, inspiration)
        self.log(f"[策划Agent] ✅ 故事梗概生成完成")
        self.log(f"[策划Agent] 📖 剧本标题：{synopsis_data['title']}")
        self.log(f"[策划Agent] 🎭 故事类型：{synopsis_data['genre']}")
        
        # 如果指定了总集数，覆盖模型输出
        if total_episodes:
            synopsis_data["total_episodes"] = total_episodes

        # 3. 创建人物
        self.log(f"[策划Agent] 正在创建人物角色...")
        characters_data = self.create_characters(
            synopsis_data["synopsis"],
            synopsis_data["genre"],
            synopsis_data["target_audience"],
            overall_outline="",  # 此时还没生成总体大纲，先传空，稍后更新
            inspiration=inspiration
        )
        self.log(f"[策划Agent] ✅ 人物角色创建完成（共{len(characters_data['characters'])}位）")
        
        # 4. 生成总体大纲（需结合灵感）
        # 注意：这里先生成总体大纲，再生成多集大纲
        self.log(f"[策划Agent] 正在生成总体大纲...")
        overall_outline = self.generate_overall_outline(
            synopsis_data["synopsis"],
            synopsis_data["title"],
            synopsis_data["genre"],
            total_episodes=synopsis_data.get("total_episodes", 80),
            inspiration=inspiration,
            characters=characters_data["characters"]
        )
        self.log(f"[策划Agent] ✅ 总体大纲生成完成")
        
        # 5. 生成多集大纲（分段），再生成分集大纲
        total_eps = synopsis_data.get("total_episodes", 80)
        self.log(f"[策划Agent] 正在生成{total_eps}集的多集大纲...")
        multi_episode_outline = self.generate_multi_episode_outline(
            synopsis_data["synopsis"],
            overall_outline,
            characters_data["characters"],
            total_episodes=total_eps
        )
        self.log(f"[策划Agent] ✅ 多集大纲生成完成")
        
        self.log(f"[策划Agent] 正在生成每集的详细节奏点...")
        beat_sheet_data = self.generate_beat_sheet(
            synopsis_data["synopsis"],
            characters_data["characters"],
            total_eps,
            multi_episode_outline=multi_episode_outline
        )
        self.log(f"[策划Agent] ✅ 分集大纲生成完成（共{len(beat_sheet_data['beats'])}集）")
        
        # 6. 构建Bible
        bible = Bible(
            title=synopsis_data["title"],
            genre=synopsis_data["genre"],
            target_audience=synopsis_data["target_audience"],
            synopsis=synopsis_data["synopsis"],
            theme=synopsis_data.get("theme", ""),
            total_episodes=synopsis_data.get("total_episodes", 80)
        )
        bible.overall_outline = overall_outline
        bible.multi_episode_outline = multi_episode_outline
        
        # 添加角色
        for char_data in characters_data["characters"]:
            # age 容错：允许 LLM 传回字符串（如 "18" 或 "18（重生后）"），提取第一个数字
            age_val = char_data.get("age")
            if isinstance(age_val, str):
                import re
                m = re.search(r"\d+", age_val)
                age_val = int(m.group(0)) if m else None

            bg = char_data.get("background", "")
            if char_data.get("core_goal"):
                bg += " 核心目标：" + str(char_data["core_goal"])
            if char_data.get("memory_point"):
                bg += " 记忆点：" + str(char_data["memory_point"])
            character = Character(
                name=char_data["name"],
                identity=char_data["identity"],
                archetype=CharacterArchetype(char_data["archetype"]),
                age=age_val,
                personality=char_data.get("personality", ""),
                background=bg,
                skills=char_data.get("skills", []),
                secrets=char_data.get("secrets", []),
                arc=char_data.get("arc", "")
            )
            bible.add_character(character)
            
            if char_data["archetype"] == "protagonist":
                bible.protagonist_name = char_data["name"]
        
        # 添加角色关系
        for rel in characters_data.get("relationships", []):
            char1 = bible.get_character(rel["character1"])
            if char1:
                from ..models.character import CharacterRelationship
                char1.add_relationship(CharacterRelationship(
                    target=rel["character2"],
                    relation_type=rel["relation_type"],
                    sentiment="neutral",
                    notes=rel.get("dynamic", "")
                ))
        
        # 添加分集大纲
        beat_sheet = BeatSheet()
        for beat in beat_sheet_data["beats"]:
            beat_sheet.add_beat(
                beat["episode"],
                beat["synopsis"],
                beat["ending_hook"],
                beat["hook_type"]
            )
        bible.beat_sheet = beat_sheet
        
        # 提取初始冲突
        if beat_sheet_data.get("beats"):
            first_beats = beat_sheet_data["beats"][:5]
            for beat in first_beats:
                key_conflict = beat.get("key_conflict")
                if key_conflict:
                    bible.active_conflicts.append(key_conflict)
        
        self.log("=" * 50)
        self.log(f"[策划Agent] 🎉 策划完成！《{bible.title}》")
        self.log(f"[策划Agent]   📚 类型：{', '.join(bible.genre)}")
        self.log(f"[策划Agent]   👥 角色：{len(bible.characters)}个")
        self.log(f"[策划Agent]   📺 集数：{bible.total_episodes}集")
        self.log("=" * 50)
        
        return bible
