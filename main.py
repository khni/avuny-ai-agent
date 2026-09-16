import asyncio

from client.llm_client import LLMClient


from dotenv import load_dotenv

load_dotenv()


async def main():

    llm_client = LLMClient()

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello! How are you?"},
    ]

    await llm_client.chat_completion(messages, stream=False)
    await llm_client.close()


asyncio.run(main())
