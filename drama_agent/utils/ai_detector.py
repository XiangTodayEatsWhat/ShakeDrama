"""
AI文本检测器 - 集成多个专业AI检测API
"""
import requests
import json
from typing import Dict, Any, Optional, List
from enum import Enum
import os


class DetectorProvider(Enum):
    """AI检测服务提供商"""
    GPTZERO = "gptzero"
    ORIGINALITY = "originality"
    COPYLEAKS = "copyleaks"
    SAPLING = "sapling"
    WRITER = "writer"
    ZEROGPT = "zerogpt"


class AIDetectionResult:
    """AI检测结果"""
    
    def __init__(
        self,
        is_ai_generated: bool,
        confidence: float,
        ai_probability: float,
        provider: str,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        self.is_ai_generated = is_ai_generated
        self.confidence = confidence  # 0-1, 置信度
        self.ai_probability = ai_probability  # 0-1, AI生成的概率
        self.provider = provider
        self.details = details or {}
        self.error = error
    
    def __str__(self):
        if self.error:
            return f"[{self.provider}] 检测失败: {self.error}"
        
        status = "AI生成" if self.is_ai_generated else "人类创作"
        return (f"[{self.provider}] {status} "
                f"(AI概率: {self.ai_probability*100:.1f}%, "
                f"置信度: {self.confidence*100:.1f}%)")
    
    def to_dict(self):
        return {
            "is_ai_generated": self.is_ai_generated,
            "confidence": self.confidence,
            "ai_probability": self.ai_probability,
            "provider": self.provider,
            "details": self.details,
            "error": self.error
        }


class AIDetector:
    """
    AI文本检测器 - 支持多个专业检测API
    
    使用方法：
    1. 在环境变量或config中配置API密钥
    2. 调用detect()方法检测文本
    
    支持的API：
    - GPTZero: 专业的AI检测服务，准确率高
    - Originality.ai: 支持GPT-3/4检测
    - Copyleaks: 企业级检测服务
    - Sapling: 免费API，准确率中等
    - Writer.com: 免费检测API
    - ZeroGPT: 免费在线检测
    """
    
    def __init__(self):
        # 从环境变量读取API密钥
        self.api_keys = {
            DetectorProvider.GPTZERO: os.getenv("GPTZERO_API_KEY"),
            DetectorProvider.ORIGINALITY: os.getenv("ORIGINALITY_API_KEY"),
            DetectorProvider.COPYLEAKS: os.getenv("COPYLEAKS_API_KEY"),
            DetectorProvider.SAPLING: os.getenv("SAPLING_API_KEY"),
            DetectorProvider.WRITER: os.getenv("WRITER_API_KEY"),
        }
    
    def detect(
        self,
        text: str,
        providers: Optional[List[DetectorProvider]] = None,
        timeout: int = 30
    ) -> List[AIDetectionResult]:
        """
        检测文本是否为AI生成
        
        Args:
            text: 要检测的文本
            providers: 使用的检测服务列表，None表示使用所有可用服务
            timeout: 超时时间（秒）
        
        Returns:
            检测结果列表
        """
        if providers is None:
            # 使用所有有API密钥的服务
            providers = [p for p in DetectorProvider if self.api_keys.get(p)]
            
            # 如果没有配置任何API，使用免费服务
            if not providers:
                providers = [DetectorProvider.ZEROGPT, DetectorProvider.SAPLING]
        
        results = []
        for provider in providers:
            try:
                if provider == DetectorProvider.GPTZERO:
                    result = self._detect_gptzero(text, timeout)
                elif provider == DetectorProvider.ORIGINALITY:
                    result = self._detect_originality(text, timeout)
                elif provider == DetectorProvider.COPYLEAKS:
                    result = self._detect_copyleaks(text, timeout)
                elif provider == DetectorProvider.SAPLING:
                    result = self._detect_sapling(text, timeout)
                elif provider == DetectorProvider.WRITER:
                    result = self._detect_writer(text, timeout)
                elif provider == DetectorProvider.ZEROGPT:
                    result = self._detect_zerogpt(text, timeout)
                else:
                    continue
                
                results.append(result)
            except Exception as e:
                results.append(AIDetectionResult(
                    is_ai_generated=False,
                    confidence=0,
                    ai_probability=0,
                    provider=provider.value,
                    error=str(e)
                ))
        
        return results
    
    def _detect_gptzero(self, text: str, timeout: int) -> AIDetectionResult:
        """
        使用GPTZero API检测
        文档: https://gptzero.me/docs
        """
        api_key = self.api_keys[DetectorProvider.GPTZERO]
        if not api_key:
            raise ValueError("GPTZero API密钥未配置")
        
        url = "https://api.gptzero.me/v2/predict/text"
        headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "document": text
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        data = response.json()
        
        # GPTZero返回的字段
        completely_generated_prob = data.get("documents", [{}])[0].get("completely_generated_prob", 0)
        average_generated_prob = data.get("documents", [{}])[0].get("average_generated_prob", 0)
        
        # 使用平均概率作为判断依据
        ai_prob = average_generated_prob
        is_ai = ai_prob > 0.5
        
        return AIDetectionResult(
            is_ai_generated=is_ai,
            confidence=abs(ai_prob - 0.5) * 2,  # 转换为置信度
            ai_probability=ai_prob,
            provider="gptzero",
            details={
                "completely_generated_prob": completely_generated_prob,
                "average_generated_prob": average_generated_prob
            }
        )
    
    def _detect_originality(self, text: str, timeout: int) -> AIDetectionResult:
        """
        使用Originality.ai API检测
        文档: https://originality.ai/api-documentation
        """
        api_key = self.api_keys[DetectorProvider.ORIGINALITY]
        if not api_key:
            raise ValueError("Originality.ai API密钥未配置")
        
        url = "https://api.originality.ai/api/v1/scan/ai"
        headers = {
            "X-OAI-API-KEY": api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "content": text,
            "aiModelVersion": "1"  # 或 "2" for GPT-4 detection
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        data = response.json()
        
        ai_score = data.get("score", {}).get("ai", 0)
        original_score = data.get("score", {}).get("original", 0)
        
        is_ai = ai_score > original_score
        
        return AIDetectionResult(
            is_ai_generated=is_ai,
            confidence=abs(ai_score - original_score),
            ai_probability=ai_score,
            provider="originality",
            details=data.get("score", {})
        )
    
    def _detect_copyleaks(self, text: str, timeout: int) -> AIDetectionResult:
        """
        使用Copyleaks API检测
        文档: https://api.copyleaks.com/documentation
        """
        api_key = self.api_keys[DetectorProvider.COPYLEAKS]
        if not api_key:
            raise ValueError("Copyleaks API密钥未配置")
        
        # Copyleaks需要先登录获取token
        # 这里简化处理，实际使用需要完整的OAuth流程
        raise NotImplementedError("Copyleaks需要完整的OAuth认证流程，请参考官方文档")
    
    def _detect_sapling(self, text: str, timeout: int) -> AIDetectionResult:
        """
        使用Sapling AI Detector API
        文档: https://sapling.ai/ai-content-detector
        """
        api_key = self.api_keys.get(DetectorProvider.SAPLING, "demo")  # 可以使用demo key
        
        url = "https://api.sapling.ai/api/v1/aidetect"
        payload = {
            "key": api_key,
            "text": text
        }
        
        response = requests.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        
        data = response.json()
        
        # Sapling返回的score: 0-1，越高越可能是AI
        ai_score = data.get("score", 0)
        is_ai = ai_score > 0.5
        
        return AIDetectionResult(
            is_ai_generated=is_ai,
            confidence=abs(ai_score - 0.5) * 2,
            ai_probability=ai_score,
            provider="sapling",
            details={
                "score": ai_score,
                "sentence_scores": data.get("sentence_scores", [])
            }
        )
    
    def _detect_writer(self, text: str, timeout: int) -> AIDetectionResult:
        """
        使用Writer.com AI Content Detector
        文档: https://writer.com/ai-content-detector/
        """
        # Writer提供免费的web API
        url = "https://enterprise-api.writer.com/content/organization/undefined/team/undefined/ai-content-detector"
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        payload = {
            "input": text
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        data = response.json()
        
        # Writer返回分数 0-100
        score = data.get("score", 0) / 100.0
        is_ai = score > 0.5
        
        return AIDetectionResult(
            is_ai_generated=is_ai,
            confidence=abs(score - 0.5) * 2,
            ai_probability=score,
            provider="writer",
            details=data
        )
    
    def _detect_zerogpt(self, text: str, timeout: int) -> AIDetectionResult:
        """
        使用ZeroGPT API
        免费在线检测服务
        """
        # ZeroGPT的API端点（可能需要更新）
        url = "https://api.zerogpt.com/api/detect/detectText"
        
        payload = {
            "input_text": text
        }
        
        try:
            response = requests.post(url, json=payload, timeout=timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # ZeroGPT返回AI百分比
            ai_percentage = data.get("data", {}).get("fakePercentage", 0) / 100.0
            is_ai = ai_percentage > 0.5
            
            return AIDetectionResult(
                is_ai_generated=is_ai,
                confidence=abs(ai_percentage - 0.5) * 2,
                ai_probability=ai_percentage,
                provider="zerogpt",
                details=data.get("data", {})
            )
        except Exception as e:
            # ZeroGPT可能不稳定，提供降级方案
            raise Exception(f"ZeroGPT检测失败: {str(e)}")
    
    def get_consensus(self, results: List[AIDetectionResult]) -> AIDetectionResult:
        """
        综合多个检测结果，得出共识
        
        Args:
            results: 多个检测结果
        
        Returns:
            综合结果
        """
        if not results:
            return AIDetectionResult(
                is_ai_generated=False,
                confidence=0,
                ai_probability=0,
                provider="consensus",
                error="没有可用的检测结果"
            )
        
        # 过滤掉失败的结果
        valid_results = [r for r in results if r.error is None]
        
        if not valid_results:
            return AIDetectionResult(
                is_ai_generated=False,
                confidence=0,
                ai_probability=0,
                provider="consensus",
                error="所有检测服务都失败了"
            )
        
        # 计算加权平均
        total_prob = 0
        total_weight = 0
        
        for result in valid_results:
            weight = result.confidence  # 用置信度作为权重
            total_prob += result.ai_probability * weight
            total_weight += weight
        
        avg_prob = total_prob / total_weight if total_weight > 0 else 0
        
        # 计算标准差（衡量结果一致性）
        variance = sum((r.ai_probability - avg_prob) ** 2 for r in valid_results) / len(valid_results)
        std_dev = variance ** 0.5
        
        # 一致性越高，置信度越高
        consensus_confidence = 1 - min(std_dev * 2, 1)
        
        return AIDetectionResult(
            is_ai_generated=avg_prob > 0.5,
            confidence=consensus_confidence,
            ai_probability=avg_prob,
            provider="consensus",
            details={
                "num_detectors": len(valid_results),
                "individual_results": [r.to_dict() for r in valid_results],
                "std_deviation": std_dev
            }
        )


def detect_text(text: str, providers: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    便捷函数：检测文本是否为AI生成
    
    Args:
        text: 要检测的文本
        providers: 使用的服务列表，如 ["gptzero", "sapling"]
    
    Returns:
        检测结果字典
    """
    detector = AIDetector()
    
    # 转换provider名称为枚举
    provider_enums = None
    if providers:
        provider_enums = []
        for p in providers:
            try:
                provider_enums.append(DetectorProvider(p.lower()))
            except ValueError:
                pass
    
    results = detector.detect(text, provider_enums)
    consensus = detector.get_consensus(results)
    
    return {
        "consensus": consensus.to_dict(),
        "individual_results": [r.to_dict() for r in results]
    }


# CLI测试入口
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python ai_detector.py '要检测的文本'")
        print("\n或者设置环境变量后运行:")
        print("  export GPTZERO_API_KEY=your_key")
        print("  export SAPLING_API_KEY=your_key")
        print("  python ai_detector.py '要检测的文本'")
        sys.exit(1)
    
    text = sys.argv[1]
    print(f"正在检测文本（{len(text)}字符）...\n")
    
    detector = AIDetector()
    results = detector.detect(text)
    
    print("=" * 60)
    print("检测结果:")
    print("=" * 60)
    
    for result in results:
        print(result)
    
    print("\n" + "=" * 60)
    print("综合判断:")
    print("=" * 60)
    
    consensus = detector.get_consensus(results)
    print(consensus)
    
    if consensus.details:
        print(f"\n基于 {consensus.details.get('num_detectors', 0)} 个检测器")
        print(f"结果一致性: {(1 - consensus.details.get('std_deviation', 1)) * 100:.1f}%")
