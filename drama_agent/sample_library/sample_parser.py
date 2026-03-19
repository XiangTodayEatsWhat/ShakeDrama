"""
样本剧本解析器 - 将docx剧本转换为结构化数据
"""
import os
import re
import hashlib
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


@dataclass
class ScriptChunk:
    """剧本片段"""
    episode: int                          # 所属集数
    scene: int                            # 场景号
    content: str                          # 内容
    chunk_type: str                       # 类型：dialogue/action/os/scene_header
    characters: List[str] = field(default_factory=list)  # 涉及角色


@dataclass
class ParsedSample:
    """解析后的样本剧本"""
    id: str                               # 唯一标识
    title: str                            # 剧名
    filepath: str                         # 原始文件路径
    raw_text: str                         # 原始文本
    total_episodes: int                   # 总集数
    chunks: List[ScriptChunk] = field(default_factory=list)  # 分块
    format_examples: Dict[str, str] = field(default_factory=dict)  # 格式示例
    style_notes: str = ""                 # 风格特点
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "filepath": self.filepath,
            "total_episodes": self.total_episodes,
            "format_examples": self.format_examples,
            "style_notes": self.style_notes,
            "chunk_count": len(self.chunks)
        }


class SampleParser:
    """样本剧本解析器"""
    
    # 场景头正则：匹配如 "1-1 客厅 日 内" 或 "第1集"
    SCENE_HEADER_PATTERN = re.compile(
        r'^(\d+)-(\d+)\s+(.+?)\s+(日|夜)\s+(内|外)',
        re.MULTILINE
    )
    EPISODE_HEADER_PATTERN = re.compile(
        r'^第(\d+)集',
        re.MULTILINE
    )
    
    # 动作描写
    ACTION_PATTERN = re.compile(r'^△\s*(.+)$', re.MULTILINE)
    
    # 内心独白/旁白
    OS_PATTERN = re.compile(r'^(.+?)（OS）[：:]\s*(.+)$', re.MULTILINE)
    VO_PATTERN = re.compile(r'^(.+?)（VO）[：:]\s*(.+)$', re.MULTILINE)
    
    # 对话：角色名后跟对话内容
    DIALOGUE_PATTERN = re.compile(r'^([^\s△（【]+)\n(.+?)(?=\n[^\s]|\n△|\n【|$)', re.MULTILINE | re.DOTALL)
    
    def __init__(self):
        if not HAS_DOCX:
            print("警告：python-docx未安装，无法解析docx文件。请运行: pip install python-docx")
    
    def read_docx(self, filepath: str) -> str:
        """读取docx文件内容"""
        if not HAS_DOCX:
            raise ImportError("python-docx未安装")
        
        doc = Document(filepath)
        paragraphs = [p.text for p in doc.paragraphs]
        return '\n'.join(paragraphs)
    
    def read_txt(self, filepath: str) -> str:
        """读取txt文件内容"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    
    def read_file(self, filepath: str) -> str:
        """读取文件内容"""
        ext = os.path.splitext(filepath)[1].lower()
        if ext == '.docx':
            return self.read_docx(filepath)
        elif ext == '.txt':
            return self.read_txt(filepath)
        else:
            raise ValueError(f"不支持的文件格式：{ext}")
    
    def extract_episodes(self, text: str) -> List[Dict[str, Any]]:
        """提取分集信息"""
        episodes = []
        
        # 尝试按场景头分割
        scene_matches = list(self.SCENE_HEADER_PATTERN.finditer(text))
        
        if scene_matches:
            current_episode = 0
            for i, match in enumerate(scene_matches):
                ep_num = int(match.group(1))
                scene_num = int(match.group(2))
                location = match.group(3)
                time = match.group(4)
                interior = match.group(5)
                
                # 获取场景内容
                start = match.end()
                end = scene_matches[i + 1].start() if i + 1 < len(scene_matches) else len(text)
                content = text[start:end].strip()
                
                if ep_num != current_episode:
                    current_episode = ep_num
                    episodes.append({
                        "number": ep_num,
                        "scenes": []
                    })
                
                if episodes:
                    episodes[-1]["scenes"].append({
                        "scene_number": scene_num,
                        "location": location,
                        "time": time,
                        "interior": interior,
                        "content": content
                    })
        
        # 如果没有标准场景头，尝试按"第X集"分割
        if not episodes:
            ep_matches = list(self.EPISODE_HEADER_PATTERN.finditer(text))
            for i, match in enumerate(ep_matches):
                ep_num = int(match.group(1))
                start = match.end()
                end = ep_matches[i + 1].start() if i + 1 < len(ep_matches) else len(text)
                content = text[start:end].strip()
                
                episodes.append({
                    "number": ep_num,
                    "content": content
                })
        
        return episodes
    
    def extract_format_examples(self, text: str) -> Dict[str, str]:
        """提取各种格式的示例"""
        examples = {}
        
        # 场景头示例
        scene_match = self.SCENE_HEADER_PATTERN.search(text)
        if scene_match:
            examples["scene_header"] = scene_match.group(0)
        
        # 动作描写示例
        action_matches = self.ACTION_PATTERN.findall(text)
        if action_matches:
            examples["action"] = f"△ {action_matches[0][:100]}"
        
        # 内心独白示例
        os_match = self.OS_PATTERN.search(text)
        if os_match:
            examples["inner_monologue"] = f"{os_match.group(1)}（OS）：{os_match.group(2)[:50]}"
        
        return examples
    
    def analyze_style(self, text: str) -> str:
        """分析写作风格"""
        # 统计特征
        action_count = len(self.ACTION_PATTERN.findall(text))
        os_count = len(self.OS_PATTERN.findall(text))
        
        # 计算对话密度
        lines = text.split('\n')
        dialogue_lines = len([l for l in lines if l.strip() and not l.startswith('△') and not l.startswith('【')])
        
        style_notes = []
        
        if action_count > len(lines) * 0.1:
            style_notes.append("动作描写丰富")
        
        if os_count > 10:
            style_notes.append("大量使用内心独白")
        
        # 检查对话风格
        if '！' in text and text.count('！') > 50:
            style_notes.append("对话情绪激烈")
        
        if '...' in text or '……' in text:
            style_notes.append("有悬念留白")
        
        return '，'.join(style_notes) if style_notes else "标准短剧风格"
    
    def create_chunks(self, text: str, chunk_size: int = 1000) -> List[ScriptChunk]:
        """将剧本分块"""
        chunks = []
        episodes = self.extract_episodes(text)
        
        for ep_data in episodes:
            ep_num = ep_data.get("number", 0)
            
            if "scenes" in ep_data:
                for scene in ep_data["scenes"]:
                    content = scene.get("content", "")
                    # 按chunk_size分割
                    for i in range(0, len(content), chunk_size):
                        chunk_content = content[i:i + chunk_size]
                        chunks.append(ScriptChunk(
                            episode=ep_num,
                            scene=scene.get("scene_number", 0),
                            content=chunk_content,
                            chunk_type="mixed"
                        ))
            else:
                content = ep_data.get("content", "")
                for i in range(0, len(content), chunk_size):
                    chunk_content = content[i:i + chunk_size]
                    chunks.append(ScriptChunk(
                        episode=ep_num,
                        scene=0,
                        content=chunk_content,
                        chunk_type="mixed"
                    ))
        
        return chunks
    
    def parse(self, filepath: str) -> ParsedSample:
        """
        解析剧本文件
        
        Args:
            filepath: 剧本文件路径
        
        Returns:
            ParsedSample对象
        """
        # 读取文件
        text = self.read_file(filepath)
        
        # 生成ID
        sample_id = hashlib.md5(filepath.encode()).hexdigest()[:12]
        
        # 从文件名提取剧名
        filename = os.path.basename(filepath)
        title = os.path.splitext(filename)[0]
        # 清理剧名
        title = re.sub(r'[（(].*?[）)]', '', title)  # 移除括号内容
        title = re.sub(r'全剧本|剧本', '', title)
        title = title.strip()
        
        # 提取分集
        episodes = self.extract_episodes(text)
        total_episodes = len(episodes) if episodes else 1
        
        # 提取格式示例
        format_examples = self.extract_format_examples(text)
        
        # 分析风格
        style_notes = self.analyze_style(text)
        
        # 创建分块
        chunks = self.create_chunks(text)
        
        return ParsedSample(
            id=sample_id,
            title=title,
            filepath=filepath,
            raw_text=text,
            total_episodes=total_episodes,
            chunks=chunks,
            format_examples=format_examples,
            style_notes=style_notes
        )
    
    def get_format_reference(self, sample: ParsedSample, max_length: int = 1200) -> str:
        """
        获取格式参考文本（仅用于格式学习，不用于创意参考）
        控制篇幅，避免挤占主提示。
        """
        reference_parts = []
        
        # 格式示例（精简）
        reference_parts.append("【格式规范示例】")
        for fmt_type, example in sample.format_examples.items():
            reference_parts.append(f"{fmt_type}: {example}")
        
        if sample.style_notes:
            reference_parts.append(f"\n【写作风格】{sample.style_notes[:200]}")
        
        # 只取 1～2 段短片段作为格式参考
        reference_parts.append("\n【剧本片段参考（仅供格式参考）】")
        if sample.chunks:
            first_chunks = [c for c in sample.chunks if c.episode <= 2][:2]
            for chunk in first_chunks:
                reference_parts.append(chunk.content[:350])
        
        result = '\n'.join(reference_parts)
        return result[:max_length]
