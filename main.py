import asyncio
from bot import loader


async def main():
    await loader.run()


if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
