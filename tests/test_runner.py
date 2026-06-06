# tests/test_runner.py
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from backend.metrics.base import MetricResult
from backend.runner import EvalRunner, EvalSample, EvalRunResult, RunMetadata


def _make_metric_result(score: float = 0.85, passed: bool = True) -> MetricResult:
    return MetricResult(
        score=score,
        passed=passed,
        reasoning="Mocked result",
        latency_ms=50,
        metric_name="answer_relevance",
    )


@pytest.fixture
def sample_dataset() -> list[EvalSample]:
    return [
        EvalSample(
            query="What is the default timeout?",
            context="The default timeout is 30 seconds.",
            expected_answer="The default timeout is 30 seconds.",
        ),
        EvalSample(
            query="How do I authenticate?",
            context="Use Bearer token authentication.",
            expected_answer="Use Bearer token authentication.",
        ),
    ]


@pytest.fixture
def sample_prompt() -> str:
    return "Answer the question based on context.\nContext: {context}\nQuestion: {query}\nAnswer:"


@pytest.fixture
def sample_metadata() -> RunMetadata:
    return RunMetadata(
        prompt_file="example/prompts/rag_answer.txt",
        commit_sha="abc1234",
        pr_number="42",
    )


class TestEvalRunner:
    @pytest.mark.asyncio
    async def test_run_creates_db_record(
        self,
        db_session,
        test_settings,
        sample_dataset,
        sample_prompt,
        sample_metadata,
    ):
        mock_metric_result = _make_metric_result()

        with patch("backend.runner.METRIC_REGISTRY", {
            "answer_relevance": MagicMock(return_value=MagicMock(
                score=AsyncMock(return_value=mock_metric_result)
            ))
        }), patch.object(
            EvalRunner, "_get_actual_answer", new=AsyncMock(return_value="Mocked answer")
        ):
            runner = EvalRunner(settings=test_settings, session=db_session)
            result = await runner.run(
                dataset=sample_dataset,
                prompt_template=sample_prompt,
                run_metadata=sample_metadata,
            )

        assert isinstance(result, EvalRunResult)
        assert result.run_id > 0
        assert result.total_samples == 2
        assert result.prompt_file == "example/prompts/rag_answer.txt"

    @pytest.mark.asyncio
    async def test_run_returns_aggregate_scores(
        self,
        db_session,
        test_settings,
        sample_dataset,
        sample_prompt,
        sample_metadata,
    ):
        mock_metric_result = _make_metric_result(score=0.88)

        mock_metric = MagicMock()
        mock_metric.score = AsyncMock(return_value=mock_metric_result)

        with patch("backend.runner.METRIC_REGISTRY", {
            "answer_relevance": MagicMock(return_value=mock_metric)
        }), patch.object(
            EvalRunner, "_get_actual_answer", new=AsyncMock(return_value="Good answer")
        ):
            test_settings.enabled_metrics = ["answer_relevance"]
            runner = EvalRunner(settings=test_settings, session=db_session)
            result = await runner.run(
                dataset=sample_dataset,
                prompt_template=sample_prompt,
                run_metadata=sample_metadata,
            )

        assert "answer_relevance" in result.aggregate_scores
        assert abs(result.aggregate_scores["answer_relevance"] - 0.88) < 0.01

    @pytest.mark.asyncio
    async def test_run_handles_metric_exception_gracefully(
        self,
        db_session,
        test_settings,
        sample_dataset,
        sample_prompt,
        sample_metadata,
    ):
        mock_metric = MagicMock()
        mock_metric.score = AsyncMock(side_effect=RuntimeError("Metric exploded"))

        with patch("backend.runner.METRIC_REGISTRY", {
            "answer_relevance": MagicMock(return_value=mock_metric)
        }), patch.object(
            EvalRunner, "_get_actual_answer", new=AsyncMock(return_value="Answer")
        ):
            test_settings.enabled_metrics = ["answer_relevance"]
            runner = EvalRunner(settings=test_settings, session=db_session)
            result = await runner.run(
                dataset=sample_dataset,
                prompt_template=sample_prompt,
                run_metadata=sample_metadata,
            )

        # Should not raise; should return 0.0 for the failed metric
        assert result.aggregate_scores.get("answer_relevance", 0.0) == 0.0

    @pytest.mark.asyncio
    async def test_run_status_passed_when_all_thresholds_met(
        self,
        db_session,
        test_settings,
        sample_dataset,
        sample_prompt,
        sample_metadata,
    ):
        # Score of 0.95 is above all thresholds
        mock_result = _make_metric_result(score=0.95, passed=True)
        mock_metric = MagicMock()
        mock_metric.score = AsyncMock(return_value=mock_result)

        with patch("backend.runner.METRIC_REGISTRY", {
            "answer_relevance": MagicMock(return_value=mock_metric)
        }), patch.object(
            EvalRunner, "_get_actual_answer", new=AsyncMock(return_value="Perfect answer")
        ):
            test_settings.enabled_metrics = ["answer_relevance"]
            test_settings.thresholds = {"answer_relevance": 0.70}
            runner = EvalRunner(settings=test_settings, session=db_session)
            result = await runner.run(
                dataset=sample_dataset,
                prompt_template=sample_prompt,
                run_metadata=sample_metadata,
            )

        assert result.status == "passed"

    @pytest.mark.asyncio
    async def test_run_status_failed_when_threshold_not_met(
        self,
        db_session,
        test_settings,
        sample_dataset,
        sample_prompt,
        sample_metadata,
    ):
        mock_result = _make_metric_result(score=0.30, passed=False)
        mock_metric = MagicMock()
        mock_metric.score = AsyncMock(return_value=mock_result)

        with patch("backend.runner.METRIC_REGISTRY", {
            "answer_relevance": MagicMock(return_value=mock_metric)
        }), patch.object(
            EvalRunner, "_get_actual_answer", new=AsyncMock(return_value="Poor answer")
        ):
            test_settings.enabled_metrics = ["answer_relevance"]
            test_settings.thresholds = {"answer_relevance": 0.70}
            runner = EvalRunner(settings=test_settings, session=db_session)
            result = await runner.run(
                dataset=sample_dataset,
                prompt_template=sample_prompt,
                run_metadata=sample_metadata,
            )

        assert result.status == "failed"
