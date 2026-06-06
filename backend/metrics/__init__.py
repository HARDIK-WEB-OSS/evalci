# backend/metrics package
from backend.metrics.answer_relevance import AnswerRelevanceMetric
from backend.metrics.faithfulness import FaithfulnessMetric
from backend.metrics.semantic_similarity import SemanticSimilarityMetric

METRIC_REGISTRY: dict[str, type] = {
    "answer_relevance": AnswerRelevanceMetric,
    "faithfulness": FaithfulnessMetric,
    "semantic_similarity": SemanticSimilarityMetric,
}

__all__ = [
    "AnswerRelevanceMetric",
    "FaithfulnessMetric",
    "SemanticSimilarityMetric",
    "METRIC_REGISTRY",
]
