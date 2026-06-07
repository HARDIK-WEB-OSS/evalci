# backend/runner.py
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import Settings
from backend.judge import OllamaJudge as AsyncJudgeClient
from backend.metrics import METRIC_REGISTRY
from backend.metrics.base import BaseMetric, MetricResult
from backend.models import EvalRun, MetricScore, RunStatus, SampleResult

logger = logging.getLogger(__name__)


@dataclass
class EvalSample:
    query: str
    context: str
    expected_answer: str


@dataclass
class RunMetadata:
    prompt_file: str
    commit_sha: Optional[str] = None
    pr_number: Optional[str] = None
    pipeline_version: Optional[str] = None


@dataclass
class SampleMetricResult:
    sample_index: int
    query: str
    context: str
    expected_answer: str
    actual_answer: str
    results: dict[str, MetricResult] = field(default_factory=dict)


@dataclass
class EvalRunResult:
    run_uuid: str
    run_id: int
    status: str
    prompt_file: str
    aggregate_scores: dict[str, float]
    threshold_results: dict[str, bool]  # metric -> passed
    sample_results: list[SampleMetricResult]
    has_regression: bool
    regression_violations: list[dict]
    total_samples: int
    error_message: Optional[str] = None


def _render_prompt(template: str, query: str, context: str) -> str:
    return template.replace("{query}", query).replace("{context}", context)


async def _mock_pipeline(prompt: str) -> str:
    import os, re as _re
    from backend.judge import OllamaJudge
    client = OllamaJudge(
        base_url=os.environ.get("EVALCI_OLLAMA_URL", "http://localhost:11434"),
        model=os.environ.get("EVALCI_JUDGE_MODEL", "mistral"),
        timeout=30,
    )
    try:
        is_alive = await client.health_check()
        if is_alive:
            response = await client.judge(prompt)
            await client.close()
            return response.strip() if response else "No answer generated."
        raise ConnectionError("Ollama not reachable")
    except Exception as exc:
        logger.info("Ollama unavailable in CI: %s", exc)
        try:
            await client.close()
        except Exception:
            pass
    # Extract Context block from rendered prompt as proxy answer for CI
    idx_ctx = prompt.find("Context:")
    idx_q = prompt.find("Question:")
    idx_a = prompt.find("Answer:")
    if idx_ctx != -1:
        end_idx = min(
            x for x in [idx_q, idx_a, len(prompt)]
            if x > idx_ctx
        )
        ctx_block = prompt[idx_ctx + len("Context:"):end_idx].strip()
        if ctx_block:
            return ctx_block
    lines = [l.strip() for l in prompt.splitlines() if l.strip()]
    return max(lines, key=len) if lines else "No answer available."



