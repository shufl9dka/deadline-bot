import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.utils.callback_data import CallbackData

from modules.database import Database

from bot.handlers.user_sub.commons import start_registered
from bot.handlers.user_sub.deadlines import UserDeadlinesHandlers
from bot.handlers.user_sub.timezones import UserTimezoneHandlers
from bot.states import SettingStates


class UserHandlers:
    def __init__(self, bot: Bot, dp: Dispatcher):
        self.bot = bot
        self.dp = dp

        self.hide_msg_btn = CallbackData('HIDE_ME')

        dp.register_message_handler(self.user_start, commands=["start"], state=None, is_private=True)
        dp.register_message_handler(self.cancel_operation, lambda msg: msg.text in ["\u274C Отменить", '/cancel'], state='*',  is_private=True)
        self.timezone_handlers = UserTimezoneHandlers(bot, dp)
        dp.register_message_handler(
            self.timezone_handlers.ask_timezone,
            lambda msg: msg.text == "\U0001F551 Часовой пояс",
            content_types=[types.ContentType.TEXT],
            state=None, is_private=True
        )

        self.deadline_handlers = UserDeadlinesHandlers(bot, dp)
        dp.register_callback_query_handler(self.query_hide_message, self.hide_msg_btn.filter(), state="*")

    async def cancel_operation(self, message: types.Message, state: FSMContext):
        await state.finish()
        await state.reset_data()
        await start_registered(self.bot, message.from_user)

    async def user_start(self, message: types.Message):
        async with Database() as db:
            new_user: bool = (await db.get_user_val(message.from_user.id, 'user_id')) is None
        if new_user:
            await SettingStates.ask_timezone.set()
            await self.new_user_pipeline(message)
        else:
            await start_registered(self.bot, message.from_user)

    async def new_user_pipeline(self, message: types.Message):
        await self.bot.send_message(message.from_user.id, "\U0001F44B Привет! Перед тем, как пользоваться ботом, нужно указать свой часовой пояс. Это необходимо для комфортной работы со временем твоих дедлайнов.")

        await self.bot.send_chat_action(message.from_user.id, 'typing')
        await asyncio.sleep(2)
        await self.timezone_handlers.ask_timezone(message, add_cancel=False)

    @staticmethod
    async def query_hide_message(query: types.CallbackQuery):
        await query.message.delete()
