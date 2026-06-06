# backend/metrics/answer_relevance.py
from __future__ import annotations

import json
import logging
import re
import time

from backend.judge import OllamaJudge
from backend.metrics.base import BaseMetric, MetricResult

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = """\
You are an expert evaluator assessing the relevance of an answer to a given question.

Question: {query}

Answer: {actual}

Your task: Score how relevant the answer is to the question on a scale from 0.0 to 1.0.
- 1.0 = The answer directly and completely addresses the question
- 0.7 = The answer is mostly relevant with minor tangents
- 0.4 = The answer is partially relevant but misses key aspects
- 0.1 = The answer is barely relevant or off-topic
- 0.0 = The answer is completely irrelevant

Respond ONLY with a JSON object, no other text:
{{"score": <float between 0.0 and 1.0>, "reasoning": "<one sentence explanation>"}}
"""


def _parse_score(raw: str) -> tuple[float, str]:
    """Extract score and reasoning from judge response with multiple fallback strategies."""
    # Strategy 1: parse as JSON directly
    try:
        cleaned = raw.strip()
        # Find the first JSON object in the response
        match = re.search(r'\{[^{}]*\}', cleaned, re.DOTALL)
        if match:
            data = json.loads(match.group())
            score = float(data.get("score", 0.0))
            reasoning = str(data.get("reasoning", "No reasoning provided"))
            return max(0.0, min(1.0, score)), reasoning
    except (json.JSONDecodeError, ValueError, KeyError):
        pass

    # Strategy 2: extract float with regex
    score_match = re.search(r'(?:score["\s:]+)?([01](?:\.\d+)?)', raw)
    if score_match:
        try:
            score = float(score_match.group(1))
            return max(0.0, min(1.0, score)), raw[:200]
        except ValueError:
            pass

    logger.warning("Failed to parse answer_relevance score from: %s", raw[:200])
    return 0.0, f"Parse error. Raw response: {raw[:200]}"


class AnswerRelevanceMetric(BaseMetric):
    name = "answer_relevance"
    description = "Measures how relevant the generated answer is to the input query."

    def __init__(self, judge: OllamaJudge, threshold: float = 0.70) -> None:
        super().__init__(threshold=threshold)
        self.judge = judge

    async def score(
        self,
        query: str,
        context: str,
        expected: str,
        actual: str,
    ) -> MetricResult:
        start = time.perf_counter()
        prompt = _PROMPT_TEMPLATE.format(query=query, actual=actual)

        try:
            raw = await self.judge.judge(prompt)
        except Exception as exc:
            logger.error("Judge call failed for answer_relevance: %s", exc)
            return self._make_result(0.0, f"Judge error: {exc}", start)

        score_val, reasoning = _parse_score(raw)
        return self._make_result(score_val, reasoning, start, raw_response=raw)
