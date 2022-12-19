import html
from typing import Optional

from datetime import datetime, timedelta

import dateparser
from timezonefinder import TimezoneFinder

from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.utils.callback_data import CallbackData

from modules.database import Database

from bot.handlers.user_sub.commons import start_registered
from bot.utils import keyboards, functions
from bot.states import DeadlineStates


geocore = TimezoneFinder()
PAGE_SIZE = 12


def fmt_date(date: datetime, tz: str = None):
    if tz is None:
        tz = 'Europe/Moscow'
    date = date.replace(tzinfo=functions.resolve_timezone(tz))
    now = datetime.utcnow().astimezone(functions.resolve_timezone(tz))

    if (now.day, now.month, now.year) == (date.day, date.month, date.year):
        return date.strftime("Сегодня %H:%M")
    now += timedelta(days=1)
    if (now.day, now.month, now.year) == (date.day, date.month, date.year):
        return date.strftime("Завтра %H:%M")
    now += timedelta(days=1)
    if (now.day, now.month, now.year) == (date.day, date.month, date.year):
        return date.strftime("Послезавтра %H:%M")

    return date.strftime("%d.%m.%y %H:%M")


class UserDeadlinesHandlers:
    def __init__(self, bot: Bot, dp: Dispatcher):
        self.bot = bot
        self.dp = dp

        self.kb_idx_cb = CallbackData('kb_action', 'delta')
        self.kb_list_cb = CallbackData('list_pick', 'id', 'act')
        self.del_item_cb = CallbackData('del_it', 'id', 'ans')

        dp.register_message_handler(self.start_adding_deadline, lambda msg: msg.text == "\u2795 Новый дедлайн", content_types=[types.ContentType.TEXT], state=None, is_private=True)
        dp.register_message_handler(self.show_deadlines_handle, lambda msg: msg.text == "\U0001F4CB Список дедлайнов", content_types=[types.ContentType.TEXT], state=None, is_private=True)

        dp.register_message_handler(self.deadline_title_received, content_types=[types.ContentType.TEXT], state=DeadlineStates.deadline_title, is_private=True)
        dp.register_message_handler(self.deadline_date_received, content_types=[types.ContentType.TEXT], state=DeadlineStates.deadline_date, is_private=True)
        dp.register_message_handler(self.deadline_remind_received, content_types=[types.ContentType.TEXT], state=DeadlineStates.remind_delay, is_private=True)
        dp.register_message_handler(self.deadline_repeat_received, content_types=[types.ContentType.TEXT], state=DeadlineStates.repeat_delay, is_private=True)

        dp.register_callback_query_handler(self.query_keyboard_pagenum, self.kb_idx_cb.filter(), state=None)
        dp.register_callback_query_handler(self.query_deadline_act, self.kb_list_cb.filter(), state=None)
        dp.register_callback_query_handler(self.query_approve_del, self.del_item_cb.filter(), state=DeadlineStates.approve_delete)

    async def show_my_deadlines(self, user_id: int, state: FSMContext, page_num: Optional[int] = 0, message: types.Message = None, update=True):
        data = await state.get_data()
        if update or 'deadlines_cache' not in data:
            async with Database() as db:
                deadlines_list = sorted(await db.get_deadlines(user_id), key=lambda x: x['deadline'])
                data['deadlines_cache'] = deadlines_list
                data['timezone'] = await db.get_user_val(user_id, 'timezone')
                await state.update_data(deadlines_cache=data['deadlines_cache'], timezone=data['timezone'])
        if 'prev_list_id' in data and (message is None or message.message_id != data['prev_list_id']):
            try:
                await self.bot.delete_message(user_id, data['prev_list_id'])
                await self.bot.delete_message(user_id, data.get('prev_list_rs'))
            except Exception:
                pass

        page_num = data.get('last_page_num', 0) if page_num is None else page_num
        deadlines_list = data.get('deadlines_cache')
        max_page_num = (len(deadlines_list) - 1) // PAGE_SIZE
        page_num = max(0, min(page_num, max_page_num))
        display_deadlines = deadlines_list[page_num * PAGE_SIZE:(page_num + 1) * PAGE_SIZE]

        layout = [[
            (
                f"{fmt_date(deadline['deadline'], data.get('timezone'))} | {deadline['title']}",
                self.kb_list_cb.new(id=deadline['deadline_id'], act='DEL')
            ),
            (
                "\u2705 Готово" if deadline['done'] else "В процессе",
                self.kb_list_cb.new(id=deadline['deadline_id'], act='DONE')
            )
        ] for deadline in display_deadlines]
        if display_deadlines and max_page_num > 0:
            layout.append(
                [
                    ('<<<', self.kb_idx_cb.new(delta=-1)),
                    (f'{page_num + 1} / {max_page_num + 1}', 'None'),
                    ('>>>', self.kb_idx_cb.new(delta=+1))
                ]
            )
        reply_kb = keyboards.inline_keyboard(layout)
        await state.update_data(last_page_num=page_num)
        if message is None:
            if not deadlines_list:
                msg = await self.bot.send_message(user_id, "\u26A0 У вас нет ни одного дедлайна! Вы можете задать новый.")
            else:
                msg = await self.bot.send_message(user_id, "Выберите дедлайн:", reply_markup=reply_kb)
        else:
            if not deadlines_list:
                msg = await message.edit_text("\u26A0 У вас нет ни одного дедлайна! Вы можете задать новый.")
            else:
                msg = await message.edit_reply_markup(reply_markup=reply_kb)
        await state.update_data(prev_list_id=msg.message_id)
        return msg

    async def show_deadlines_handle(self, message: types.Message, state: FSMContext):
        await state.update_data(curr_page_num=0)
        await self.show_my_deadlines(message.from_user.id, state, 0, update=True)
        await state.update_data(prev_list_rs=message.message_id)

    async def query_keyboard_pagenum(self, query: types.CallbackQuery, state: FSMContext, callback_data: dict[str, str]):
        data = await state.get_data()
        if 'prev_list_id' in data and data['prev_list_id'] != query.message.message_id:
            await query.answer("Кнопка устарела :(")
            return

        page_num = data.get('curr_page_num', 0) + int(callback_data.get('delta', 0))
        await state.update_data(curr_page_num=page_num)
        await self.show_my_deadlines(query.from_user.id, state, page_num, query.message, update=False)

    async def query_deadline_act(self, query: types.CallbackQuery, state: FSMContext, callback_data: dict[str, str]):
        data = await state.get_data()
        if 'prev_list_id' in data and data['prev_list_id'] != query.message.message_id:
            await query.answer("Кнопка устарела :(")
            return

        if callback_data.get('act') == "DEL":
            itm_id = int(callback_data.get('id', 0))
            reply_kb = keyboards.inline_keyboard([
                [("Да", self.del_item_cb.new(id=itm_id, ans="Y")),
                 ("Нет", self.del_item_cb.new(id=itm_id, ans="N"))]
            ])
            async with Database() as db:
                title = await db.get_deadline_val(itm_id, "title")
                if title is None:
                    await query.answer("Такого дедлайна нет")
                    return
                await query.message.edit_text(f"\u26A0 Вы уверены, что хотите удалить дедлайн <b>\"{html.escape(title)}\"</b>?", reply_markup=reply_kb)
                await DeadlineStates.approve_delete.set()
        else:
            itm_id = int(callback_data.get('id', 0))
            async with Database() as db:
                done = await db.get_deadline_val(itm_id, "done")
                if done is None:
                    await query.answer("Такого дедлайна нет")
                    return
                await db.update_deadline(itm_id, done=not done)
                await query.answer("Состояние изменено!")
            await self.show_my_deadlines(query.from_user.id, state, message=query.message, update=True)

    async def query_approve_del(self, query: types.CallbackQuery, state: FSMContext, callback_data: dict[str, str]):
        if callback_data.get('ans') == "Y":
            async with Database() as db:
                await db.remove_deadline(int(callback_data.get('id', 0)))
            await query.answer("Удалено!")
        await state.reset_state(with_data=False)
        await self.show_my_deadlines(query.from_user.id, state, message=query.message, update=True)

    @staticmethod
    async def start_adding_deadline(message: types.Message):
        reply_kb = keyboards.reply_keyboard([["\u274C Отменить"]])
        await message.answer("\u270F Введите короткое имя для дедлайна, которое нужно записать. Названия дедлайнов могут быть одинаковыми, но лучше не путать самих себя :)", reply_markup=reply_kb)
        await DeadlineStates.deadline_title.set()

    @staticmethod
    async def deadline_title_received(message: types.Message, state: FSMContext):
        if len(message.text.strip()) > 32:
            await message.answer("\u26A0 Слишком длинное имя, используйте сокращения, пожалуйста")
            return
        await state.update_data(title=message.text.strip())
        await message.answer("\U0001F4C5 Теперь зададим дату дедлайна. Дату можно вводить почти в любом формате. Примеры ввода:\n\n"
                             "<b>* 12.03.2022 21:00</b>\n"
                             "<b>* 12 марта 2022</b> (если не указать время, то будет выбрано 00:00)\n"
                             "<b>* Послезавтра в 6:45 PM</b>")
        await DeadlineStates.deadline_date.set()

    @staticmethod
    async def deadline_date_received(message: types.Message, state: FSMContext):
        async with Database() as db:
            tz = await db.get_user_val(message.from_user.id, "timezone")
        text = message.text.strip()
        settings = {
            'DATE_ORDER': 'DMY',
            'PREFER_DATES_FROM': 'future'
        }
        if len(tz) == 5 and tz[0] in ['+', '-'] and tz[1:].isdigit():  # dateparser moment
            text = text + f" {tz}"
        else:
            settings['TIMEZONE'] = tz
        date: datetime = dateparser.parse(text, settings=settings)

        if date is None:
            await message.answer("\u26A0 Не можем распознать дату, попробуйте задать её в явном формате")
            return
        await state.update_data(date=date.replace(tzinfo=None))

        reply_kb = keyboards.reply_keyboard([
            ["За день", "За два дня"],
            ["За час", "За два часа", "За три часа"],
            ["\u27A1 Пропустить"]
        ])
        await message.answer("\u23F0 Отлично! Теперь нужно выбрать, за какое время до дедлайна нужно будет отправить уведомление.\n\n"
                             "Можно выбрать среди предложенных вариантов, а можно ввести самому в формате <b>\"За X минут/часов/дней/недель\"</b>. "
                             "Если пропустить этот этап, то напоминания о дедлайне не будет.",
                             reply_markup=reply_kb)
        await DeadlineStates.remind_delay.set()

    @staticmethod
    async def deadline_remind_received(message: types.Message, state: FSMContext):
        text = message.text.strip().lower().replace("за", "через")
        if "пропустить" not in text.lower():
            date: datetime = dateparser.parse(text, settings={
                'TIMEZONE': 'UTC',
                'DATE_ORDER': 'DMY',
                'PREFER_DATES_FROM': 'future'
            })
            if date is None:
                await message.answer("\u26A0 Не можем распознать ввод, попробуйте использовать предложенные варианты")
                return
            await state.update_data(remind_in=round(abs((date.replace(tzinfo=None) - datetime.utcnow()).total_seconds())))

        reply_kb = keyboards.reply_keyboard([
            ["Каждую неделю", "Каждые 2 недели", "Каждый месяц"],
            ["Каждый день", "Каждые два дня"],
            ["\u27A1 Пропустить"]
        ])
        await message.answer("\U0001F4DD Осталось выбрать, с каким промежутком нужно будет повторять этот дедлайн!\n\n"
                             "Можно выбрать среди предложенных вариантов, а можно ввести самому в формате <b>\"Каждые X дней/недель/месяцев\"</b> "
                             "Если пропустить этот этап, то после дедлайна или выполнения дела, оно удалится.",
                             reply_markup=reply_kb)
        await DeadlineStates.repeat_delay.set()

    async def deadline_repeat_received(self, message: types.Message, state: FSMContext):
        inplaces = {"каждую", "каждый", "каждые", "каждое", "каждая"}
        text = message.text.strip().lower()
        for inplace in inplaces:
            text = text.replace(inplace, "через")

        if "пропустить" not in text.lower():
            date: datetime = dateparser.parse(text, settings={
                'TIMEZONE': 'UTC',
                'DATE_ORDER': 'DMY',
                'PREFER_DATES_FROM': 'future'
            })
            if date is None:
                await message.answer("\u26A0 Не можем распознать ввод, попробуйте использовать предложенные варианты")
                return
            repeat_in = round(abs((date.replace(tzinfo=None) - datetime.utcnow()).total_seconds()))
            if repeat_in < 30:
                await message.answer("\u26A0 Не надо ломать меня :(")
                return
            await state.update_data(repeat_in=repeat_in)

        try:
            async with Database() as db:
                data = await state.get_data()
                await db.create_deadline(
                    message.from_user.id,
                    data['title'], data['date'],
                    data.get('repeat_in'), data.get('remind_in')
                )
        except Exception:
            return_txt = "\u2705 При добавлении дедлайна произошла ошибка :("
        else:
            return_txt = "\u2705 Новый дедлайн добавлен!"
        await state.finish()
        await state.reset_data()
        await start_registered(self.bot, message.from_user, return_txt)
