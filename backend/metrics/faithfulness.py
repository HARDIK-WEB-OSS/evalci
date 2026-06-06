# backend/metrics/faithfulness.py
from __future__ import annotations

import json
import logging
import re
import time
from typing import Optional

from backend.judge import AsyncJudgeClient
from backend.metrics.base import BaseMetric, MetricResult

logger = logging.getLogger(__name__)

_DECOMPOSE_PROMPT = """\
Break the following answer into atomic, self-contained factual claims.
Each claim should be a single, verifiable statement.

Answer: {answer}

Respond ONLY with a JSON array of strings (the claims), no other text:
["claim 1", "claim 2", ...]

If the answer has no verifiable claims, respond with: []
"""

_VERIFY_PROMPT = """\
You are a fact-checker. Determine if the following claim is supported by the given context.

Context: {context}

Claim: {claim}

Respond ONLY with a JSON object, no other text:
{{"supported": true or false, "reasoning": "<one sentence>"}}
"""


def _parse_claims(raw: str) -> list[str]:
    """Extract list of claim strings from judge response."""
    try:
        cleaned = raw.strip()
        match = re.search(r'\[.*?\]', cleaned, re.DOTALL)
        if match:
            claims = json.loads(match.group())
            if isinstance(claims, list):
                return [str(c) for c in claims if c]
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: split on newlines or numbered items
    lines = [
        re.sub(r'^[\d\.\-\*\s]+', '', line).strip()
        for line in raw.splitlines()
        if line.strip()
    ]
    return [l for l in lines if len(l) > 10]


def _parse_verification(raw: str) -> tuple[bool, str]:
    """Extract supported boolean and reasoning."""
    try:
        match = re.search(r'\{[^{}]*\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
            supported = bool(data.get("supported", False))
            reasoning = str(data.get("reasoning", ""))
            return supported, reasoning
    except (json.JSONDecodeError, ValueError, KeyError):
        pass

    # Regex fallback
    lower = raw.lower()
    supported = "true" in lower or "yes" in lower or "supported" in lower
    return supported, raw[:200]


class FaithfulnessMetric(BaseMetric):
    name = "faithfulness"
    description = (
        "Measures whether all claims in the answer are supported by the provided context. "
        "Uses a two-step approach: decompose into claims, then verify each claim."
    )

    def __init__(self, judge: AsyncJudgeClient, threshold: float = 0.75) -> None:
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

        # Step 1: Decompose answer into atomic claims
        decompose_prompt = _DECOMPOSE_PROMPT.format(answer=actual)
        try:
            claims_raw = await self.judge.judge(decompose_prompt)
        except Exception as exc:
            logger.error("Claim decomposition failed: %s", exc)
            return self._make_result(0.0, f"Decomposition error: {exc}", start)

        claims = _parse_claims(claims_raw)

        if not claims:
            # No verifiable claims means we can't fail on faithfulness
            return self._make_result(
                1.0,
                "Answer contains no verifiable factual claims; faithfulness N/A.",
                start,
                raw_response=claims_raw,
            )

        # Step 2: Verify each claim against the context
        verified_count = 0
        reasoning_parts: list[str] = []

        for claim in claims:
            verify_prompt = _VERIFY_PROMPT.format(context=context, claim=claim)
            try:
                verify_raw = await self.judge.judge(verify_prompt)
                supported, claim_reasoning = _parse_verification(verify_raw)
            except Exception as exc:
                logger.warning("Claim verification failed for '%s': %s", claim[:80], exc)
                supported = False
                claim_reasoning = f"Verification error: {exc}"

            if supported:
                verified_count += 1
            status = "✓" if supported else "✗"
            reasoning_parts.append(f"{status} {claim[:100]}: {claim_reasoning}")

        faithfulness_score = verified_count / len(claims)
        reasoning = (
            f"{verified_count}/{len(claims)} claims supported.\n"
            + "\n".join(reasoning_parts)
        )

        return self._make_result(faithfulness_score, reasoning, start, raw_response=claims_raw)
