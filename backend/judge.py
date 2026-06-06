import os
import json
import asyncio
from openai import AsyncOpenAI


class AsyncJudgeClient:
    def __init__(self, base_url: str = None, model: str = None, timeout: float = 25):
        self.provider = os.getenv("EVALCI_PROVIDER", "ollama").lower()
        self.timeout = timeout

        if self.provider == "groq":
            self.api_key = os.getenv("GROQ_API_KEY")
            if not self.api_key:
                raise ValueError("GROQ_API_KEY environment variable is required for Groq provider.")
            self.base_url = "https://api.groq.com/openai/v1"
            self.model = os.getenv("EVALCI_MODEL", "llama-3.1-8b-instant")
            client_base = self.base_url
        else:
            self.base_url = base_url or os.getenv("OLLAMA_URL", "http://localhost:11434")
            self.model = model or os.getenv("EVALCI_MODEL", "mistral")
            self.api_key = "ollama"
            client_base = f"{self.base_url}/v1"

        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=client_base,
            timeout=self.timeout,
        )

    async def judge(self, prompt: str) -> str:
        """Legacy single-prompt interface used by metric classes."""
        retries = 3
        delay = 1

        for attempt in range(retries):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.0,
                )
                return response.choices[0].message.content
            except Exception as e:
                if attempt == retries - 1:
                    return json.dumps({"score": 0.0, "reasoning": f"Evaluation engine failure: {str(e)}"})
                await asyncio.sleep(delay)
                delay *= 2

    async def evaluate_json(self, system_prompt: str, user_prompt: str) -> dict:
        """Structured two-prompt interface."""
        retries = 3
        delay = 1

        for attempt in range(retries):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.0,
                )
                raw_content = response.choices[0].message.content
                return json.loads(raw_content)
            except Exception as e:
                if attempt == retries - 1:
                    return {"score": 0.0, "reasoning": f"Evaluation engine failure: {str(e)}"}
                await asyncio.sleep(delay)
                delay *= 2

    async def close(self):
        """Cleanup — closes the underlying HTTP client."""
        await self.client.close()
