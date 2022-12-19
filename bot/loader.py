import asyncio

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from bot.utils.filters import PrivateFilter, RegisteredFilter
from bot.handlers.user import UserHandlers

from modules import local_config
from modules.deadlines import deadlines_loop


def register_filters(dp: Dispatcher):
    dp.filters_factory.bind(PrivateFilter)
    dp.filters_factory.bind(RegisteredFilter)


async def run():
    storage = MemoryStorage()

    bot = Bot(token=local_config.cfg['App']['bot_token'], parse_mode='HTML')
    dp = Dispatcher(bot, storage=storage)
    register_filters(dp)

    user_handlers = UserHandlers(bot, dp)
    asyncio.create_task(deadlines_loop(bot))

    print('Bot has started.')
    try:
        await dp.start_polling()
    finally:
        await dp.storage.close()
        await dp.storage.wait_closed()
        await (await bot.get_session()).close()
