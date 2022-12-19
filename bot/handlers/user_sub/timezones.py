import pytz
import dateparser

from datetime import datetime
from timezonefinder import TimezoneFinder

from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext

from modules.database import Database

from bot.utils import keyboards
from bot.states import SettingStates
from bot.handlers.user_sub.commons import start_registered


geocore = TimezoneFinder()


class UserTimezoneHandlers:
    def __init__(self, bot: Bot, dp: Dispatcher):
        self.bot = bot
        self.dp = dp

        dp.register_message_handler(self.timezone_received, content_types=[types.ContentType.TEXT, types.ContentType.LOCATION], state=SettingStates.ask_timezone, is_private=True)
        dp.register_message_handler(self.approval_received, content_types=[types.ContentType.TEXT], state=SettingStates.approve_timezone, is_private=True)

    async def ask_timezone(self, message: types.Message, add_cancel=True):
        await SettingStates.ask_timezone.set()
        reply_kb = keyboards.reply_keyboard([["UTC", "MSK", "EET"],
                                             ["\U0001F9ED Отправить местоположение"],
                                             ["\u274C Отменить" if add_cancel else []]], location_idx=1)
        utc_time = datetime.now(tz=pytz.utc).strftime("%H:%M")
        msk_time = datetime.now(tz=pytz.timezone('Europe/Moscow')).strftime("%H:%M")
        eest_time = datetime.now(tz=pytz.timezone('EET')).strftime("%H:%M")
        reply_str = """Пожалуйста, выбери часовой пояс, с которым будет удобнее работать:

<b>* UTC</b> — Среднее время по Гринвичу <b>({utc_time})</b>
<b>* MSK</b> — Московский часовой пояс (+3 GMT) <b>({msk_time})</b>
<b>* EET</b> — Восточная Европа (Прибалтика, Финляндия и Украина) <b>({eet_time})</b>

Также можно отправить своё местоположение (могут потребоваться сервисы геолокации). <b>Это безопасно: сохраняется только часовой пояс, мы не сохраним твоё местоположение.</b>\n\nЕсли ни один из предложенных вариантов не подходит, можно ввести текущее время и мы определим твой часовой пояс. Формат ввода: HH:MM (AM/PM). Например, <code>14:45</code> или <code>02:45 PM</code>.""".format(
            utc_time=utc_time, msk_time=msk_time, eet_time=eest_time
        )
        await self.bot.send_message(message.from_user.id, reply_str, reply_markup=reply_kb)

    @staticmethod
    async def timezone_received(message: types.Message, state: FSMContext):
        if message.location is not None:
            tz_string = geocore.timezone_at(lat=message.location.latitude, lng=message.location.longitude)
            tz = pytz.timezone(tz_string)
            await message.answer("\U0001F310 Местоположение скрыто.")
            await message.delete()
        elif message.text in ["UTC", "MSK", "EET"]:
            tz_string = "Europe/Moscow" if message.text == "MSK" else message.text
            tz = pytz.timezone(tz_string)
        else:
            result = dateparser.parse(message.text)
            if result is None:
                await message.answer("\u26A0 Пожалуйста, придерживайтесь формата выше")
                return
            hh, mm = result.hour, result.minute
            now = datetime.utcnow()
            hh, mm = hh - now.hour, mm - now.minute
            if mm < 0:
                mm += 60
                hh -= 1
            if hh > 12:
                hh -= 24
            if hh < -12:
                hh += 24
            tz_string = ('' if hh < 0 else '+') + str(hh).zfill(2 + int(hh < 0)) + str(mm).zfill(2)
            tz = datetime.strptime(tz_string, "%z").tzinfo
        await state.update_data(tz_string=tz_string)
        now = datetime.now(tz)

        reply_kb = keyboards.reply_keyboard([['\u2714 Да', '\u274C Нет']])
        await message.answer("\U0001F551 Текущее время — {time_now}?".format(
            time_now=now.strftime("%H:%M"), time_now_p=now.strftime("%I:%M %p"),
        ), reply_markup=reply_kb)
        await SettingStates.next()

    async def approval_received(self, message: types.Message, state: FSMContext):
        if message.text == '\u2714 Да':
            async with Database() as db:
                data = await state.get_data()
                if (await db.get_user_val(message.from_user.id, 'user_id')) is None:
                    await db.create_user(message.from_user.id, 'ru', data['tz_string'])
                else:
                    await db.set_user_val(message.from_user.id, 'timezone', data['tz_string'])
            await state.finish()
            await state.reset_data()
            await start_registered(self.bot, message.from_user)
        else:
            reply_kb = keyboards.reply_keyboard([["UTC", "MSK", "EET"],
                                                 ["\U0001F9ED Отправить местоположение"]], location_idx=1)
            await message.answer("Пожалуйста, попробуй ещё раз", reply_markup=reply_kb)
            await SettingStates.previous()
