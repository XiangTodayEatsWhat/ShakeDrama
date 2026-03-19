"""
策划前必选的「红果/短剧爆款」趋势搜索，用于注入到梗概生成提示中
从红果短剧官网抓取真实爆款数据，分析题材、设定、标签等深层特征
支持离线样本库：抓取的爆款数据会保存到本地，作为离线参考
"""
import urllib.request
import urllib.parse
import json
import time
import re
import os
from typing import Optional, Dict, List, Tuple
from collections import Counter
from pathlib import Path
from datetime import datetime

from .llm_client import LLMClient


def _is_complete(d: Dict) -> bool:
    """已有完整信息：简介 + 角色（roles 可为空列表）"""
    return bool(d.get('description')) and 'roles' in d


def search_short_drama_trends(timeout: int = 15, max_retries: int = 3, debug: bool = True, 
                             fetch_details: bool = True) -> str:
    """
    爆款短剧流程：
    1. 先抓爆款列表
    2. 看哪些没存或存了但缺东西（缺简介/角色）
    3. 只对这些抓详情页并更新
    4. 用全部完整爆款做趋势总结，供后续灵感用
    """
    samples_data = _try_load_from_samples()
    existing_by_id = {d.get('series_id'): d for d in (samples_data or []) if d.get('series_id')}
    if samples_data:
        print(f"📦 离线已有 {len(samples_data)} 部")
    
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            print(f"\n{'='*60}")
            print(f"🔍 第 {attempt}/{max_retries} 次抓取爆款列表...")
            print(f"{'='*60}")
            
            url = "https://novelquickapp.com/category?time=2&sort_type=1"
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                }
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                html = resp.read().decode('utf-8')
            
            dramas = _parse_drama_list(html)
            if not dramas or len(dramas) < 10:
                last_error = f"列表页只解析到 {len(dramas)} 部（需要≥10）"
                continue
            if debug:
                print(f"  爆款列表共 {len(dramas)} 部")
            
            # 没存下来的 或 存了但缺简介/角色 的，需要抓详情
            to_fetch = [
                d for d in dramas
                if d['series_id'] not in existing_by_id
                or not _is_complete(existing_by_id.get(d['series_id'], {}))
            ]
            
            if to_fetch and fetch_details:
                print(f"  其中 {len(to_fetch)} 部需补全（未存或缺简介/角色），正在抓详情...")
                new_details = _fetch_drama_details(to_fetch, timeout, debug)
                _save_to_samples([d for d in new_details if d.get('description')], debug)
                # 更新本地缓存：刚抓到的写入 existing_by_id，供后面合并用
                for d in new_details:
                    if d.get('description'):
                        existing_by_id[d['series_id']] = d
            elif to_fetch and not fetch_details:
                print(f"  其中 {len(to_fetch)} 部缺完整信息（未抓详情）")
            
            # 合并：按爆款顺序，只保留信息完整的
            complete_by_id = {sid: d for sid, d in existing_by_id.items() if _is_complete(d)}
            result = [complete_by_id[d['series_id']] for d in dramas if d['series_id'] in complete_by_id]
            
            if len(result) >= 10:
                trend_analysis = _analyze_trends(result)
                _try_save_to_cache(trend_analysis)
                print(f"\n✅ 共 {len(result)} 部完整爆款，已生成趋势总结")
                print(f"{'='*60}\n")
                return trend_analysis
            
            last_error = f"完整爆款仅 {len(result)} 部（需要≥10）"
        
        except urllib.error.HTTPError as e:
            last_error = f"HTTP {e.code}: {e.reason}"
            print(f"\n❌ {last_error}")
        except urllib.error.URLError as e:
            last_error = f"网络错误: {e.reason}"
            print(f"\n❌ {last_error}")
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            print(f"\n❌ {last_error}")
            if debug:
                import traceback
                traceback.print_exc()
        
        if attempt < max_retries:
            print(f"⏳ {attempt * 2} 秒后重试...")
            time.sleep(attempt * 2)
    
    # 列表抓取全部失败时，用离线里信息完整的做总结
    print(f"\n{'='*60}")
    print(f"⚠️ 爆款列表抓取失败，尝试用离线样本...")
    print(f"{'='*60}")
    
    complete_samples = [d for d in (samples_data or []) if _is_complete(d)]
    if len(complete_samples) >= 10:
        print(f"✅ 使用离线完整样本 {len(complete_samples)} 部")
        return _analyze_trends(complete_samples)
    
    n_complete = len(complete_samples)
    error_details = f"""
红果短剧爆款数据获取失败（已尝试{max_retries}次网络抓取）

最后错误: {last_error}

离线样本库: {'无' if not samples_data else f'共{len(samples_data)}部，其中完整{n_complete}部（需要≥10部完整）'}

可能原因：
1. 网络连接问题（无法访问 novelquickapp.com）
2. 网站HTML结构已变更（解析失败）
3. 被网站防爬虫机制拦截
4. 请求超时（当前超时设置: {timeout}秒）
5. 离线样本库未初始化

解决方案：
1. 检查网络连接
2. 联系管理员更新代码（网站结构可能已变更）
3. 或等待网络恢复后重试（首次成功后会建立离线样本库）
    """.strip()
    
    raise RuntimeError(error_details)


