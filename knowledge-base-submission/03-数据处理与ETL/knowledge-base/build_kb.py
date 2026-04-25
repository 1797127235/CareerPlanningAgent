"""
构建向量知识库
─────────────
支持 Qdrant（默认）和 ChromaDB 两种后端，通过 VECTOR_DB 环境变量切换。

用法:
    python -m knowledge_base.build_kb                    # 使用默认数据源
    python -m knowledge_base.build_kb --source data/jobs.json --reset
    python -m knowledge_base.build_kb --backend qdrant   # 指定后端
    python -m knowledge_base.build_kb --migrate           # 从 ChromaDB 迁移到 Qdrant
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List

from openai import OpenAI

from agent.nodes.utils import get_env_int, get_env_str, load_env
from knowledge_base.vector_store import (
    VectorStore,
    ChromaVectorStore,
    QdrantVectorStore,
    get_vector_store,
    reset_store_singleton,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
COLLECTION_NAME = "jobs"

DEFAULT_SOURCES = [
    PROJECT_ROOT / "data" / "jobs.json",
    PROJECT_ROOT / "data" / "jobs.jsonl",
    PROJECT_ROOT / "data" / "jobs.csv",
    PROJECT_ROOT / "artifacts" / "job_type_profiles.json",
]

load_env()
BAILIAN_BASE_URL = get_env_str("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
EMBEDDING_MODEL = get_env_str("EMBEDDING_MODEL", "text-embedding-v4")
API_TIMEOUT_SECONDS = get_env_int("API_TIMEOUT_SECONDS", 30)
KB_CHUNK_SIZE = get_env_int("KB_CHUNK_SIZE", 900)
KB_CHUNK_OVERLAP = get_env_int("KB_CHUNK_OVERLAP", 120)
KB_BATCH_SIZE = get_env_int("KB_BATCH_SIZE", 32)


def _get_client() -> OpenAI:
    api_key = os.environ.get("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY is not set. Please configure it in .env")
    return OpenAI(api_key=api_key, base_url=BAILIAN_BASE_URL, timeout=API_TIMEOUT_SECONDS)


def _pick(record: Dict[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        value = record.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return default


# ═══════════════════════════════════════════════════════
#  数据加载
# ═══════════════════════════════════════════════════════

def _read_json(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ["items", "data", "records", "jobs"]:
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return [data]
    return []


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                if isinstance(item, dict):
                    records.append(item)
            except json.JSONDecodeError:
                continue
    return records


def _read_csv(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(dict(row))
    return records


def _load_records(paths: Iterable[Path]) -> List[Dict[str, Any]]:
    all_records: List[Dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            continue
        suffix = path.suffix.lower()
        try:
            if suffix == ".json":
                records = _read_json(path)
            elif suffix in {".jsonl", ".jl"}:
                records = _read_jsonl(path)
            elif suffix == ".csv":
                records = _read_csv(path)
            else:
                continue
            print(f"[build_kb] loaded {len(records)} records from {path}")
            all_records.extend(records)
        except Exception as exc:
            print(f"[build_kb] skip {path}: {exc}")
    return all_records


# ═══════════════════════════════════════════════════════
#  数据规范化 & 文档构建
# ═══════════════════════════════════════════════════════

def _normalize_job(record: Dict[str, Any], idx: int) -> Dict[str, Any]:
    job_id = _pick(record, "job_id", "岗位编码", "职位ID", default=f"job_{idx}")
    job_title = _pick(record, "job_title", "job_type_name", "岗位名称", "职位名称")
    company = _pick(record, "company_name", "company", "公司名称", "企业名称")
    location = _pick(record, "location", "city", "工作地点", "城市", "地址")
    salary = _pick(record, "salary_range", "salary", "薪资范围")
    industry = _pick(record, "industry", "所属行业")

    description = _pick(
        record, "description", "document", "job_description", "岗位描述", "岗位职责",
    )
    requirements = _pick(
        record, "requirements", "requirement", "job_requirements", "任职要求",
    )

    skills = record.get("skills", [])
    if isinstance(skills, list):
        skills_text = ", ".join(str(skill).strip() for skill in skills if str(skill).strip())
    else:
        skills_text = str(skills).strip() if skills is not None else ""

    return {
        "job_id": job_id,
        "job_title": job_title,
        "company_name": company,
        "location": location,
        "salary_range": salary,
        "industry": industry,
        "description": description,
        "requirements": requirements,
        "skills": skills_text,
        "raw": record,
    }


def _build_document(job: Dict[str, Any]) -> str:
    lines = [
        f"Job Title: {job.get('job_title', '')}",
        f"Company: {job.get('company_name', '')}",
        f"Location: {job.get('location', '')}",
        f"Salary: {job.get('salary_range', '')}",
    ]
    if job.get("description"):
        lines.append(f"Description: {job['description']}")
    if job.get("requirements"):
        lines.append(f"Requirements: {job['requirements']}")
    if job.get("skills"):
        lines.append(f"Skills: {job['skills']}")
    return "\n".join(line for line in lines if line.strip())


def _split_text(text: str, chunk_size: int = KB_CHUNK_SIZE, overlap: int = KB_CHUNK_OVERLAP) -> List[str]:
    content = (text or "").strip()
    if not content:
        return []
    if len(content) <= chunk_size:
        return [content]

    chunks: List[str] = []
    start = 0
    while start < len(content):
        end = min(start + chunk_size, len(content))
        chunk = content[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(content):
            break
        start = max(0, end - overlap)
    return chunks


def _embed_batch(client: OpenAI, texts: List[str]) -> List[List[float]]:
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
        encoding_format="float",
    )
    return [item.embedding for item in response.data]


# ═══════════════════════════════════════════════════════
#  构建知识库
# ═══════════════════════════════════════════════════════

def build_kb(
    source_paths: List[Path] | None = None,
    reset: bool = False,
    backend: str | None = None,
) -> None:
    """
    构建向量知识库。

    参数:
        source_paths: 数据源文件路径列表
        reset: 是否删除现有集合后重建
        backend: 指定后端 ("qdrant" / "chroma")，None 时使用环境变量 VECTOR_DB
    """
    paths = source_paths or [path for path in DEFAULT_SOURCES]
    records = _load_records(paths)
    if not records:
        print("[build_kb] no source records found")
        return

    jobs = [_normalize_job(record, idx) for idx, record in enumerate(records, start=1)]
    jobs = [job for job in jobs if job.get("job_id") and job.get("job_title")]

    documents: List[str] = []
    metadatas: List[Dict[str, Any]] = []
    ids: List[str] = []

    for job in jobs:
        doc = _build_document(job)
        chunks = _split_text(doc)
        for index, chunk in enumerate(chunks):
            ids.append(f"{job['job_id']}__chunk{index}")
            documents.append(chunk)
            metadatas.append({
                "job_id": job["job_id"],
                "job_title": job.get("job_title", ""),
                "company_name": job.get("company_name", ""),
                "location": job.get("location", ""),
                "salary_range": job.get("salary_range", ""),
                "industry": job.get("industry", ""),
            })

    if not documents:
        print("[build_kb] no documents generated")
        return

    if backend:
        os.environ["VECTOR_DB"] = backend
    reset_store_singleton()
    store = get_vector_store(collection_name=COLLECTION_NAME, singleton=False)

    if reset:
        store.delete_collection()
        print(f"[build_kb] deleted existing collection: {COLLECTION_NAME}")
        reset_store_singleton()
        store = get_vector_store(collection_name=COLLECTION_NAME, singleton=False)

    client = _get_client()
    backend_name = type(store).__name__

    for start in range(0, len(documents), KB_BATCH_SIZE):
        end = min(start + KB_BATCH_SIZE, len(documents))
        batch_docs = documents[start:end]
        batch_meta = metadatas[start:end]
        batch_ids = ids[start:end]

        embeddings = _embed_batch(client, batch_docs)
        store.upsert(
            ids=batch_ids,
            embeddings=embeddings,
            documents=batch_docs,
            metadatas=batch_meta,
        )
        print(f"[build_kb] ({backend_name}) upserted {end}/{len(documents)} chunks")

    print(
        f"[build_kb] done: backend={backend_name} jobs={len(jobs)} "
        f"chunks={len(documents)} collection_count={store.count()}"
    )


# ═══════════════════════════════════════════════════════
#  ChromaDB → Qdrant 迁移
# ═══════════════════════════════════════════════════════

def migrate_chroma_to_qdrant() -> None:
    """
    从现有 ChromaDB 读取全量数据，写入 Qdrant。
    无需重新调用 Embedding API，直接迁移已有向量。
    """
    print("[migrate] 开始从 ChromaDB 迁移到 Qdrant ...")

    chroma_store = ChromaVectorStore(collection_name=COLLECTION_NAME)
    total = chroma_store.count()
    if total == 0:
        print("[migrate] ChromaDB 中无数据，跳过迁移")
        return

    print(f"[migrate] ChromaDB 中共有 {total} 条记录")

    import chromadb
    chroma_path = str(PROJECT_ROOT / "knowledge_base" / "chroma_db")
    chroma_client = chromadb.PersistentClient(path=chroma_path)
    coll = chroma_client.get_collection(COLLECTION_NAME)

    all_data = coll.get(include=["embeddings", "metadatas", "documents"])
    all_ids = all_data["ids"]
    all_embeddings = all_data["embeddings"]
    all_documents = all_data["documents"]
    all_metadatas = all_data["metadatas"]

    qdrant_store = QdrantVectorStore(collection_name=COLLECTION_NAME)
    if qdrant_store.collection_exists():
        qdrant_store.delete_collection()
        qdrant_store = QdrantVectorStore(collection_name=COLLECTION_NAME)

    batch_size = 100
    for start in range(0, len(all_ids), batch_size):
        end = min(start + batch_size, len(all_ids))
        qdrant_store.upsert(
            ids=all_ids[start:end],
            embeddings=all_embeddings[start:end],
            documents=all_documents[start:end],
            metadatas=all_metadatas[start:end],
        )
        print(f"[migrate] 已迁移 {end}/{len(all_ids)} 条")

    print(f"[migrate] 迁移完成！Qdrant 共 {qdrant_store.count()} 条记录")


# ═══════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build vector knowledge base for job retrieval")
    parser.add_argument(
        "--source", action="append", default=[],
        help="Input file path (json/jsonl/csv). Can be provided multiple times.",
    )
    parser.add_argument("--reset", action="store_true", help="Delete and recreate collection before upsert")
    parser.add_argument(
        "--backend", choices=["qdrant", "chroma"], default=None,
        help="Vector store backend (default: env VECTOR_DB or qdrant)",
    )
    parser.add_argument(
        "--migrate", action="store_true",
        help="Migrate existing ChromaDB data to Qdrant (no re-embedding needed)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    if args.migrate:
        migrate_chroma_to_qdrant()
    else:
        custom_sources = [Path(path) for path in args.source] if args.source else None
        build_kb(custom_sources, reset=args.reset, backend=args.backend)
