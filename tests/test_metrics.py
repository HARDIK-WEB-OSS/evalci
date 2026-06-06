# tests/test_metrics.py
from __future__ import annotations

import pytest

from backend.metrics.answer_relevance import AnswerRelevanceMetric
from backend.metrics.base import MetricResult
from backend.metrics.faithfulness import FaithfulnessMetric
from backend.metrics.semantic_similarity import SemanticSimilarityMetric


# ── AnswerRelevanceMetric ──────────────────────────────────────────────────

class TestAnswerRelevanceMetric:
    @pytest.mark.asyncio
    async def test_perfect_answer_scores_high(
        self, mock_judge_perfect, sample_query, sample_context, sample_expected, sample_perfect_answer
    ):
        metric = AnswerRelevanceMetric(judge=mock_judge_perfect, threshold=0.70)
        result = await metric.score(
            query=sample_query,
            context=sample_context,
            expected=sample_expected,
            actual=sample_perfect_answer,
        )
        assert isinstance(result, MetricResult)
        assert result.score > 0.90
        assert result.passed is True
        assert result.latency_ms >= 0
        assert result.metric_name == "answer_relevance"

    @pytest.mark.asyncio
    async def test_wrong_answer_scores_low(
        self, mock_judge_poor, sample_query, sample_context, sample_expected, sample_wrong_answer
    ):
        metric = AnswerRelevanceMetric(judge=mock_judge_poor, threshold=0.70)
        result = await metric.score(
            query=sample_query,
            context=sample_context,
            expected=sample_expected,
            actual=sample_wrong_answer,
        )
        assert result.score < 0.30
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_judge_error_returns_zero(
        self, sample_query, sample_context, sample_expected, sample_perfect_answer
    ):
        from unittest.mock import AsyncMock
        from backend.judge import JudgeTimeoutError, OllamaJudge

        judge = AsyncMock(spec=OllamaJudge)
        judge.judge = AsyncMock(side_effect=JudgeTimeoutError("All retries failed"))

        metric = AnswerRelevanceMetric(judge=judge, threshold=0.70)
        result = await metric.score(
            query=sample_query,
            context=sample_context,
            expected=sample_expected,
            actual=sample_perfect_answer,
        )
        assert result.score == 0.0
        assert result.passed is False
        assert "error" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_score_clamped_to_0_1(
        self, sample_query, sample_context, sample_expected, sample_perfect_answer
    ):
        from unittest.mock import AsyncMock
        from backend.judge import OllamaJudge

        judge = AsyncMock(spec=OllamaJudge)
        # Malformed response — score out of range
        judge.judge = AsyncMock(return_value='{"score": 1.5, "reasoning": "Great"}')

        metric = AnswerRelevanceMetric(judge=judge, threshold=0.70)
        result = await metric.score(
            query=sample_query,
            context=sample_context,
            expected=sample_expected,
            actual=sample_perfect_answer,
        )
        assert 0.0 <= result.score <= 1.0

    @pytest.mark.asyncio
    async def test_malformed_json_falls_back_to_regex(
        self, sample_query, sample_context, sample_expected, sample_perfect_answer
    ):
        from unittest.mock import AsyncMock
        from backend.judge import OllamaJudge

        judge = AsyncMock(spec=OllamaJudge)
        # Not JSON, but contains a float
        judge.judge = AsyncMock(return_value="The score is 0.82. This is a good answer.")

        metric = AnswerRelevanceMetric(judge=judge, threshold=0.70)
        result = await metric.score(
            query=sample_query,
            context=sample_context,
            expected=sample_expected,
            actual=sample_perfect_answer,
        )
        assert result.score == pytest.approx(0.82, abs=0.01)


# ── FaithfulnessMetric ─────────────────────────────────────────────────────

