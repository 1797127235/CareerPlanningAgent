# -*- coding: utf-8 -*-
"""Skill embedding cache for semantic skill matching."""
from __future__ import annotations

import json
import logging
import math
from pathlib import Path

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_SKILL_EMB_PATH = _PROJECT_ROOT / "data" / "skill_embeddings.json"


class _SkillEmbedder:
    """Skill embedding cache with file persistence.

    Graph skill embeddings are pre-computed and cached to file.
    User skill embeddings are computed on-the-fly and cached in memory.
    """

    def __init__(self):
        self._cache: dict[str, list[float]] = {}
        self._client = None
        self._loaded = False

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            from backend.config import DASHSCOPE_API_KEY, LLM_BASE_URL
            api_key = DASHSCOPE_API_KEY
            if not api_key or api_key == "sk-placeholder":
                return None
            self._client = OpenAI(base_url=LLM_BASE_URL, api_key=api_key, timeout=10, max_retries=1)
        return self._client

    def load_cache(self):
        """Load pre-computed embeddings from file."""
        if self._loaded:
            return
        self._loaded = True
        if _SKILL_EMB_PATH.exists():
            try:
                data = json.loads(_SKILL_EMB_PATH.read_text(encoding="utf-8"))
                self._cache.update(data)
                logger.info("Loaded %d skill embeddings from cache", len(data))
            except Exception as e:
                logger.warning("Failed to load skill embeddings: %s", e)

    def save_cache(self):
        """Save current cache to file."""
        try:
            _SKILL_EMB_PATH.write_text(
                json.dumps(self._cache, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as e:
            logger.warning("Failed to save skill embeddings: %s", e)

    def _embed_batch(self, texts: list[str]) -> dict[str, list[float]]:
        """Embed a batch of texts (max 10 per DashScope call)."""
        client = self._get_client()
        if not client:
            return {}
        result = {}
        # DashScope limit: 10 per batch
        for i in range(0, len(texts), 10):
            batch = texts[i:i + 10]
            try:
                resp = client.embeddings.create(model="text-embedding-v3", input=batch)
                for text, emb in zip(batch, resp.data):
                    result[text] = emb.embedding
                    self._cache[text] = emb.embedding
            except Exception as e:
                logger.warning("Batch embedding failed: %s", e)
        return result

    def ensure_embedded(self, skills: list[str]) -> None:
        """Ensure all skills have embeddings (batch embed missing ones)."""
        missing = [s for s in skills if s not in self._cache]
        if missing:
            self._embed_batch(missing)

    def best_similarity(self, skill: str, candidates: list[str]) -> float:
        """Find the highest cosine similarity between skill and any candidate."""
        skill_vec = self._cache.get(skill)
        if skill_vec is None:
            return 0.0
        best = 0.0
        for c in candidates:
            c_vec = self._cache.get(c)
            if c_vec is None:
                continue
            dot = sum(a * b for a, b in zip(skill_vec, c_vec))
            norm_a = math.sqrt(sum(a * a for a in skill_vec))
            norm_b = math.sqrt(sum(b * b for b in c_vec))
            if norm_a > 0 and norm_b > 0:
                sim = dot / (norm_a * norm_b)
                if sim > best:
                    best = sim
        return best


_skill_embedder: _SkillEmbedder | None = None


def _get_skill_embedder() -> _SkillEmbedder | None:
    """Get or create the singleton skill embedder."""
    global _skill_embedder
    if _skill_embedder is None:
        _skill_embedder = _SkillEmbedder()
        _skill_embedder.load_cache()
    if _skill_embedder._get_client() is None:
        return None
    return _skill_embedder


