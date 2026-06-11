"""
星伴·启明 — ChromaDB 知识库客户端

使用 ChromaDB 存储初中数学考点知识，
支持考点检索、相似度匹配等。
"""

import uuid
from typing import Optional
import chromadb
from chromadb.config import Settings


COLLECTION_NAME = "xingban_knowledge_points"


class KnowledgeBase:
    """ChromaDB 知识库客户端"""

    def __init__(self, persist_directory: str = "./chroma_data"):
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection: Optional[chromadb.Collection] = None

    @property
    def collection(self) -> chromadb.Collection:
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def add_knowledge_point(
        self,
        name: str,
        description: str,
        error_types: list[str],
        strategies: list[str],
        grade: str = "初中",
        subject: str = "数学",
        metadata: dict = None,
    ) -> str:
        """
        添加一个知识点。

        Args:
            name: 考点名称 (e.g. "一元二次方程求根公式")
            description: 考点描述
            error_types: 常见错误类型列表
            strategies: 对应的追问策略名称列表
            grade: 年级
            subject: 学科
            metadata: 其他自定义元数据

        Returns:
            知识点 ID
        """
        kp_id = str(uuid.uuid4())
        doc_text = f"{name}：{description}"
        meta = {
            "name": name,
            "grade": grade,
            "subject": subject,
            "error_types": ",".join(error_types),
            "strategies": ",".join(strategies),
        }
        if metadata:
            meta.update(metadata)

        self.collection.add(
            documents=[doc_text],
            metadatas=[meta],
            ids=[kp_id],
        )
        return kp_id

    def search(self, query: str, n_results: int = 5) -> list[dict]:
        """
        按查询文本搜索最匹配的知识点。

        Args:
            query: 查询文本（题目/学生回答）
            n_results: 返回结果数

        Returns:
            [{id, document, metadata, distance}, ...]
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
        )
        items = []
        for i in range(len(results["ids"][0])):
            items.append({
                "id": results["ids"][0][i],
                "document": results["documents"][0][i] if results.get("documents") else "",
                "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                "distance": results["distances"][0][i] if results.get("distances") else 0,
            })
        return items

    def count(self) -> int:
        return self.collection.count()

    def delete_all(self):
        """清空集合（用于测试或重新灌数据）"""
        self.client.delete_collection(COLLECTION_NAME)
        self._collection = None
