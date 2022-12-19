import asyncio
import html
from datetime import datetime, timedelta

from aiogram.bot import Bot
from aiogram.utils.callback_data import CallbackData

from bot.utils.functions import resolve_timezone
from bot.utils.keyboards import inline_keyboard
from modules.database import Database

hide_msg_btn = CallbackData('HIDE_ME')


def local_datetime_fmt(dt: datetime, fmt: str = "%d %m %Y %H:%M", loc: str = 'ru') -> str:
    months_name = {
        'ru': ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля',
               'августа', 'сентября', 'октября', 'ноября', 'декабря']
    }
    return dt.strftime(fmt.replace('%m', months_name[loc][dt.month - 1]))


async def send_remind(bot: Bot, deadline: dict, deadline_time: bool):
    if deadline_time:
        if deadline.get('done'):
            text = "\u2705 <b>Наступил дедлайн, который уже выполнен: \"{title}\"!</b>\n\n"
        else:
            text = "\u2757 <b>Наступил дедлайн: \"{title}\"!</b>\n\n"
        if deadline.get('repeat_in'):
            text += "Время следующего дедлайна назначено на <b>{next_deadline}</b>"
        else:
            text += "Время следующего дедлайна не было установлено, поэтому дедлайн удалён."
    else:
        text = "\u26A0 <b>Скоро подойдёт дедлайн: \"{title}\"!</b>\n\n" \
               "Время дедлайна назначено на <b>{deadline_date}</b>. Постарайся не пропустить его!"
    text += "\n\n<i>(это сообщение можно убрать, нажав кнопку ниже)</i>"
    text = text.format(
        title=html.escape(deadline['title']),
        deadline_date=local_datetime_fmt(deadline['deadline'], fmt="%d %m %H:%M"),
        next_deadline=local_datetime_fmt((deadline['deadline'] + timedelta(seconds=deadline['repeat_in'])), fmt="%d %m %H:%M") if deadline.get('repeat_in') else None
    )
    try:
        reply_kb = inline_keyboard([
            [("\U0001F440 Скрыть сообщение", hide_msg_btn.new())]
        ])
        await bot.send_message(deadline['user_id'], text, reply_markup=reply_kb)
    except Exception:
        pass


async def deadlines_loop(bot: Bot, upd_delta: float = 6):
    while True:
        await asyncio.sleep(upd_delta)
        async with Database() as db:
            timezones = {k: resolve_timezone(v) for k, v in (await db.get_user_timezones()).items()}
            for deadline in await db.get_deadlines():
                user_tz = timezones.get(deadline['user_id'])
                now = datetime.now(user_tz)
                deadline_date: datetime = deadline['deadline'].replace(tzinfo=now.tzinfo)
                if deadline.get('done') is False and deadline.get('reminded') is False and deadline.get('remind_in'):
                    remind_date: datetime = deadline_date - timedelta(seconds=deadline['remind_in'])
                    if remind_date <= now:
                        await send_remind(bot, deadline, deadline_time=False)
                        await db.update_deadline(deadline['deadline_id'], reminded=True)
                if deadline_date <= now:
                    await send_remind(bot, deadline, deadline_time=True)
                    if deadline.get('repeat_in') is None:
                        await db.remove_deadline(deadline['deadline_id'])
                    else:
                        await db.update_deadline(
                            deadline['deadline_id'],
                            deadline=deadline['deadline'] + timedelta(seconds=deadline['repeat_in']),
                            done=False, reminded=False
                        )
