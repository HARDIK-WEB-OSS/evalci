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
                timeout=httpx.Timeout(float(self.timeout) + 5.0, connect=10.0),
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def health_check(self) -> bool:
        try:
            client = self._get_client()
            resp = await client.get(f"{self.base_url}/api/tags", timeout=5.0)
            return resp.status_code == 200
        except Exception as exc:
            logger.warning("Ollama health check failed: %s", exc)
            return False

    async def judge(self, prompt: str, timeout: Optional[int] = None) -> str:
        effective_timeout = timeout or self.timeout
        last_exc: Optional[Exception] = None

        for attempt in range(3):
            if attempt > 0:
                await asyncio.sleep(2 ** attempt)
            try:
                return await self._call_ollama(prompt, effective_timeout)
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                last_exc = exc
                logger.warning("Ollama attempt %d/3 failed: %s", attempt + 1, exc)
            except Exception as exc:
                last_exc = exc
                logger.error("Unexpected judge error attempt %d/3: %s", attempt + 1, exc)

        raise JudgeTimeoutError(
            f"All 3 Ollama attempts failed. Last error: {last_exc}"
        )

    async def _call_ollama(self, prompt: str, timeout: int) -> str:
        client = self._get_client()
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.0},
        }
        try:
            resp = await client.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=httpx.Timeout(float(timeout), connect=10.0),
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise JudgeError(f"Ollama returned HTTP {exc.response.status_code}") from exc

        body = resp.text.strip()

        if "\n" in body:
            full = ""
            for line in body.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                    full += chunk.get("response", "")
                    if chunk.get("done", False):
                        break
                except json.JSONDecodeError:
                    continue
            return full.strip()
        else:
            data = json.loads(body)
            return data.get("response", "").strip()
