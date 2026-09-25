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
        tool_calls: list[ToolCall] = []

        async for event in self.client.chat_completion(
            messages, tools=tool_schemas if tool_schemas else None, stream=True
        ):
            if event.type == StreamEventType.TEXT_DELTA:
                if event.text_delta:
                    content = event.text_delta.content
                    response_text += content
                    yield AgentEvent.text_delta(content)
            elif event.type == StreamEventType.TOOL_CALL_COMPLETE:
                if event.tool_call:
                    tool_calls.append(event.tool_call)
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
        # if not tool_calls:
        #     if usage:
        #         self.session.context_manager.set_latest_usage(usage)
        #         self.session.context_manager.add_usage(usage)

        #     self.session.context_manager.prune_tool_outputs()
        #     return

        tool_call_results: list[ToolResultMessage] = []

        for tool_call in tool_calls:
            yield AgentEvent.tool_call_start(
                tool_call.call_id,
                tool_call.name,
                tool_call.arguments,
            )

            # self.session.loop_detector.record_action(
            #     "tool_call",
            #     tool_name=tool_call.name,
            #     args=tool_call.arguments,
            # )

            result = await self.tool_registry.invoke(
                tool_call.name,
                tool_call.arguments,
                self.config.cwd,
                # self.session.hook_system,
                # self.session.approval_manager,
            )

            yield AgentEvent.tool_call_complete(
                tool_call.call_id,
                tool_call.name,
                result,
            )

            tool_call_results.append(
                ToolResultMessage(
                    tool_call_id=tool_call.call_id,
                    content=result.to_model_output(),
                    is_error=not result.success,
                )
            )

        for tool_result in tool_call_results:
            self.context_manager.add_tool_result(
                tool_result.tool_call_id,
                tool_result.content,
            )

        # loop_detection_error = self.session.loop_detector.check_for_loop()
        # if loop_detection_error:
        #     loop_prompt = create_loop_breaker_prompt(loop_detection_error)
        #     self.session.context_manager.add_user_message(loop_prompt)

        # if usage:
        #     self.session.context_manager.set_latest_usage(usage)
        #     self.session.context_manager.add_usage(usage)

        # self.session.context_manager.prune_tool_outputs()

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
