from __future__ import annotations
from typing import AsyncGenerator, Awaitable, Callable
from agent.events import AgentEvent, AgentEventType

from client import llm_client
from client.llm_client import LLMClient
from client.response import StreamEventType, TokenUsage, ToolCall, ToolResultMessage
from config.config import Config


class Agent:
    def __init__(
        self,
        config: Config,
    ):
        self.config = config
        self.client = LLMClient(config)

    async def run(self, message: str):
        yield AgentEvent.agent_start(message)

        final_response: str | None = None

        async for event in self._agentic_loop():
            yield event

            if event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content")

        yield AgentEvent.agent_end(final_response)

    async def _agentic_loop(self) -> AsyncGenerator[AgentEvent, None]:

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello! How are you?"},
        ]

        response_text = ""

        usage: TokenUsage | None = None

        async for event in self.client.chat_completion(messages, stream=True):
            if event.type == StreamEventType.TEXT_DELTA:
                if event.text_delta:
                    content = event.text_delta.content
                    response_text += content
                    yield AgentEvent.text_delta(content)
            elif event.type == StreamEventType.ERROR:
                yield AgentEvent.agent_error(
                    event.error or "Unknown error occurred.",
                )
            elif event.type == StreamEventType.MESSAGE_COMPLETE:
                usage = event.usage
        if response_text:
            yield AgentEvent.text_complete(response_text)
            # self.session.loop_detector.record_action(
            #     "response",
            #     text=response_text,
            # )

    async def __aenter__(self) -> Agent:
        return self

    async def __aexit__(
        self,
        exc_type,
        exc_val,
        exc_tb,
    ) -> None:
        if self.client:
            await self.client.close()
            self.client = None
