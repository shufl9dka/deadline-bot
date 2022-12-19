from aiogram import Bot, types
from bot.utils import keyboards


async def start_registered(bot: Bot, user: types.User, text: str = None):
    reply_kb = keyboards.reply_keyboard([
        ["\u2795 Новый дедлайн", "\U0001F4CB Список дедлайнов"],
        ["\U0001F551 Часовой пояс"]
    ])
    await bot.send_message(user.id, text if text else "\U0001F44B Мы в главном меню", reply_markup=reply_kb)