def _parse_drama_list(html: str) -> List[Dict]:
    """解析HTML，提取短剧列表信息（包括series_id）"""
    dramas = []
    seen_titles = set()  # 去重
    
    # 新的HTML结构：
    # <a href="/detail?series_id=123456">
    #   <p class="...episode...">全XX集</p>
    #   <p class="...title...">剧名</p>
    #   <div class="...tags..."><span>标签1</span>...
    # </a>
    
    # 先找到所有带series_id的链接块
    link_pattern = r'<a href="/detail\?series_id=(\d+)"[^>]*>(.*?)</a>'
    link_matches = re.finditer(link_pattern, html, re.DOTALL)
    
    for link_match in list(link_matches)[:100]:  # 最多处理前100部
        series_id = link_match.group(1)
        link_content = link_match.group(2)
        
        # 在链接内容中提取集数
        episode_match = re.search(r'全(\d+)集', link_content)
        if not episode_match:
            continue
        episodes = episode_match.group(1)
        
        # 提取标题
        title_pattern = r'<p[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</p>'
        title_match = re.search(title_pattern, link_content)
        if not title_match:
            continue
        
        title = title_match.group(1).strip()
        
        # 过滤掉太短的剧名或重复的剧名
        if len(title) < 2 or title in seen_titles:
            continue
        seen_titles.add(title)
        
        # 提取标签
        tag_pattern = r'<span[^>]*class="[^"]*tag-text[^"]*"[^>]*>([^<]+)</span>'
        tag_matches = re.findall(tag_pattern, link_content)
        
        # 清理和验证标签
        tags = []
        for tag_text in tag_matches[:10]:  # 每部剧最多10个标签
            tag_text = tag_text.strip()
            if tag_text and len(tag_text) <= 20:  # 标签长度合理
                tags.append(tag_text)
        
        # 至少要有1个标签才算有效
        if title and tags:
            dramas.append({
                'title': title,
                'episodes': episodes,
                'tags': tags,
                'raw_tags': '、'.join(tags),
                'series_id': series_id  # 添加series_id
            })
    
    return dramas




def _generate_trend_insight_with_llm(fixed_data_text: str, stats: Dict) -> str:
    """
    用 AI 根据爬取数据生成趋势洞察，重点是人设、剧情、爆点、钩子；
    标签组合仅作参考，不写制作规格特征。
    """
    try:
        client = LLMClient()
        system_prompt = """你是一位短剧行业的数据分析专家。请根据下方「红果短剧爆款」的爬取数据（含简介、角色、标签等），用简洁、有条理的中文写一段趋势分析。

重点必须放在（按重要性）：
1. 人设与角色设定：爆款里常见的人物类型、身份设定、关系结构。
2. 剧情与叙事：常见剧情走向、矛盾设计、节奏特点。
3. 爆点与爽点：高频出现的情绪爆点、反转、打脸、逆袭等设计。
4. 钩子与留白：开头/结尾如何留钩子、悬念怎么设、如何促追看。

标签组合可顺带提及作为参考，不必单独成节。不要写制作规格（集数、角色数等），不要重复罗列原始数据，重在从案例中归纳可复用的创作规律，篇幅约 200–400 字。"""
        user_content = f"""【爬取数据】

{fixed_data_text}

---
参考（可选）：常见标签组合 {stats.get('top_tag_combos', '') or '（见上方数据）'}

请基于以上爆款案例的简介与角色信息，重点分析：人设/剧情/爆点/钩子 等方面的共性规律与可借鉴点（可自拟小标题，不必拘泥固定模板）。"""
        out = client.chat_with_system(
            system_prompt,
            user_content,
            temperature=0.3,
            max_tokens=800,
        )
        return (out or "").strip()
    except Exception:
        return "（本次 AI 分析暂不可用，请以上方爬取数据为准）"


