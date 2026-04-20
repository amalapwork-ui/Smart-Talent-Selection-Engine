"""
Vector store for semantic candidate search.  Python 3.13-safe.

Backend priority (auto-detected at first use):
  1. sentence-transformers + FAISS  — 384-dim neural embeddings, best quality
  2. sentence-transformers (no FAISS) — embeddings stored in numpy, cosine search
  3. sklearn TF-IDF (pure Python)   — fallback when torch / sentence-transformers
                                      is absent; good enough for skill matching

All three share the same public API:
  generate_embedding(text)  → list[float]
  get_faiss_store()         → VectorStore   (works for all backends)
"""

from __future__ import annotations

import os
import json
import logging
import math
from pathlib import Path
from typing import Protocol

import numpy as np

logger = logging.getLogger(__name__)

# Singletons
_embedding_model = None   # sentence-transformers model OR sklearn vectorizer
_faiss_store     = None   # VectorStore instance
_backend: str    = ""     # "sbert" | "sbert_numpy" | "tfidf"

# Dimension constants
_SBERT_DIM  = 384   # all-MiniLM-L6-v2
_TFIDF_DIM  = 512   # fixed hash-trick dimension for TF-IDF fallback


# ═══════════════════════════════════════════════════════════════════════════
#  BACKEND DETECTION
# ═══════════════════════════════════════════════════════════════════════════

def _detect_backend() -> str:
    """
    Return the best available embedding backend.
    Probe order: sentence-transformers → tfidf.
    Result is cached in module-level _backend.
    """
    global _backend
    if _backend:
        return _backend

    try:
        from sentence_transformers import SentenceTransformer  # noqa: F401
        try:
            import faiss  # noqa: F401
            _backend = "sbert"
            logger.info("Embedding backend: sentence-transformers + FAISS")
        except ImportError:
            _backend = "sbert_numpy"
            logger.info("Embedding backend: sentence-transformers (numpy cosine, no FAISS)")
    except ImportError:
        _backend = "tfidf"
        logger.info("Embedding backend: TF-IDF (sklearn fallback — no sentence-transformers)")

    return _backend


# ═══════════════════════════════════════════════════════════════════════════
#  MODEL LOADING
# ═══════════════════════════════════════════════════════════════════════════

class _TFIDFEmbedder:
    """
    Lightweight sklearn TF-IDF embedder.
    Produces fixed-length vectors via HashingVectorizer (no fitting required).
    """

    def __init__(self, n_features: int = _TFIDF_DIM):
        from sklearn.feature_extraction.text import HashingVectorizer
        self._vec = HashingVectorizer(
            analyzer="word",
            ngram_range=(1, 2),
            n_features=n_features,
            norm="l2",
            alternate_sign=False,
        )
        self.dim = n_features

    def encode(self, texts: list[str], normalize_embeddings: bool = True) -> np.ndarray:
        matrix = self._vec.transform(texts)
        arr = np.asarray(matrix.todense(), dtype=np.float32)
        if normalize_embeddings:
            norms = np.linalg.norm(arr, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1.0, norms)
            arr = arr / norms
        return arr


def get_embedding_model():
    """Return the active embedding model (singleton, lazy-loaded)."""
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model

    backend = _detect_backend()

    if backend in ("sbert", "sbert_numpy"):
        try:
            from sentence_transformers import SentenceTransformer
            _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Loaded SentenceTransformer: all-MiniLM-L6-v2")
        except Exception as e:
            logger.warning(f"SentenceTransformer load failed ({e}); falling back to TF-IDF")
            global _backend
            _backend = "tfidf"
            _embedding_model = _TFIDFEmbedder()
    else:
        _embedding_model = _TFIDFEmbedder()

    return _embedding_model


def _embedding_dim() -> int:
    backend = _detect_backend()
    return _SBERT_DIM if backend in ("sbert", "sbert_numpy") else _TFIDF_DIM


# ═══════════════════════════════════════════════════════════════════════════
#  PUBLIC EMBEDDING API
# ═══════════════════════════════════════════════════════════════════════════

def generate_embedding(text: str) -> list[float]:
    """Generate a normalised embedding vector for the given text."""
    model = get_embedding_model()
    vector = model.encode([text], normalize_embeddings=True)[0]
    return vector.tolist()


