# backend/metrics/semantic_similarity.py
from __future__ import annotations

import logging
import time
from functools import lru_cache
from typing import Optional

import numpy as np

from backend.metrics.base import BaseMetric, MetricResult

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_model():
    """Load the sentence-transformer model once and cache it."""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Loaded sentence-transformer: all-MiniLM-L6-v2")
        return model
    except ImportError as exc:
        raise RuntimeError(
            "sentence-transformers is required for SemanticSimilarityMetric. "
            "Install it with: pip install sentence-transformers"
        ) from exc


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two 1-D vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class SemanticSimilarityMetric(BaseMetric):
    name = "semantic_similarity"
    description = (
        "Measures semantic similarity between the actual and expected answer "
        "using cosine similarity on all-MiniLM-L6-v2 embeddings. "
        "Deterministic — does not use the Ollama judge."
    )

    def __init__(self, threshold: float = 0.65, judge=None) -> None:
        # judge parameter accepted for API consistency but not used
        super().__init__(threshold=threshold)
        self._model = None

    def _get_model(self):
        if self._model is None:
            self._model = _load_model()
        return self._model

    async def score(
        self,
        query: str,
        context: str,
        expected: str,
        actual: str,
    ) -> MetricResult:
        start = time.perf_counter()

        try:
            model = self._get_model()
            # Encode both strings; returns numpy arrays
            embeddings = model.encode([expected, actual], normalize_embeddings=True)
            expected_emb: np.ndarray = embeddings[0]
            actual_emb: np.ndarray = embeddings[1]

            similarity = _cosine_similarity(expected_emb, actual_emb)
            # Clamp to [0, 1] — cosine similarity on normalized vectors is in [-1, 1]
            similarity = max(0.0, min(1.0, similarity))

            reasoning = (
                f"Cosine similarity between expected and actual answer embeddings: "
                f"{similarity:.4f}. Threshold: {self.threshold:.2f}."
            )
            return self._make_result(similarity, reasoning, start)

        except Exception as exc:
            logger.error("SemanticSimilarityMetric error: %s", exc)
            return self._make_result(
                0.0,
                f"Embedding error: {exc}",
                start,
            )