def _analyze_trends(dramas: List[Dict]) -> str:
    """
    分析爆款短剧趋势：前半为爬取固定信息（标签 TOP30、典型案例），
    后半由 AI 生成洞察，重点是人设、剧情、爆点、钩子；标签组合仅作参考，不写制作规格。
    """
    # 统计高频标签
    all_tags = []
    for drama in dramas:
        all_tags.extend(drama.get('tags', []))
    tag_counter = Counter(all_tags)
    top_30_tags = tag_counter.most_common(30)

    # 统计集数分布
    episodes_list = []
    for d in dramas:
        ep = d.get('episodes', '') or d.get('total_episodes', '')
        if ep and str(ep).isdigit():
            episodes_list.append(int(ep))
    if episodes_list:
        avg_episodes = sum(episodes_list) // len(episodes_list)
        min_episodes = min(episodes_list)
        max_episodes = max(episodes_list)
    else:
        avg_episodes = 80
        min_episodes = 60
        max_episodes = 100

    # 统计角色数量、每部标签数
    role_counts = [len(d.get('roles', [])) for d in dramas if d.get('roles')]
    avg_roles = sum(role_counts) // len(role_counts) if role_counts else 0
    tags_per_drama = [len(d.get('tags', [])) for d in dramas if d.get('tags')]
    avg_tags_per_drama = sum(tags_per_drama) // len(tags_per_drama) if tags_per_drama else 0

    # 常见标签组合（前5），供 AI 参考
    top_combos_text = _analyze_tag_combinations(dramas[:30])
    top_tag_combos = top_combos_text.replace("  • ", "").replace("（", " ").strip() if top_combos_text else ""

    # 固定信息：仅保留爬取到的真实数据（一、二）
    fixed_data_text = f"""【红果短剧爆款趋势】基于最近 30 天热门短剧真实数据（共 {len(dramas)} 部）

一、爆款高频标签 TOP30（按出现频率排序）：
{_format_tags_with_count([t for t, c in top_30_tags], tag_counter)}

二、典型爆款案例（TOP10，含完整信息）：
{_format_drama_examples(dramas[:10])}"""

    stats = {
        "drama_count": len(dramas),
        "avg_episodes": avg_episodes,
        "min_episodes": min_episodes,
        "max_episodes": max_episodes,
        "avg_roles": avg_roles,
        "avg_tags_per_drama": avg_tags_per_drama,
        "top_tag_combos": top_tag_combos[:300] if top_tag_combos else "",
    }

    # 后半部分由 AI 根据固定数据 + 统计摘要生成，不锁死模板
    ai_insight = _generate_trend_insight_with_llm(fixed_data_text, stats)

    trend_text = f"""{fixed_data_text}

{ai_insight}

注：一、二为红果短剧官网实时抓取数据；上方分析由 AI 基于该数据生成。"""
    return trend_text.strip()


def _format_tags_with_count(tags: List[str], counter: Counter) -> str:
    """格式化标签及其出现次数"""
    if not tags:
        return "（数据不足）"
    
    lines = []
    for tag in tags:
        count = counter[tag]
        lines.append(f"  • {tag}（{count}部短剧）")
    
    return "\n".join(lines)


def _format_drama_examples(dramas: List[Dict]) -> str:
    """格式化短剧案例（包含剧情简介、演员表）"""
    lines = []
    for i, drama in enumerate(dramas, 1):
        tags_str = "、".join(drama['tags'][:5])
        line = f"  {i}. 《{drama['title']}》{drama.get('episodes', '?')}集 - {tags_str}"
        
        # 如果有剧情简介，也展示出来
        if 'description' in drama and drama['description']:
            desc = drama['description']
            # 限制简介长度
            if len(desc) > 100:
                desc = desc[:100] + "..."
            line += f"\n     简介：{desc}"
        
        # 如果有角色表，展示前几位
        if 'roles' in drama and drama['roles']:
            roles = drama['roles']
            roles_str = "、".join(roles[:5])
            if len(roles) > 5:
                roles_str += f"等{len(roles)}个角色"
            line += f"\n     角色：{roles_str}"
        
        lines.append(line)
    
    return "\n".join(lines)


def _analyze_tag_combinations(dramas: List[Dict]) -> str:
    """
    分析标签组合模式（动态分析，不使用固定规则）
    找出最常见的标签组合
    """
    # 统计2-3个标签的组合
    combinations = []
    for drama in dramas:
        tags = drama['tags']
        # 统计两两组合
        for i in range(len(tags)):
            for j in range(i+1, min(i+3, len(tags))):  # 最多看前3个标签的组合
                combo = tuple(sorted([tags[i], tags[j]]))
                combinations.append(combo)
    
    combo_counter = Counter(combinations)
    top_combos = combo_counter.most_common(5)
    
    if not top_combos:
        return "  • 数据不足，无法分析组合模式"
    
    lines = []
    for combo, count in top_combos:
        combo_str = " + ".join(combo)
        lines.append(f"  • {combo_str}（{count}次）")
    
    return "\n".join(lines)


