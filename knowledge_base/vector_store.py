"""
向量数据库抽象层
─────────────────
提供统一接口，支持在 ChromaDB / Qdrant 之间无缝切换。

用法:
    store = get_vector_store()          # 根据 VECTOR_DB 环境变量自动选择
    store.upsert(ids, embeddings, documents, metadatas)
    results = store.search(query_embedding, top_k=50, filters={...})
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_COLLECTION = "jobs"


def _load_env() -> None:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _env_str(key: str, default: str = "") -> str:
    _load_env()
    value = os.getenv(key)
    return value if value is not None and value != "" else default


def _env_int(key: str, default: int) -> int:
    _load_env()
    try:
        return int(os.getenv(key, str(default)))
    except (TypeError, ValueError):
        return default


# ── Qdrant 优化参数（针对 ~10K 条 1024 维向量场景）──
HNSW_M = _env_int("HNSW_M", 32)
HNSW_EF_CONSTRUCT = _env_int("HNSW_EF_CONSTRUCT", 256)
HNSW_EF_SEARCH = _env_int("HNSW_EF_SEARCH", 128)


# ═══════════════════════════════════════════════════════
#  抽象基类
# ═══════════════════════════════════════════════════════

class VectorStore(ABC):
    """向量数据库统一接口"""

    @abstractmethod
    def upsert(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict[str, Any]],
    ) -> None:
        """批量插入或更新向量数据"""

    @abstractmethod
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 50,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        向量检索，返回结果列表。
        每个元素包含: id, score, document, metadata(含 job_id 等字段)
        """

    @abstractmethod
    def count(self) -> int:
        """返回当前集合中的向量总数"""

    @abstractmethod
    def delete_collection(self) -> None:
        """删除当前集合（用于重建索引）"""

    @abstractmethod
    def collection_exists(self) -> bool:
        """检查集合是否存在"""


# ═══════════════════════════════════════════════════════
#  ChromaDB 实现（保留兼容）
# ═══════════════════════════════════════════════════════

class ChromaVectorStore(VectorStore):

    def __init__(
        self,
        persist_path: str | None = None,
        collection_name: str = DEFAULT_COLLECTION,
    ):
        import chromadb

        self._path = persist_path or str(PROJECT_ROOT / "knowledge_base" / "chroma_db")
        self._collection_name = collection_name
        self._client = chromadb.PersistentClient(path=self._path)
        self._collection = self._client.get_or_create_collection(collection_name)

    def upsert(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict[str, Any]],
    ) -> None:
        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 50,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        where = self._build_where(filters) if filters else None
        kwargs: Dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": min(top_k, self._collection.count()),
            "include": ["metadatas", "distances", "documents"],
        }
        if where:
            kwargs["where"] = where

        res = self._collection.query(**kwargs)
        results: List[Dict[str, Any]] = []
        for meta, dist, doc in zip(
            res["metadatas"][0],
            res["distances"][0],
            res["documents"][0],
        ):
            results.append({
                "id": meta.get("job_id", ""),
                "score": float(dist),
                "document": doc,
                "metadata": meta,
            })
        return results

    def count(self) -> int:
        return self._collection.count()

    def delete_collection(self) -> None:
        try:
            self._client.delete_collection(self._collection_name)
        except Exception:
            pass
        self._collection = self._client.get_or_create_collection(self._collection_name)

    def collection_exists(self) -> bool:
        try:
            names = [c.name for c in self._client.list_collections()]
            return self._collection_name in names
        except Exception:
            return False

    @staticmethod
    def _build_where(filters: Dict[str, Any]) -> Dict[str, Any] | None:
        conditions = []
        for key, value in filters.items():
            if isinstance(value, dict):
                conditions.append({key: value})
            else:
                conditions.append({key: {"$eq": value}})
        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}


# ═══════════════════════════════════════════════════════
#  Qdrant 实现（推荐方案）
# ═══════════════════════════════════════════════════════

