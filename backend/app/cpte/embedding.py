"""
优化1: 语义 Embedding 替代哈希

用 sentence-transformers 生成有语义意义的向量，
"一元二次方程" 和 "二次方程" 距离很近，
"x=3" 和 "x=5" 距离也近（同类型信念）。
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import hashlib


class SemanticEmbedder:
    """语义嵌入器

    优先使用 sentence-transformers，降级到 TF-IDF，最后兜底哈希。
    """

    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        self.model = None
        self.model_name = model_name
        self._cache: Dict[str, np.ndarray] = {}
        self._fallback_mode = False

        self._try_load_model()

    def _try_load_model(self):
        """尝试加载模型"""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
            print(f"✓ 语义模型加载成功: {self.model_name}")
        except Exception as e:
            print(f"⚠ 语义模型加载失败，降级到 TF-IDF: {e}")
            self._fallback_mode = True
            self._tfidf_vocab: Dict[str, int] = {}
            self._tfidf_idf: Optional[np.ndarray] = None

    def encode(self, text: str, dimension: int = 16) -> np.ndarray:
        """将文本编码为 N 维向量

        Args:
            text: 输入文本
            dimension: 目标维度

        Returns:
            N 维向量，值域 [-1, 1]
        """
        # 检查缓存
        cache_key = f"{text}_{dimension}"
        if cache_key in self._cache:
            return self._cache[cache_key].copy()

        if self.model is not None:
            vec = self._encode_with_model(text, dimension)
        elif self._fallback_mode:
            vec = self._encode_with_tfidf(text, dimension)
        else:
            vec = self._encode_with_hash(text, dimension)

        self._cache[cache_key] = vec.copy()
        return vec

    def encode_batch(self, texts: List[str], dimension: int = 16) -> np.ndarray:
        """批量编码"""
        if self.model is not None and len(texts) > 1:
            return self._encode_batch_with_model(texts, dimension)
        return np.array([self.encode(t, dimension) for t in texts])

    def _encode_with_model(self, text: str, dimension: int) -> np.ndarray:
        """用 sentence-transformers 编码"""
        raw_vec = self.model.encode(text, normalize_embeddings=True)

        # 降维到目标维度
        if len(raw_vec) > dimension:
            # PCA 降维（简化版：取前 N 维 + 均值池化）
            vec = self._reduce_dimension(raw_vec, dimension)
        else:
            vec = np.pad(raw_vec, (0, max(0, dimension - len(raw_vec))))

        return np.clip(vec[:dimension], -1, 1)

    def _encode_batch_with_model(self, texts: List[str], dimension: int) -> np.ndarray:
        """批量编码（利用 GPU 加速）"""
        raw_vecs = self.model.encode(texts, normalize_embeddings=True, batch_size=32)
        result = []
        for raw_vec in raw_vecs:
            if len(raw_vec) > dimension:
                vec = self._reduce_dimension(raw_vec, dimension)
            else:
                vec = np.pad(raw_vec, (0, max(0, dimension - len(raw_vec))))
            result.append(np.clip(vec[:dimension], -1, 1))
        return np.array(result)

    def _reduce_dimension(self, vec: np.ndarray, target_dim: int) -> np.ndarray:
        """降维（分块均值池化）"""
        source_dim = len(vec)
        block_size = source_dim // target_dim
        reduced = np.zeros(target_dim)
        for i in range(target_dim):
            start = i * block_size
            end = start + block_size if i < target_dim - 1 else source_dim
            reduced[i] = np.mean(vec[start:end])
        return reduced

    def _encode_with_tfidf(self, text: str, dimension: int) -> np.ndarray:
        """TF-IDF 降级编码"""
        # 字符级 n-gram
        chars = list(text)
        bigrams = [text[i:i+2] for i in range(len(text)-1)]
        tokens = chars + bigrams

        # 更新词汇表
        for t in tokens:
            if t not in self._tfidf_vocab:
                self._tfidf_vocab[t] = len(self._tfidf_vocab)

        # 构建 TF 向量
        vec = np.zeros(min(len(self._tfidf_vocab), 1000))
        for t in tokens:
            idx = self._tfidf_vocab.get(t, 0)
            if idx < len(vec):
                vec[idx] += 1

        # 归一化
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm

        # 降维到目标维度
        if len(vec) > dimension:
            return self._reduce_dimension(vec, dimension)
        return np.pad(vec, (0, dimension - len(vec)))[:dimension]

    def _encode_with_hash(self, text: str, dimension: int) -> np.ndarray:
        """哈希兜底编码（最差质量）"""
        seeds = [hashlib.md5(f"{text}_{i}".encode()).hexdigest() for i in range(dimension)]
        vec = np.array([int(s[:8], 16) / 0xFFFFFFFF * 2 - 1 for s in seeds])
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec

    def similarity(self, text1: str, text2: str) -> float:
        """计算两个文本的语义相似度"""
        vec1 = self.encode(text1)
        vec2 = self.encode(text2)
        dot = np.dot(vec1, vec2)
        norm_product = np.linalg.norm(vec1) * np.linalg.norm(vec2)
        if norm_product < 1e-10:
            return 0.0
        return float(dot / norm_product)

    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()


# 全局单例
_embedder: Optional[SemanticEmbedder] = None


def get_embedder() -> SemanticEmbedder:
    """获取全局嵌入器单例"""
    global _embedder
    if _embedder is None:
        _embedder = SemanticEmbedder()
    return _embedder
