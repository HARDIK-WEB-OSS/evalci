# backend/schemas.py
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Input schemas ──────────────────────────────────────────────────────────

class EvalSampleIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    query: str
    context: str
    expected_answer: str


class RunMetadataIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    prompt_file: str
    commit_sha: Optional[str] = None
    pr_number: Optional[str] = None
    pipeline_version: Optional[str] = None


class TriggerRunRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    dataset: list[EvalSampleIn]
    prompt_template: str
    metadata: RunMetadataIn


class ThresholdUpdateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    thresholds: dict[str, float]


# ── Output schemas ─────────────────────────────────────────────────────────

class SampleResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sample_index: int
    query: str
    context: str
    expected_answer: str
    actual_answer: str
    metric_name: str
    score: float
    passed: bool
    reasoning: Optional[str]
    latency_ms: int


class MetricScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    metric_name: str
    score: float
    threshold: float
    passed: bool
    sample_count: int
    recorded_at: datetime


class EvalRunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_uuid: str
    prompt_file: str
    commit_sha: Optional[str]
    pr_number: Optional[str]
    pipeline_version: Optional[str]
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    total_samples: int
    error_message: Optional[str]
    metric_scores: list[MetricScoreOut] = Field(default_factory=list)


class EvalRunDetail(EvalRunSummary):
    sample_results: list[SampleResultOut] = Field(default_factory=list)


class RunsListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[EvalRunSummary]


class MetricTrendPoint(BaseModel):
    run_id: int
    run_uuid: str
    commit_sha: Optional[str]
    recorded_at: datetime
    score: float
    threshold: float
    passed: bool


class MetricTrendResponse(BaseModel):
    metric: str
    points: list[MetricTrendPoint]


class LatestMetricsResponse(BaseModel):
    metrics: dict[str, MetricScoreOut]


class CompareRunsResponse(BaseModel):
    run_a: EvalRunSummary
    run_b: EvalRunSummary
    deltas: dict[str, float]  # metric_name -> score_b - score_a


class RegressionViolationOut(BaseModel):
    metric: str
    baseline: float
    current: float
    delta: float
    threshold: float
    allowed_delta: float


class RegressionReportOut(BaseModel):
    has_regression: bool
    violations: list[RegressionViolationOut]