class TestFaithfulnessMetric:
    @pytest.mark.asyncio
    async def test_faithful_answer_scores_high(
        self,
        mock_judge_faithfulness_decompose,
        sample_query,
        sample_context,
        sample_expected,
        sample_perfect_answer,
    ):
        metric = FaithfulnessMetric(judge=mock_judge_faithfulness_decompose, threshold=0.75)
        result = await metric.score(
            query=sample_query,
            context=sample_context,
            expected=sample_expected,
            actual=sample_perfect_answer,
        )
        assert result.score > 0.90
        assert result.passed is True
        assert "2/2" in result.reasoning

    @pytest.mark.asyncio
    async def test_hallucinated_answer_scores_low(
        self,
        mock_judge_faithfulness_hallucination,
        sample_query,
        sample_context,
        sample_expected,
        sample_wrong_answer,
    ):
        metric = FaithfulnessMetric(judge=mock_judge_faithfulness_hallucination, threshold=0.75)
        result = await metric.score(
            query=sample_query,
            context=sample_context,
            expected=sample_expected,
            actual=sample_wrong_answer,
        )
        assert result.score < 0.20
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_empty_context_returns_no_claims_score_one(
        self, sample_query, sample_expected, sample_perfect_answer
    ):
        from unittest.mock import AsyncMock
        from backend.judge import OllamaJudge

        judge = AsyncMock(spec=OllamaJudge)
        # No claims to verify
        judge.judge = AsyncMock(return_value="[]")

        metric = FaithfulnessMetric(judge=judge, threshold=0.75)
        result = await metric.score(
            query=sample_query,
            context="",
            expected=sample_expected,
            actual=sample_perfect_answer,
        )
        # No verifiable claims — should return 1.0 (N/A)
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_decomposition_failure_returns_zero(
        self, sample_query, sample_context, sample_expected, sample_perfect_answer
    ):
        from unittest.mock import AsyncMock
        from backend.judge import JudgeTimeoutError, OllamaJudge

        judge = AsyncMock(spec=OllamaJudge)
        judge.judge = AsyncMock(side_effect=JudgeTimeoutError("timeout"))

        metric = FaithfulnessMetric(judge=judge, threshold=0.75)
        result = await metric.score(
            query=sample_query,
            context=sample_context,
            expected=sample_expected,
            actual=sample_perfect_answer,
        )
        assert result.score == 0.0
        assert result.passed is False


# ── SemanticSimilarityMetric ───────────────────────────────────────────────

class TestSemanticSimilarityMetric:
    @pytest.mark.asyncio
    async def test_identical_answers_score_one(self, sample_query, sample_context, sample_expected):
        metric = SemanticSimilarityMetric(threshold=0.65)
        result = await metric.score(
            query=sample_query,
            context=sample_context,
            expected=sample_expected,
            actual=sample_expected,  # same text
        )
        assert result.score > 0.99
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_similar_answers_score_high(
        self, sample_query, sample_context, sample_expected, sample_perfect_answer
    ):
        metric = SemanticSimilarityMetric(threshold=0.65)
        result = await metric.score(
            query=sample_query,
            context=sample_context,
            expected=sample_expected,
            actual=sample_perfect_answer,
        )
        assert result.score > 0.65
        assert result.metric_name == "semantic_similarity"
        assert result.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_completely_different_text_scores_low(
        self, sample_query, sample_context, sample_expected
    ):
        metric = SemanticSimilarityMetric(threshold=0.65)
        result = await metric.score(
            query=sample_query,
            context=sample_context,
            expected=sample_expected,
            actual="Bananas are a tropical fruit high in potassium and vitamin B6.",
        )
        assert result.score < 0.65

    @pytest.mark.asyncio
    async def test_no_judge_dependency(self, sample_query, sample_context, sample_expected):
        """SemanticSimilarityMetric must work without a judge argument."""
        metric = SemanticSimilarityMetric(threshold=0.65)
        # Should not raise even though judge=None
        result = await metric.score(
            query=sample_query,
            context=sample_context,
            expected=sample_expected,
            actual=sample_expected,
        )
        assert isinstance(result, MetricResult)