def profile_to_text(profile: dict) -> str:
    """
    Serialise a structured candidate profile to a single dense text string
    suitable for embedding.
    """
    parts: list[str] = []

    skills = profile.get("skills", [])
    if skills:
        parts.append("Skills: " + ", ".join(skills))

    exp = profile.get("experience_years", {})
    if isinstance(exp, dict):
        years = exp.get("total_years", 0)
        parts.append(f"Experience: {years} years")
        for role in exp.get("roles", [])[:5]:
            if isinstance(role, dict):
                title = role.get("title", "")
                desc  = role.get("description", "")
                if title:
                    parts.append(f"Role: {title}. {desc}")
    elif isinstance(exp, (int, float)):
        parts.append(f"Experience: {exp} years")

    for proj in profile.get("projects", [])[:5]:
        if isinstance(proj, dict):
            name = proj.get("name", "")
            desc = proj.get("description", "")
            tech = ", ".join(proj.get("tech_stack", []))
            if name:
                parts.append(f"Project: {name}. {desc}. Tech: {tech}")

    for edu in profile.get("education", [])[:2]:
        if isinstance(edu, dict):
            degree = edu.get("degree", "")
            inst   = edu.get("institution", "")
            if degree:
                parts.append(f"Education: {degree} {inst}".strip())

    summary = profile.get("summary", "")
    if summary:
        parts.append(summary)

    return " | ".join(parts)


# ═══════════════════════════════════════════════════════════════════════════
#  VECTOR STORE  (FAISS or pure-numpy fallback)
# ═══════════════════════════════════════════════════════════════════════════

class _NumpyVectorStore:
    """
    Pure-numpy in-memory vector store.
    Cosine similarity via dot product on normalised vectors.
    Used when FAISS is not available.
    Persists vectors + id-map as JSON (acceptable for < ~5 000 candidates).
    """

    def __init__(self, index_path: str):
        self.index_path  = Path(index_path)
        self.index_path.mkdir(parents=True, exist_ok=True)
        self.vectors_file = self.index_path / "vectors_numpy.json"

        # candidate_id (int) → embedding list[float]
        self._store: dict[int, list[float]] = {}
        self._load()
        logger.info(f"NumpyVectorStore loaded {len(self._store)} vectors")

    def _load(self):
        if self.vectors_file.exists():
            try:
                with open(self.vectors_file) as f:
                    raw = json.load(f)
                self._store = {int(k): v for k, v in raw.items()}
            except Exception as e:
                logger.warning(f"Could not load numpy vector store: {e}")

    def _save(self):
        try:
            with open(self.vectors_file, "w") as f:
                json.dump({str(k): v for k, v in self._store.items()}, f)
        except Exception as e:
            logger.error(f"Failed to save numpy vector store: {e}")

    def add_candidate(self, candidate_id: int, embedding: list[float]) -> bool:
        self._store[candidate_id] = embedding
        self._save()
        return True

    def remove_candidate(self, candidate_id: int):
        self._store.pop(candidate_id, None)
        self._save()

    def search(self, query_embedding: list[float], k: int = 20) -> list[dict]:
        if not self._store:
            return []
        q   = np.array(query_embedding, dtype=np.float32)
        ids = list(self._store.keys())
        mat = np.array([self._store[i] for i in ids], dtype=np.float32)

        # Dot product of normalised vectors == cosine similarity
        scores = mat @ q
        top_k  = min(k, len(ids))
        top_idx = np.argpartition(scores, -top_k)[-top_k:]
        top_idx = top_idx[np.argsort(scores[top_idx])[::-1]]

        return [
            {"candidate_id": ids[i], "similarity_score": float(scores[i])}
            for i in top_idx
        ]

    def total_vectors(self) -> int:
        return len(self._store)