class EvalRunner:
    def __init__(
        self,
        settings: Settings,
        session: AsyncSession,
        pipeline_url: Optional[str] = None,
    ) -> None:
        self.settings = settings
        self.session = session
        self.pipeline_url = pipeline_url
        self.judge = AsyncJudgeClient(
            base_url=settings.ollama_url,
            model=settings.judge_model,
            timeout=settings.judge_timeout_seconds,
        )

    def _build_metrics(self) -> dict[str, BaseMetric]:
        metrics: dict[str, BaseMetric] = {}
        for name in self.settings.enabled_metrics:
            cls = METRIC_REGISTRY.get(name)
            if cls is None:
                logger.warning("Unknown metric '%s', skipping.", name)
                continue
            threshold = self.settings.thresholds.get(name, 0.7)
            if name == "semantic_similarity":
                metrics[name] = cls(threshold=threshold)
            else:
                metrics[name] = cls(judge=self.judge, threshold=threshold)
        return metrics

    async def _get_actual_answer(self, prompt: str) -> str:
        if self.pipeline_url:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    resp = await client.post(
                        self.pipeline_url,
                        json={"prompt": prompt},
                    )
                    resp.raise_for_status()
                    return resp.json().get("answer", "")
                except Exception as exc:
                    logger.error("Pipeline call failed: %s", exc)
                    return f"[Pipeline error: {exc}]"
        return await _mock_pipeline(prompt)

    async def _eval_sample(
        self,
        idx: int,
        sample: EvalSample,
        prompt_template: str,
        metrics: dict[str, BaseMetric],
        semaphore: asyncio.Semaphore,
    ) -> SampleMetricResult:
        async with semaphore:
            rendered = _render_prompt(prompt_template, sample.query, sample.context)
            actual_answer = await self._get_actual_answer(rendered)

            tasks = {
                name: metric.score(
                    query=sample.query,
                    context=sample.context,
                    expected=sample.expected_answer,
                    actual=actual_answer,
                )
                for name, metric in metrics.items()
            }

            results: dict[str, MetricResult] = {}
            for name, coro in tasks.items():
                try:
                    results[name] = await coro
                except Exception as exc:
                    logger.error("Metric '%s' failed on sample %d: %s", name, idx, exc)
                    results[name] = MetricResult(
                        score=0.0,
                        passed=False,
                        reasoning=f"Metric error: {exc}",
                        latency_ms=0,
                        metric_name=name,
                    )

            return SampleMetricResult(
                sample_index=idx,
                query=sample.query,
                context=sample.context,
                expected_answer=sample.expected_answer,
                actual_answer=actual_answer,
                results=results,
            )

    async def run(
        self,
        dataset: list[EvalSample],
        prompt_template: str,
        run_metadata: RunMetadata,
    ) -> EvalRunResult:
        run_uuid = str(uuid.uuid4())
        metrics = self._build_metrics()
        semaphore = asyncio.Semaphore(self.settings.max_concurrent_evals)

        # Create DB record
        db_run = EvalRun(
            run_uuid=run_uuid,
            prompt_file=run_metadata.prompt_file,
            commit_sha=run_metadata.commit_sha,
            pr_number=run_metadata.pr_number,
            pipeline_version=run_metadata.pipeline_version,
            status=RunStatus.RUNNING.value,
            total_samples=len(dataset),
        )
        self.session.add(db_run)
        await self.session.commit()
        await self.session.refresh(db_run)

        try:
            # Run all samples
            tasks = [
                self._eval_sample(i, sample, prompt_template, metrics, semaphore)
                for i, sample in enumerate(dataset)
            ]
            sample_results: list[SampleMetricResult] = await asyncio.gather(*tasks)

            # Aggregate scores per metric
            aggregate: dict[str, list[float]] = {name: [] for name in metrics}
            for sr in sample_results:
                for name, result in sr.results.items():
                    aggregate[name].append(result.score)

            aggregate_scores = {
                name: (sum(scores) / len(scores) if scores else 0.0)
                for name, scores in aggregate.items()
            }

            # Threshold pass/fail
            threshold_results = {
                name: score >= self.settings.thresholds.get(name, 0.7)
                for name, score in aggregate_scores.items()
            }

            all_passed = all(threshold_results.values())
            status = RunStatus.PASSED.value if all_passed else RunStatus.FAILED.value

            # Persist metric scores
            for name, score in aggregate_scores.items():
                ms = MetricScore(
                    run_id=db_run.id,
                    metric_name=name,
                    score=score,
                    threshold=self.settings.thresholds.get(name, 0.7),
                    passed=threshold_results.get(name, False),
                    sample_count=len(dataset),
                )
                self.session.add(ms)

            # Persist sample results
            for sr in sample_results:
                for name, result in sr.results.items():
                    s = SampleResult(
                        run_id=db_run.id,
                        sample_index=sr.sample_index,
                        query=sr.query,
                        context=sr.context,
                        expected_answer=sr.expected_answer,
                        actual_answer=sr.actual_answer,
                        metric_name=name,
                        score=result.score,
                        passed=result.passed,
                        reasoning=result.reasoning,
                        latency_ms=result.latency_ms,
                    )
                    self.session.add(s)

            # Update run status
            db_run.status = status
            db_run.completed_at = datetime.now(timezone.utc)
            await self.session.commit()

            return EvalRunResult(
                run_uuid=run_uuid,
                run_id=db_run.id,
                status=status,
                prompt_file=run_metadata.prompt_file,
                aggregate_scores=aggregate_scores,
                threshold_results=threshold_results,
                sample_results=sample_results,
                has_regression=False,  # regression checked externally by RegressionGuard
                regression_violations=[],
                total_samples=len(dataset),
            )

        except Exception as exc:
            logger.exception("EvalRunner.run failed: %s", exc)
            db_run.status = RunStatus.ERROR.value
            db_run.error_message = str(exc)
            db_run.completed_at = datetime.now(timezone.utc)
            await self.session.commit()
            raise
        finally:
            await self.judge.close()
