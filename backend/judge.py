# backend/judge.py
from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class JudgeTimeoutError(Exception):
    """Raised when all retry attempts to the Ollama judge fail."""


class JudgeError(Exception):
    """General judge communication error."""


class OllamaJudge:
    def __init__(self, base_url: str, model: str, timeout: int = 25) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout + 5.0, connect=10.0),
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def health_check(self) -> bool:
        try:
            client = self._get_client()
            resp = await client.get("/api/tags", timeout=5.0)
            return resp.status_code == 200
        except Exception as exc:
            logger.warning("Ollama health check failed: %s", exc)
            return False

    async def judge(self, prompt: str, timeout: Optional[int] = None) -> str:
        effective_timeout = timeout or self.timeout
        last_exc: Optional[Exception] = None

        for attempt in range(3):
            backoff = 2 ** attempt  # 1s, 2s, 4s
            if attempt > 0:
                await asyncio.sleep(backoff)
            try:
                result = await self._call_ollama(prompt, effective_timeout)
                return result
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                last_exc = exc
                logger.warning(
                    "Ollama judge attempt %d/3 failed: %s", attempt + 1, exc
                )
            except Exception as exc:
                last_exc = exc
                logger.error("Unexpected judge error on attempt %d/3: %s", attempt + 1, exc)

        raise JudgeTimeoutError(
            f"All 3 Ollama judge attempts failed. Last error: {last_exc}"
        )

    async def _call_ollama(self, prompt: str, timeout: int) -> str:
        client = self._get_client()
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.0,
                "top_p": 1.0,
            },
        }

        try:
            resp = await client.post(
                "/api/generate",
                json=payload,
                timeout=httpx.Timeout(float(timeout), connect=10.0),
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise JudgeError(f"Ollama returned HTTP {exc.response.status_code}") from exc

        body = resp.text.strip()

        # Ollama may return either a single JSON object or newline-delimited stream
        if "\n" in body:
            # Streaming format — concatenate all response fragments
            full_response = ""
            for line in body.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                    full_response += chunk.get("response", "")
                    if chunk.get("done", False):
                        break
                except json.JSONDecodeError:
                    continue
            return full_response.strip()
        else:
            try:
                data = json.loads(body)
                return data.get("response", "").strip()
            except json.JSONDecodeError as exc:
                raise JudgeError(f"Failed to parse Ollama response: {body[:200]}") from exc
