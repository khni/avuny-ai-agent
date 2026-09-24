from __future__ import annotations
from typing import AsyncGenerator, Awaitable, Callable
from agent.events import AgentEvent, AgentEventType

from client import llm_client
from client.llm_client import LLMClient
from client.response import StreamEventType, TokenUsage, ToolCall, ToolResultMessage
from config.config import Config
from context.manager import ContextManager
from tools.registry import create_default_registry


class Agent:
    def __init__(
        self,
        config: Config,
    ):
        self.config = config
        self.client = LLMClient(config)
        self.context_manager = ContextManager(self.config)
        self.tool_registry = create_default_registry(config)

    async def run(self, message: str):
        yield AgentEvent.agent_start(message)
        self.context_manager.add_user_message(message)

        final_response: str | None = None

        async for event in self._agentic_loop():
            yield event

            if event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content")

        yield AgentEvent.agent_end(final_response)

    async def _agentic_loop(self) -> AsyncGenerator[AgentEvent, None]:

        messages = self.context_manager.get_messages()

        response_text = ""

        tool_schemas = self.tool_registry.get_schemas()

        usage: TokenUsage | None = None

        async for event in self.client.chat_completion(
            messages, tools=tool_schemas if tool_schemas else None, stream=True
        ):
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
            self.context_manager.add_assistant_message(response_text)
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
