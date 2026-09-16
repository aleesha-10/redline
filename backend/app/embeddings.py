"""
Semantic engine: embeds an input clause and finds its nearest neighbors in
the pre-built CUAD clause index (see backend/scripts/build_index.py).

The index is built offline so the API's hot path never needs network access
or on-the-fly model downloads -- this keeps p95 latency low and makes
failure modes explicit (missing index => clear startup error, not a silent
fallback).
"""
import json
import os
from functools import lru_cache

import numpy as np

from .config import settings

_EMBEDDINGS_PATH = os.path.join(settings.INDEX_DIR, "embeddings.npy")
_METADATA_PATH = os.path.join(settings.INDEX_DIR, "metadata.json")


class IndexNotBuiltError(RuntimeError):
    """Raised when the CUAD index hasn't been built yet."""


class SemanticEngine:
    def __init__(self):
        self._model = None
        self._embeddings: np.ndarray | None = None
        self._metadata: list[dict] | None = None

    def _load_model(self):
        if self._model is None:
            # Imported lazily so `pytest` / API startup doesn't pay the
            # torch import cost unless semantic scoring is actually used.
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(settings.SIMILARITY_MODEL)
        return self._model

    def _load_index(self):
        if self._embeddings is None or self._metadata is None:
            if not (os.path.exists(_EMBEDDINGS_PATH) and os.path.exists(_METADATA_PATH)):
                raise IndexNotBuiltError(
                    "CUAD index not found. Run backend/scripts/download_cuad.py "
                    "and backend/scripts/build_index.py first."
                )
            self._embeddings = np.load(_EMBEDDINGS_PATH)
            with open(_METADATA_PATH, "r") as f:
                self._metadata = json.load(f)
        return self._embeddings, self._metadata

    def score(self, clause: str, top_k: int = 3) -> tuple[str | None, float, list[str]]:
        """
        Returns (matched_category, similarity[0-1], nearest_example_snippets).
        Raises IndexNotBuiltError if the index isn't available -- callers
        must propagate this as an explicit error, never silently skip it.
        """
        model = self._load_model()
        embeddings, metadata = self._load_index()

        query_vec = model.encode([clause], normalize_embeddings=True)[0]
        corpus = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        sims = corpus @ query_vec

        top_idx = np.argsort(sims)[::-1][:top_k]
        best_idx = top_idx[0]
        best_category = metadata[best_idx]["category"]
        best_similarity = float(sims[best_idx])
        examples = [metadata[i]["snippet"] for i in top_idx]

        return best_category, best_similarity, examples


@lru_cache
def get_semantic_engine() -> SemanticEngine:
    return SemanticEngine()
