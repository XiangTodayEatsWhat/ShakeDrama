"""
批量生成和智能分割模块

新的生成逻辑：
1. 一次生成5集的完整文本（2500-3500字）
2. 智能分割成5集，每集约600字
3. 对衔接处添加钩子
"""
import re
from typing import List, Tuple
from ..models import Bible, Episode


def generate_batch_script(screenwriter, bible: Bible, start_ep: int, end_ep: int) -> str:
    """
    一次性生成多集的完整剧本
    
    Args:
        screenwriter: 编剧Agent实例
        bible: 世界观圣经
        start_ep: 起始集数
        end_ep: 结束集数
    
    Returns:
        完整的剧本文本（2500-3500字）
    """
    num_episodes = end_ep - start_ep + 1
    target_length = num_episodes * 600  # 目标总长度
    
    # 构建完整提示词
    beats_text = []
    for ep_num in range(start_ep, end_ep + 1):
        beat = (bible.beat_sheet.get_beat(ep_num) if bible.beat_sheet else None) or {}
        beats_text.append(f"第{ep_num}集：{beat.get('synopsis', '')}")
    
    # 获取前情摘要
    prev_summary = ""
    if bible.episodes:
        prev_eps = sorted([ep for ep in bible.episodes if ep.number < start_ep], key=lambda e: e.number)
        if prev_eps:
            prev_lines = []
            for prev_ep in prev_eps[-3:]:  # 最近3集
                synopsis_text = prev_ep.synopsis[:80] + "..." if prev_ep.synopsis and len(prev_ep.synopsis) > 80 else (prev_ep.synopsis or "")
                prev_lines.append(f"第{prev_ep.number}集：{synopsis_text}")
            prev_summary = "\n".join(prev_lines)
    
    # 角色信息
    char_info = "\n".join([
        f"- {name}: {char.identity}，{char.personality}"
        for name, char in bible.characters.items()
    ])
    char_names_str = "、".join(list(bible.characters.keys()))
    
    # 冲突信息
    conflicts_str = "、".join(bible.active_conflicts[:5]) if bible.active_conflicts else "无"
    
    prompt = f"""请根据以下大纲，一次性写出第{start_ep}-{end_ep}集的完整剧本（约{target_length}字）。

===== 世界观圣经 =====
【剧名】{bible.title}
【故事梗概】{bible.synopsis or '（未设定）'}
【角色设定】
{char_info}
【角色名列表】{char_names_str}
【当前活跃冲突】{conflicts_str}

===== 前情提要 =====
{prev_summary if prev_summary else "这是开头几集"}

===== 本批次大纲 =====
{chr(10).join(beats_text)}

===== 撰写要求 =====
1. **字数**：总共{target_length}字左右（{target_length-200}~{target_length+300}字），我会手动分割成多集
2. **连贯性**：一次性写完，保证剧情连贯流畅，不要有明显的"集"的界限
3. **节奏**：适当分配每集的内容量，不要前紧后松
4. **对话优先**：每句话都要像人话、通顺、清楚
5. **格式**：
   - 场景头：只写「地点 时/夜 内/外」，例如「办公室 日 内」（不要写集数和场景号）
   - 对话：角色名：台词
   - 动作：△ 开头

【⚠️ 称呼要正确】
- 人物之间的称呼要符合关系（夫妻、上下级、朋友）
- 不能乱叫，要前后一致

【⚠️ 禁止】
- 不要写"第X集"、"END"、"1-1"等编号
- 全中文，禁止出现英文字母（对白、旁白、动作一律用简体中文）
- 不要写诗意的环境描写

直接输出剧本，不要加任何说明。"""
    
    screenwriter.log(f"开始生成第{start_ep}-{end_ep}集的完整剧本...")
    
    # 打印完整提示词
    print("\n" + "=" * 80)
    print("【批量生成 - 完整提示词】")
    print("=" * 80)
    print(prompt)
    print("=" * 80 + "\n")
    
    full_script = screenwriter._chat(prompt, temperature=0.8, print_prompt=False)  # 已经手动打印了
    
    # 清理
    from .screenwriter import clean_script
    full_script = clean_script(full_script)
    
    screenwriter.log(f"完整剧本生成完成，共{len(full_script)}字")
    
    return full_script


