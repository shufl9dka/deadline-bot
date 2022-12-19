from aiogram.dispatcher.filters.state import State, StatesGroup


class SettingStates(StatesGroup):
    ask_timezone = State()
    approve_timezone = State()


class DeadlineStates(StatesGroup):
    deadline_title = State()
    deadline_date = State()
    remind_delay = State()
    repeat_delay = State()

    approve_delete = State()
