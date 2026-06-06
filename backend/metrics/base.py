# backend/metrics/base.py
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MetricResult:
    score: float
    passed: bool
    reasoning: str
    latency_ms: int
    metric_name: str = ""
    raw_response: Optional[str] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            # Clamp rather than error — judge responses can be noisy
            self.score = max(0.0, min(1.0, self.score))


class BaseMetric(ABC):
    name: str = ""
    description: str = ""

    def __init__(self, threshold: float = 0.7) -> None:
        self.threshold = threshold

    @abstractmethod
    async def score(
        self,
        query: str,
        context: str,
        expected: str,
        actual: str,
    ) -> MetricResult:
        """Evaluate a single (query, context, expected, actual) tuple."""

    def _make_result(
        self,
        score: float,
        reasoning: str,
        start_time: float,
        raw_response: Optional[str] = None,
    ) -> MetricResult:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        return MetricResult(
            score=score,
            passed=score >= self.threshold,
            reasoning=reasoning,
            latency_ms=latency_ms,
            metric_name=self.name,
            raw_response=raw_response,
        )