class QdrantVectorStore(VectorStore):

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        path: str | None = None,
        collection_name: str = DEFAULT_COLLECTION,
        vector_size: int = 1024,
    ):
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams, HnswConfigDiff

        self._collection_name = collection_name
        self._vector_size = vector_size

        qdrant_mode = _env_str("QDRANT_MODE", "local")

        if qdrant_mode == "server":
            _host = host or _env_str("QDRANT_HOST", "localhost")
            _port = port or _env_int("QDRANT_PORT", 6333)
            self._client = QdrantClient(host=_host, port=_port)
        else:
            _path = path or str(PROJECT_ROOT / "knowledge_base" / "qdrant_db")
            os.makedirs(_path, exist_ok=True)
            self._client = QdrantClient(path=_path)

        if not self._client.collection_exists(collection_name):
            self._client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE,
                    hnsw_config=HnswConfigDiff(
                        m=HNSW_M,
                        ef_construct=HNSW_EF_CONSTRUCT,
                    ),
                ),
            )

    def upsert(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict[str, Any]],
    ) -> None:
        from qdrant_client.models import PointStruct

        points = []
        for i, (point_id, emb, doc, meta) in enumerate(
            zip(ids, embeddings, documents, metadatas)
        ):
            payload = dict(meta)
            payload["document"] = doc
            payload["_str_id"] = point_id
            points.append(PointStruct(
                id=self._stable_hash(point_id),
                vector=emb,
                payload=payload,
            ))

        batch_size = 100
        for start in range(0, len(points), batch_size):
            batch = points[start : start + batch_size]
            self._client.upsert(
                collection_name=self._collection_name,
                points=batch,
            )

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 50,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        from qdrant_client.models import SearchParams

        query_filter = self._build_filter(filters) if filters else None
        response = self._client.query_points(
            collection_name=self._collection_name,
            query=query_embedding,
            limit=top_k,
            query_filter=query_filter,
            search_params=SearchParams(
                hnsw_ef=HNSW_EF_SEARCH,
                exact=False,
            ),
            with_payload=True,
        )

        results: List[Dict[str, Any]] = []
        for point in response.points:
            payload = dict(point.payload) if point.payload else {}
            doc = payload.pop("document", "")
            str_id = payload.pop("_str_id", "")
            results.append({
                "id": str_id or str(point.id),
                "score": 1.0 - point.score,  # cosine similarity → distance
                "document": doc,
                "metadata": payload,
            })
        return results

    def count(self) -> int:
        info = self._client.get_collection(self._collection_name)
        return info.points_count or 0

    def delete_collection(self) -> None:
        if self._client.collection_exists(self._collection_name):
            self._client.delete_collection(self._collection_name)

    def collection_exists(self) -> bool:
        return self._client.collection_exists(self._collection_name)

    @staticmethod
    def _stable_hash(s: str) -> int:
        """将字符串 ID 转为 Qdrant 需要的正整数 ID（确定性哈希）"""
        import hashlib
        return int(hashlib.sha256(s.encode()).hexdigest()[:15], 16)

    @staticmethod
    def _build_filter(filters: Dict[str, Any]):
        from qdrant_client.models import Filter, FieldCondition, MatchValue, Range

        conditions = []
        for key, value in filters.items():
            if isinstance(value, dict):
                range_kwargs = {}
                if "gte" in value:
                    range_kwargs["gte"] = value["gte"]
                if "lte" in value:
                    range_kwargs["lte"] = value["lte"]
                if "gt" in value:
                    range_kwargs["gt"] = value["gt"]
                if "lt" in value:
                    range_kwargs["lt"] = value["lt"]
                if range_kwargs:
                    conditions.append(
                        FieldCondition(key=key, range=Range(**range_kwargs))
                    )
            else:
                conditions.append(
                    FieldCondition(key=key, match=MatchValue(value=value))
                )
        return Filter(must=conditions) if conditions else None


# ═══════════════════════════════════════════════════════
#  工厂函数
# ═══════════════════════════════════════════════════════

_store_instance: VectorStore | None = None


def get_vector_store(
    collection_name: str = DEFAULT_COLLECTION,
    singleton: bool = True,
) -> VectorStore:
    """
    根据环境变量 VECTOR_DB 选择向量数据库后端。
    - "qdrant" (默认): 使用 Qdrant
    - "chroma": 使用 ChromaDB
    """
    global _store_instance
    if singleton and _store_instance is not None:
        return _store_instance

    backend = _env_str("VECTOR_DB", "qdrant").lower()

    if backend == "chroma":
        store = ChromaVectorStore(collection_name=collection_name)
    else:
        store = QdrantVectorStore(collection_name=collection_name)

    if singleton:
        _store_instance = store
    return store


def reset_store_singleton() -> None:
    """重置单例（用于测试或重建索引时）"""
    global _store_instance
    _store_instance = None
