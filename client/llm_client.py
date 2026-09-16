import os
from typing import Any

from openai import AsyncOpenAI


class LLMClient:
    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None

    def get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=os.environ["OPENROUTER_API_KEY"],  # fail fast if missing
                base_url=os.environ["OPENROUTER_BASE_URL"],
            )

        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None

    async def chat_completion(
        self, messages: list[dict[str, Any]], stream: bool = True
    ):
        client = self.get_client()
        kwargs = {
            "model": "~deepseek/deepseek-pro-latest",
            "messages": messages,
            "stream": stream,
            "max_tokens": 512,
        }
        if stream:
            await self._stream_response(client, kwargs)
        else:
            await self._non_stream_response(client, kwargs)

    async def _stream_response(
        self,
        client: AsyncOpenAI,
        kwargs: dict[str, Any],
    ):
        pass

    async def _non_stream_response(self, client: AsyncOpenAI, kwargs: dict[str, Any]):
        response = await client.chat.completions.create(**kwargs)
        print(response)