def _try_load_from_cache() -> Optional[str]:
    """尝试从本地缓存加载爆款趋势数据"""
    try:
        # 获取缓存文件路径
        current_dir = Path(__file__).parent.parent
        cache_dir = current_dir / "data"
        
        # 支持两种缓存：HTML源文件 或 解析后的趋势文本
        html_cache = cache_dir / "trend_cache.html"
        text_cache = cache_dir / "trend_cache.txt"
        
        # 优先使用文本缓存（已解析）
        if text_cache.exists():
            mtime = text_cache.stat().st_mtime
            age_days = (time.time() - mtime) / 86400
            
            # 7天内的缓存才有效
            if age_days <= 7:
                with open(text_cache, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                if content and len(content) > 100:
                    return content
        
        # 尝试HTML缓存（需要解析）
        if html_cache.exists():
            mtime = html_cache.stat().st_mtime
            age_days = (time.time() - mtime) / 86400
            
            # 7天内的缓存才有效
            if age_days <= 7:
                with open(html_cache, 'r', encoding='utf-8') as f:
                    html = f.read()
                
                dramas = _parse_drama_list(html)
                if len(dramas) >= 10:
                    trend_analysis = _analyze_trends(dramas)
                    # 保存为文本缓存，下次直接使用
                    _try_save_to_cache(trend_analysis)
                    return trend_analysis
        
        return None
    
    except Exception as e:
        print(f"⚠️ 缓存加载失败: {e}")
        return None


def _try_save_to_cache(content: str) -> None:
    """保存趋势分析结果到本地缓存"""
    try:
        # 获取缓存文件路径
        current_dir = Path(__file__).parent.parent
        cache_dir = current_dir / "data"
        cache_dir.mkdir(exist_ok=True)
        
        text_cache = cache_dir / "trend_cache.txt"
        
        with open(text_cache, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ 已保存趋势数据到缓存: {text_cache}")
    
    except Exception as e:
        print(f"⚠️ 缓存保存失败: {e}")


def _get_samples_dir() -> Path:
    """获取样本库目录路径"""
    current_dir = Path(__file__).parent.parent
    samples_dir = current_dir / "data" / "trending_dramas"
    samples_dir.mkdir(parents=True, exist_ok=True)
    return samples_dir


def _fetch_drama_details(dramas: List[Dict], timeout: int, debug: bool) -> List[Dict]:
    """
    抓取每个短剧的详情页，补充完整信息（剧情简介、演员表、完整标签等）
    
    Args:
        dramas: 短剧基本信息列表（必须包含series_id）
        timeout: 请求超时时间
        debug: 是否输出调试信息
    
    Returns:
        包含完整详情信息的短剧列表
    """
    enriched_dramas = []
    
    for i, drama in enumerate(dramas, 1):
        try:
            # 检查是否有series_id
            if 'series_id' not in drama:
                if debug:
                    print(f"  {i}/{len(dramas)}. 《{drama['title']}》- ❌ 缺少series_id，跳过")
                continue
            
            # 构建详情页URL
            detail_url = f"https://novelquickapp.com/detail?series_id={drama['series_id']}"
            
            # 抓取详情页
            req = urllib.request.Request(
                detail_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                }
            )
            
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                detail_html = resp.read().decode('utf-8')
            
            # 1. 提取剧情简介
            desc_match = re.search(r'基本信息</div><div[^>]*class="[^"]*desc[^"]*"[^>]*>([^<]+)</div>', detail_html)
            if desc_match:
                drama['description'] = desc_match.group(1).strip()
            else:
                meta_desc = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]+)"', detail_html)
                if meta_desc:
                    drama['description'] = meta_desc.group(1).strip()
            
            # 2. 提取角色名（不存演员名）
            roles = []
            role_blocks = re.finditer(
                r'<div[^>]*class="[^"]*nickname[^"]*"[^>]*>([^<]+)</div>'
                r'[^<]*<div[^>]*class="[^"]*fakename[^"]*"[^>]*>饰\s*([^<]+)</div>',
                detail_html
            )
            for match in role_blocks:
                role_name = match.group(2).strip()
                if role_name and role_name not in roles:
                    roles.append(role_name)
            drama['roles'] = roles
            
            # 3. 从详情页补充标签
            # 找到标题位置
            title_pos = detail_html.find('<h1')
            if title_pos != -1:
                # 标题后2000字符内的标签
                tag_area = detail_html[title_pos:title_pos+2000]
                # 提取tag-text类的span
                detail_tags = re.findall(r'<span[^>]*class="[^"]*tag-text[^"]*"[^>]*>([^<]+)</span>', tag_area)
                # 只保留前面的标签（通常是当前剧的标签），去重并合并
                current_tags = []
                for tag in detail_tags[:10]:  # 只取前10个，避免获取到推荐剧的标签
                    tag = tag.strip()
                    if tag and len(tag) <= 15 and tag not in current_tags:
                        current_tags.append(tag)
                
                # 合并列表页和详情页的标签，去重
                all_tags = drama.get('tags', [])
                for tag in current_tags:
                    if tag not in all_tags:
                        all_tags.append(tag)
                drama['tags'] = all_tags
                drama['raw_tags'] = '、'.join(all_tags)
            
            # 4. 提取剧集数（验证）
            episode_matches = re.findall(r'第(\d+)集', detail_html)
            if episode_matches:
                episodes_list = sorted(set(int(e) for e in episode_matches))
                drama['total_episodes'] = len(episodes_list)
            
            if drama.get('description'):
                enriched_dramas.append(drama)
                if debug and i <= 5:
                    print(f"  {i}. 《{drama['title']}》 简介{len(drama['description'])}字 角色{len(drama.get('roles', []))}个")
            
            # 避免请求过快（重要！）
            time.sleep(1.0)  # 每个请求间隔1秒
        
        except Exception as e:
            if debug:
                print(f"  {i}/{len(dramas)}. ⚠️ 《{drama.get('title', '未知')}》详情抓取失败: {e}")
            time.sleep(0.5)
    
    return enriched_dramas


