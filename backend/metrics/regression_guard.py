# backend/metrics/regression_guard.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RegressionViolation:
    metric: str
    baseline: float
    current: float
    delta: float  # current - baseline (negative = regression)
    threshold: float
    allowed_delta: float
    violation_type: str  # "absolute" | "regression"

    @property
    def severity(self) -> str:
        gap = abs(self.delta)
        if gap > 0.2:
            return "critical"
        elif gap > 0.1:
            return "high"
        return "medium"


@dataclass
class RegressionReport:
    has_regression: bool
    violations: list[RegressionViolation] = field(default_factory=list)
    passed_metrics: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        if not self.has_regression:
            return f"✅ All {len(self.passed_metrics)} metrics passed regression check."
        lines = [f"❌ {len(self.violations)} regression violation(s) detected:"]
        for v in self.violations:
            lines.append(
                f"  • {v.metric}: {v.current:.4f} (baseline: {v.baseline:.4f}, "
                f"delta: {v.delta:+.4f}, type: {v.violation_type})"
            )
        return "\n".join(lines)


class RegressionGuard:
    """
    Checks whether current metric scores represent a regression compared to
    a baseline, enforcing both absolute thresholds and allowed deltas.
    """

    def __init__(self, default_allowed_delta: float = 0.05) -> None:
        self.default_allowed_delta = default_allowed_delta

    def check(
        self,
        current_scores: dict[str, float],
        baseline_scores: dict[str, float],
        thresholds: dict[str, float],
        allowed_deltas: Optional[dict[str, float]] = None,
    ) -> RegressionReport:
        """
        A regression is triggered when:
        1. current_score < absolute_threshold (hard floor)
        OR
        2. current_score < baseline_score - allowed_delta (relative regression)

        Args:
            current_scores: metric_name -> score for this run
            baseline_scores: metric_name -> score for the last known good run
            thresholds: metric_name -> minimum absolute passing score
            allowed_deltas: metric_name -> max allowed drop from baseline
        """
        violations: list[RegressionViolation] = []
        passed: list[str] = []

        for metric, current in current_scores.items():
            absolute_threshold = thresholds.get(metric, 0.0)
            allowed_delta = (
                (allowed_deltas or {}).get(metric, self.default_allowed_delta)
            )
            baseline = baseline_scores.get(metric)
            delta = current - baseline if baseline is not None else 0.0

            violation_type: Optional[str] = None

            # Check absolute threshold first
            if current < absolute_threshold:
                violation_type = "absolute"

            # Check relative regression (only if we have a baseline)
            elif baseline is not None and current < (baseline - allowed_delta):
                violation_type = "regression"

            if violation_type is not None:
                violations.append(
                    RegressionViolation(
                        metric=metric,
                        baseline=baseline if baseline is not None else 0.0,
                        current=current,
                        delta=delta,
                        threshold=absolute_threshold,
                        allowed_delta=allowed_delta,
                        violation_type=violation_type,
                    )
                )
            else:
                passed.append(metric)

        return RegressionReport(
            has_regression=len(violations) > 0,
            violations=violations,
            passed_metrics=passed,
        )