class FAISSVectorStore:
    """
    FAISS-backed vector store with numpy fallback.
    Automatically degrades to _NumpyVectorStore when faiss-cpu is unavailable.
    """

    def __init__(self, index_path: str):
        self.index_path   = Path(index_path)
        self.index_path.mkdir(parents=True, exist_ok=True)
        self.index_file   = self.index_path / "candidates.index"
        self.mapping_file = self.index_path / "id_mapping.json"
        self.dim          = _embedding_dim()

        self.index     = None
        self.id_map:      dict[int, int] = {}   # faiss_pos → candidate_id
        self.reverse_map: dict[int, int] = {}   # candidate_id → faiss_pos
        self._fallback: _NumpyVectorStore | None = None

        self._load()

    # ── internal ─────────────────────────────────────────────────────────

    def _load(self):
        try:
            import faiss
            if self.index_file.exists():
                self.index = faiss.read_index(str(self.index_file))
                if self.mapping_file.exists():
                    with open(self.mapping_file) as f:
                        raw = json.load(f)
                    self.id_map      = {int(k): v for k, v in raw.get("id_map", {}).items()}
                    self.reverse_map = {v: int(k) for k, v in self.id_map.items()}
                logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors (dim={self.dim})")
            else:
                self._create_new_index()
        except ImportError:
            logger.warning("faiss-cpu not installed — using numpy cosine-similarity store")
            self._fallback = _NumpyVectorStore(str(self.index_path))
        except Exception as e:
            logger.warning(f"FAISS init failed ({e}); using numpy fallback")
            self._fallback = _NumpyVectorStore(str(self.index_path))

    def _create_new_index(self):
        try:
            import faiss
            self.index       = faiss.IndexFlatIP(self.dim)
            self.id_map      = {}
            self.reverse_map = {}
            logger.info(f"Created new FAISS IndexFlatIP (dim={self.dim})")
        except ImportError:
            self._fallback = _NumpyVectorStore(str(self.index_path))

    def _save(self):
        if self.index is None:
            return
        try:
            import faiss
            faiss.write_index(self.index, str(self.index_file))
            with open(self.mapping_file, "w") as f:
                json.dump({"id_map": self.id_map, "reverse_map": self.reverse_map}, f)
        except Exception as e:
            logger.error(f"Failed to save FAISS index: {e}")

    # ── public ────────────────────────────────────────────────────────────

    def add_candidate(self, candidate_id: int, embedding: list[float]) -> bool:
        if self._fallback:
            return self._fallback.add_candidate(candidate_id, embedding)
        try:
            import faiss
            vec = np.array([embedding], dtype=np.float32)
            if candidate_id in self.reverse_map:
                self.remove_candidate(candidate_id)
            pos = self.index.ntotal
            self.index.add(vec)
            self.id_map[pos]            = candidate_id
            self.reverse_map[candidate_id] = pos
            self._save()
            return True
        except Exception as e:
            logger.error(f"FAISS add failed for candidate {candidate_id}: {e}")
            return False

    def remove_candidate(self, candidate_id: int):
        if self._fallback:
            self._fallback.remove_candidate(candidate_id)
            return
        if candidate_id in self.reverse_map:
            del self.reverse_map[candidate_id]
            self.id_map = {p: c for p, c in self.id_map.items() if c != candidate_id}

    def search(self, query_embedding: list[float], k: int = 20) -> list[dict]:
        if self._fallback:
            return self._fallback.search(query_embedding, k)
        if self.index is None or self.index.ntotal == 0:
            return []
        try:
            vec      = np.array([query_embedding], dtype=np.float32)
            actual_k = min(k, self.index.ntotal)
            distances, indices = self.index.search(vec, actual_k)
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx == -1:
                    continue
                cid = self.id_map.get(int(idx))
                if cid is not None:
                    results.append({"candidate_id": cid, "similarity_score": float(dist)})
            return results
        except Exception as e:
            logger.error(f"FAISS search failed: {e}")
            return []

    def total_vectors(self) -> int:
        if self._fallback:
            return self._fallback.total_vectors()
        return self.index.ntotal if self.index else 0

    @property
    def backend(self) -> str:
        return "numpy_cosine" if self._fallback else "faiss"


# ═══════════════════════════════════════════════════════════════════════════
#  SINGLETON ACCESSOR
# ═══════════════════════════════════════════════════════════════════════════

def get_faiss_store() -> FAISSVectorStore:
    """Return the singleton VectorStore (FAISS or numpy-backed)."""
    global _faiss_store
    if _faiss_store is None:
        try:
            from django.conf import settings
            index_path = getattr(settings, "FAISS_INDEX_PATH", "faiss_index")
        except Exception:
            index_path = "faiss_index"
        _faiss_store = FAISSVectorStore(str(index_path))
    return _faiss_store