def smart_split_script(full_script: str, num_episodes: int, target_chars_per_ep: int = 600) -> List[str]:
    """
    严格按600字分割剧本
    
    策略：
    1. 按场景分割
    2. 每集累积到接近600字就截断
    3. 不够600字的话，就返回实际能分出的集数
    4. 多余的内容直接舍弃
    
    Args:
        full_script: 完整剧本文本
        num_episodes: 期望分割成几集（实际可能更少）
        target_chars_per_ep: 每集目标字数（默认600）
    
    Returns:
        分割后的剧本列表
    """
    # 按场景头分割（无编号格式：「地点 日/夜 内/外」或「【地点】日/夜 内/外」）
    # 匹配模式：中文字符 + 空格 + 日/夜 + 空格 + 内/外
    scene_pattern = r'([^△\n]+?\s+(?:日|夜)\s+(?:内|外))'
    
    # 找到所有场景头的位置
    scene_headers = list(re.finditer(scene_pattern, full_script))
    
    if not scene_headers:
        # 如果没有场景头，按段落强行分
        print("⚠️ 未找到场景头，按段落分割")
        paragraphs = [p.strip() for p in full_script.split('\n\n') if p.strip()]
        
        episodes = []
        current_episode = []
        current_length = 0
        
        for para in paragraphs:
            para_len = len(para)
            if current_length + para_len > target_chars_per_ep and current_episode:
                # 达到目标，结束这一集
                episodes.append('\n\n'.join(current_episode))
                current_episode = []
                current_length = 0
                
                if len(episodes) >= num_episodes:
                    break
            
            current_episode.append(para)
            current_length += para_len
        
        # 最后一集
        if current_episode and len(episodes) < num_episodes:
            episodes.append('\n\n'.join(current_episode))
        
        return episodes
    
    # 根据场景头位置分割成场景列表
    scenes = []
    for i in range(len(scene_headers)):
        start = scene_headers[i].start()
        end = scene_headers[i+1].start() if i+1 < len(scene_headers) else len(full_script)
        scene_content = full_script[start:end].strip()
        if scene_content:
            scenes.append(scene_content)
    
    print(f"找到{len(scenes)}个场景")
    
    # 按600字累积分集
    episodes = []
    current_episode = []
    current_length = 0
    
    for scene in scenes:
        scene_len = len(scene)
        
        # 如果加上这个场景会超过目标字数
        if current_length + scene_len > target_chars_per_ep and current_episode:
            # 当前集已经有内容，结束这一集
            episodes.append('\n\n'.join(current_episode))
            current_episode = [scene]
            current_length = scene_len
            
            # 达到预期集数，停止
            if len(episodes) >= num_episodes:
                print(f"已达到{num_episodes}集，停止分割")
                break
        else:
            # 继续累积
            current_episode.append(scene)
            current_length += scene_len
    
    # 处理最后一集（如果还没达到预期集数）
    if current_episode and len(episodes) < num_episodes:
        episodes.append('\n\n'.join(current_episode))
    
    print(f"实际分割成{len(episodes)}集")
    
    return episodes


def add_ending_hooks(episodes: List[str], bible: Bible, start_ep: int) -> List[str]:
    """
    为每集结尾添加钩子
    
    Args:
        episodes: 分割后的剧本列表
        bible: 世界观圣经
        start_ep: 起始集数
    
    Returns:
        添加钩子后的剧本列表
    """
    enhanced = []
    
    for idx, script in enumerate(episodes):
        ep_num = start_ep + idx
        beat = (bible.beat_sheet.get_beat(ep_num) if bible.beat_sheet else None) or {}
        ending_hook = beat.get('ending_hook', '')
        
        # 检查结尾是否已经有类似的钩子
        last_200 = script[-200:] if len(script) > 200 else script
        
        # 如果结尾已经很有悬念，就不加了
        has_suspense_keywords = any(kw in last_200 for kw in [
            '冷笑', '阴狠', '危险', '盯', '你等着', '不会放过', 
            '计划', '陷阱', '秘密', '真相', '震惊', '不可能'
        ])
        
        if not has_suspense_keywords and ending_hook and idx < len(episodes) - 1:
            # 简单添加一个动作或旁白来暗示钩子
            hook_hint = f"\n\n△ {ending_hook[:30]}..."
            script = script + hook_hint
        
        enhanced.append(script)
    
    return enhanced


def update_scene_numbers(episodes: List[str], start_ep: int) -> List[str]:
    """
    为场景头添加编号（集数-场景号格式）
    
    输入格式：「办公室 日 内」
    输出格式：「1-1 办公室 日 内」
    
    Args:
        episodes: 剧本列表
        start_ep: 起始集数
    
    Returns:
        更新后的剧本列表
    """
    updated = []
    
    for idx, script in enumerate(episodes):
        ep_num = start_ep + idx
        scene_num = 1
        
        def add_scene_number(match):
            nonlocal scene_num
            full_header = match.group(0)
            # 添加编号
            result = f"{ep_num}-{scene_num} {full_header}"
            scene_num += 1
            return result
        
        # 匹配无编号的场景头：「地点 日/夜 内/外」
        # 注意：确保不会匹配到已经有编号的（如果有的话）
        pattern = r'^(?!\d+-\d+)([^△\n]+?\s+(?:日|夜)\s+(?:内|外))'
        
        # 逐行处理
        lines = script.split('\n')
        updated_lines = []
        
        for line in lines:
            # 检查这一行是否是场景头
            if re.match(pattern, line.strip()):
                # 添加编号
                updated_line = f"{ep_num}-{scene_num} {line.strip()}"
                scene_num += 1
                updated_lines.append(updated_line)
            else:
                updated_lines.append(line)
        
        updated.append('\n'.join(updated_lines))
    
    return updated
