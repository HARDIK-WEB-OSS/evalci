import os
import httpx
from openai import AsyncOpenAI

class AsyncJudgeClient:
    def __init__(self):
        # Drop-in compatibility for Groq, TogetherAI, or OpenAI
        self.api_key = os.getenv("EVALCI_API_KEY")
        self.base_url = os.getenv("EVALCI_API_URL", "https://api.groq.com/openai/v1")
        self.model = os.getenv("EVALCI_MODEL", "llama3-8b-8192")
        
        if not self.api_key:
            raise ValueError("EVALCI_API_KEY environment variable is missing.")
            
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    async def evaluate_json(self, system_prompt: str, user_prompt: str) -> str:
        """Sends an evaluation request to the cloud LLM provider with exponential backoff retry."""
        import asyncio
        retries = 3
        delay = 1
        
        for attempt in range(retries):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0
                )
                return response.choices[0].message.content
            except Exception as e:
                if attempt == retries - 1:
                    raise e
                await asyncio.sleep(delay)
                delay *= 2
