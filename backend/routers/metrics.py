# backend/routers/metrics.py
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database import get_session
from backend.models import EvalRun, MetricScore
from backend.schemas import (
    CompareRunsResponse,
    EvalRunSummary,
    LatestMetricsResponse,
    MetricScoreOut,
    MetricTrendPoint,
    MetricTrendResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/metrics", tags=["metrics"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("/trend", response_model=MetricTrendResponse)
async def get_metric_trend(
    session: SessionDep,
    metric: str = Query(..., description="Metric name to chart"),
    limit: int = Query(default=20, ge=1, le=100),
):
    result = await session.execute(
        select(MetricScore, EvalRun.run_uuid, EvalRun.commit_sha)
        .join(EvalRun, MetricScore.run_id == EvalRun.id)
        .where(MetricScore.metric_name == metric)
        .order_by(MetricScore.recorded_at.desc())
        .limit(limit)
    )
    rows = result.all()

    points = [
        MetricTrendPoint(
            run_id=ms.id,
            run_uuid=run_uuid,
            commit_sha=commit_sha,
            recorded_at=ms.recorded_at,
            score=ms.score,
            threshold=ms.threshold,
            passed=ms.passed,
        )
        for ms, run_uuid, commit_sha in reversed(rows)
    ]

    return MetricTrendResponse(metric=metric, points=points)


@router.get("/latest", response_model=LatestMetricsResponse)
async def get_latest_metrics(session: SessionDep):
    # Get the most recent run that has metric scores
    run_result = await session.execute(
        select(EvalRun)
        .options(selectinload(EvalRun.metric_scores))
        .order_by(EvalRun.created_at.desc())
        .limit(1)
    )
    run = run_result.scalar_one_or_none()

    if run is None or not run.metric_scores:
        return LatestMetricsResponse(metrics={})

    return LatestMetricsResponse(
        metrics={
            ms.metric_name: MetricScoreOut.model_validate(ms)
            for ms in run.metric_scores
        }
    )


@router.get("/compare", response_model=CompareRunsResponse)
async def compare_runs(
    session: SessionDep,
    run_a: int = Query(..., description="First run ID"),
    run_b: int = Query(..., description="Second run ID"),
):
    async def load_run(run_id: int) -> EvalRun:
        result = await session.execute(
            select(EvalRun)
            .where(EvalRun.id == run_id)
            .options(selectinload(EvalRun.metric_scores))
        )
        r = result.scalar_one_or_none()
        if r is None:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        return r

    run_a_obj = await load_run(run_a)
    run_b_obj = await load_run(run_b)

    scores_a = {ms.metric_name: ms.score for ms in run_a_obj.metric_scores}
    scores_b = {ms.metric_name: ms.score for ms in run_b_obj.metric_scores}

    all_metrics = set(scores_a) | set(scores_b)
    deltas = {
        m: scores_b.get(m, 0.0) - scores_a.get(m, 0.0)
        for m in all_metrics
    }

    return CompareRunsResponse(
        run_a=EvalRunSummary.model_validate(run_a_obj),
        run_b=EvalRunSummary.model_validate(run_b_obj),
        deltas=deltas,
    )