def _save_to_samples(dramas: List[Dict], debug: bool = False) -> None:
    """
    保存爆款短剧到离线样本库
    
    每个短剧保存为一个JSON文件，文件名为剧名的安全版本
    包含完整信息：标题、简介、演员表、标签、集数等
    """
    try:
        samples_dir = _get_samples_dir()
        
        # 保存每个短剧
        saved_count = 0
        for drama in dramas:
            # 生成安全的文件名
            safe_title = re.sub(r'[^\w\s-]', '', drama['title'])
            safe_title = re.sub(r'[-\s]+', '_', safe_title)
            # 限制文件名长度
            if len(safe_title) > 50:
                safe_title = safe_title[:50]
            filename = f"{safe_title}.json"
            filepath = samples_dir / filename
            
            # 构建完整的数据结构
            drama_data = {
                'title': drama['title'],
                'series_id': drama.get('series_id', ''),
                'episodes': drama.get('episodes', ''),
                'total_episodes': drama.get('total_episodes', None),
                'description': drama.get('description', ''),
                'roles': drama.get('roles', []),
                'tags': drama.get('tags', []),
                'raw_tags': drama.get('raw_tags', ''),
                'last_updated': datetime.now().isoformat(),
                'source': 'novelquickapp.com'
            }
            
            # 保存
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(drama_data, f, ensure_ascii=False, indent=2)
            
            saved_count += 1
        
        print(f"💾 已保存 {saved_count} 部到 {samples_dir}")
        
        index_file = samples_dir / "_index.json"
        index_data = {
            'total_count': len(dramas),
            'last_updated': datetime.now().isoformat(),
            'dramas': [{'title': d['title'], 'episodes': d.get('episodes'), 'tags': d.get('tags', [])[:5]} for d in dramas]
        }
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
    
    except Exception as e:
        print(f"⚠️ 样本库保存失败: {e}")
        if debug:
            import traceback
            traceback.print_exc()


def _try_load_from_samples() -> Optional[List[Dict]]:
    """
    从离线样本库加载爆款短剧数据
    
    Returns:
        短剧列表，如果加载失败返回None
    """
    try:
        samples_dir = _get_samples_dir()
        
        # 读取所有JSON文件
        dramas = []
        for json_file in samples_dir.glob("*.json"):
            # 跳过索引文件
            if json_file.name == "_index.json":
                continue
            
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    drama = json.load(f)
                    dramas.append(drama)
            except Exception as e:
                print(f"⚠️ 读取样本文件 {json_file.name} 失败: {e}")
                continue
        
        if dramas:
            # 按更新时间排序（最新的在前）
            dramas.sort(key=lambda x: x.get('last_updated', ''), reverse=True)
            return dramas
        
        return None
    
    except Exception as e:
        print(f"⚠️ 样本库加载失败: {e}")
        return None
