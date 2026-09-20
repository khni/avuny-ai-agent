import asyncio
import sys
import click
from config.loader import load_config
from pathlib import Path
from agent.agent import Agent
from agent.events import AgentEventType
from config.config import Config
from ui.tui import TUI, get_console

console = get_console()


class CLI:
    def __init__(self, config: Config):
        self.agent: Agent | None = None
        self.config = config
        self.tui = TUI(config, console)

    async def run_single(self, message: str):
        async with Agent(self.config) as agent:
            self.agent = agent
            return await self._process_message(message)

    async def run_interactive(self) -> str | None:
        self.tui.print_welcome(
            "AI Agent",
            lines=[
                f"model: {self.config.model_name}",
                f"cwd: {self.config.cwd}",
                "commands: /help /config /approval /model /exit",
            ],
        )

    async def _process_message(self, message: str) -> str | None:
        if not self.agent:
            return None
        assistant_streaming = False
        final_response: str | None = None

        async for event in self.agent.run(message):
            if event.type == AgentEventType.TEXT_DELTA:
                content = event.data.get("content", "")
                if not assistant_streaming:
                    self.tui.begin_assistant()
                    assistant_streaming = True
                self.tui.stream_assistant_delta(content)
            elif event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content")
                if assistant_streaming:
                    self.tui.end_assistant()
                    assistant_streaming = False
            elif event.type == AgentEventType.AGENT_ERROR:
                error = event.data.get("error", "Unknown error")
                console.print(f"\n[error]Error: {error}[/error]")
        return final_response



@click.command()
@click.argument("prompt", required=False)
@click.option(
    "--cwd",
    "-c",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Current working directory",
)
def main(
    prompt: str | None,
    cwd: Path | None,
):
    try:
        config = load_config(cwd=cwd)
    except Exception as e:
        console.print(f"[error]Configuration Error: {e}[/error]")

    errors = config.validate()

    if errors:
        for error in errors:
            console.print(f"[error]{error}[/error]")

        sys.exit(1)

    cli = CLI(config)

    # messages = [{"role": "user", "content": prompt}]
    if prompt:
        print(f"[info]Running single prompt: {prompt}[/info]")
        result = asyncio.run(cli.run_single(prompt))
        if result is None:
            sys.exit(1)
    else:
        asyncio.run(cli.run_interactive())


main()
