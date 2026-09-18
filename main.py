import asyncio
from typing import Any

import click

from client.llm_client import LLMClient


from dotenv import load_dotenv

load_dotenv()


async def run(messages: dict[str, Any]):
    llm_client = LLMClient()

    async for event in llm_client.chat_completion(messages, stream=True):
        print(event)
    await llm_client.close()


@click.command()
@click.argument("prompt", required=False)
def main(prompt: str | None):
    print(f"Prompt: {prompt}")
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello! How are you?"},
    ]
    asyncio.run(run(messages))
    print("Done!")


main()
# python3.12 main.py "how r u?"
