"""
样本管理器 - 管理样本剧本的导入、存储、检索
"""
import os
import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict

from .sample_parser import SampleParser, ParsedSample
from ..config import get_config


@dataclass
class SampleMetadata:
    """样本元数据"""
    id: str
    title: str
    filepath: str
    genre: List[str]
    target_audience: str
    total_episodes: int
    style_notes: str
    format_examples: Dict[str, str]
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "SampleMetadata":
        return cls(**data)


class SampleManager:
    """
    样本管理器
    
    管理样本剧本的导入、存储和检索。
    注意：样本主要用于格式和风格参考，不用于创意参考。
    """
    
    def __init__(self):
        self.config = get_config()
        self.parser = SampleParser()
        self.samples: Dict[str, ParsedSample] = {}
        self.metadata: Dict[str, SampleMetadata] = {}
        
        # 确保目录存在
        os.makedirs(self.samples_dir, exist_ok=True)
        
        # 加载已有样本
        self._load_metadata()
    
    @property
    def samples_dir(self) -> str:
        return self.config.sample_library.samples_dir
    
    @property
    def metadata_file(self) -> str:
        return os.path.join(self.samples_dir, "metadata.json")
    
    def _load_metadata(self):
        """加载元数据"""
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for sample_id, meta_dict in data.items():
                    self.metadata[sample_id] = SampleMetadata.from_dict(meta_dict)
    
    def _save_metadata(self):
        """保存元数据"""
        data = {
            sample_id: meta.to_dict()
            for sample_id, meta in self.metadata.items()
        }
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def import_sample(
        self,
        filepath: str,
        genre: Optional[List[str]] = None,
        target_audience: str = "女频"
    ) -> str:
        """
        导入样本剧本
        
        Args:
            filepath: 剧本文件路径
            genre: 类型标签
            target_audience: 目标受众
        
        Returns:
            样本ID
        """
        print(f"正在导入样本：{filepath}")
        
        # 解析剧本
        sample = self.parser.parse(filepath)
        
        # 存储解析结果
        self.samples[sample.id] = sample
        
        # 创建元数据
        metadata = SampleMetadata(
            id=sample.id,
            title=sample.title,
            filepath=filepath,
            genre=genre or [],
            target_audience=target_audience,
            total_episodes=sample.total_episodes,
            style_notes=sample.style_notes,
            format_examples=sample.format_examples
        )
        self.metadata[sample.id] = metadata
        
        # 保存元数据
        self._save_metadata()
        
        print(f"  导入成功：ID={sample.id}, 标题=《{sample.title}》, 集数={sample.total_episodes}")
        return sample.id
    
    def get_sample(self, sample_id: str) -> Optional[ParsedSample]:
        """获取样本"""
        # 如果已加载，直接返回
        if sample_id in self.samples:
            return self.samples[sample_id]
        
        # 尝试从元数据重新解析
        if sample_id in self.metadata:
            meta = self.metadata[sample_id]
            if os.path.exists(meta.filepath):
                sample = self.parser.parse(meta.filepath)
                self.samples[sample_id] = sample
                return sample
        
        return None
    
    def get_metadata(self, sample_id: str) -> Optional[SampleMetadata]:
        """获取样本元数据"""
        return self.metadata.get(sample_id)
    
    def list_samples(self) -> List[SampleMetadata]:
        """列出所有样本"""
        return list(self.metadata.values())
    
    def delete_sample(self, sample_id: str) -> bool:
        """删除样本"""
        if sample_id in self.samples:
            del self.samples[sample_id]
        
        if sample_id in self.metadata:
            del self.metadata[sample_id]
            self._save_metadata()
            return True
        
        return False
    
    def get_format_reference(
        self,
        sample_ids: Optional[List[str]] = None,
        max_length: int = 2000
    ) -> str:
        """
        获取格式参考文本
        
        Args:
            sample_ids: 要参考的样本ID列表，None表示使用所有样本
            max_length: 最大长度
        
        Returns:
            格式参考文本（仅包含格式规范，不包含创意内容）
        """
        if sample_ids is None:
            sample_ids = list(self.metadata.keys())
        
        if not sample_ids:
            return ""
        
        references = []
        per_sample_length = max_length // len(sample_ids)
        
        for sample_id in sample_ids:
            sample = self.get_sample(sample_id)
            if sample:
                ref = self.parser.get_format_reference(sample, per_sample_length)
                references.append(f"=== 《{sample.title}》格式参考 ===\n{ref}")
        
        return '\n\n'.join(references)[:max_length]
    
    def search_by_genre(self, genre: str) -> List[SampleMetadata]:
        """按类型搜索样本"""
        return [
            meta for meta in self.metadata.values()
            if genre in meta.genre
        ]
    
    def search_by_audience(self, audience: str) -> List[SampleMetadata]:
        """按受众搜索样本"""
        return [
            meta for meta in self.metadata.values()
            if meta.target_audience == audience
        ]
    
    def scan_and_import_all(
        self,
        default_genre: Optional[List[str]] = None,
        default_audience: str = "女频",
        recursive: bool = True
    ) -> List[str]:
        """
        自动扫描samples_dir目录下的所有文档并导入
        
        Args:
            default_genre: 默认类型标签（如果无法从文件名推断）
            default_audience: 默认目标受众
            recursive: 是否递归扫描子目录
        
        Returns:
            成功导入的样本ID列表
        """
        print(f"正在扫描目录：{self.samples_dir}")
        
        # 支持的扩展名
        supported_exts = {'.docx', '.txt'}
        
        # 收集所有文件
        files_to_import = []
        if recursive:
            for root, dirs, files in os.walk(self.samples_dir):
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in supported_exts:
                        filepath = os.path.join(root, file)
                        # 跳过metadata.json
                        if file != "metadata.json":
                            files_to_import.append(filepath)
        else:
            for file in os.listdir(self.samples_dir):
                filepath = os.path.join(self.samples_dir, file)
                if os.path.isfile(filepath):
                    ext = os.path.splitext(file)[1].lower()
                    if ext in supported_exts and file != "metadata.json":
                        files_to_import.append(filepath)
        
        if not files_to_import:
            print("未找到可导入的文件")
            return []
        
        print(f"找到 {len(files_to_import)} 个文件，开始导入...")
        
        imported_ids = []
        skipped_ids = []
        
        for filepath in files_to_import:
            # 检查是否已导入（通过文件路径判断）
            already_imported = False
            for meta in self.metadata.values():
                if os.path.abspath(meta.filepath) == os.path.abspath(filepath):
                    skipped_ids.append(meta.id)
                    already_imported = True
                    break
            
            if already_imported:
                continue
            
            try:
                # 尝试从文件名推断类型
                filename = os.path.basename(filepath)
                genre = self._infer_genre_from_filename(filename) or default_genre
                
                sample_id = self.import_sample(
                    filepath,
                    genre=genre,
                    target_audience=default_audience
                )
                imported_ids.append(sample_id)
            except Exception as e:
                print(f"  导入失败：{filepath} - {e}")
        
        print(f"\n导入完成：成功 {len(imported_ids)} 个，跳过 {len(skipped_ids)} 个（已存在）")
        return imported_ids
    
    def _infer_genre_from_filename(self, filename: str) -> Optional[List[str]]:
        """
        从文件名推断类型标签
        
        Args:
            filename: 文件名
        
        Returns:
            推断的类型列表
        """
        genre_keywords = {
            "重生": ["重生", "穿越"],
            "豪门": ["豪门", "总裁", "霸总"],
            "古装": ["古装", "古代", "宫廷", "皇后", "帝后"],
            "现代": ["现代", "都市"],
            "校园": ["校园", "学生", "青春"],
            "修仙": ["修仙", "修真", "仙侠"],
            "悬疑": ["悬疑", "罪", "救赎"],
            "甜宠": ["甜宠", "恋爱", "老公", "闪婚"],
        }
        
        inferred = []
        filename_lower = filename.lower()
        
        for genre, keywords in genre_keywords.items():
            if any(kw in filename_lower for kw in keywords):
                inferred.append(genre)
        
        return inferred if inferred else None