from aiogram import types
from typing import Iterable


def reply_keyboard(layout: Iterable[Iterable[str]], location_idx=-1):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    for i, row in enumerate(layout):
        keyboard.row(*[types.KeyboardButton(text, request_location=i == location_idx) for text in row])
    return keyboard


def inline_keyboard(layout: Iterable):
    if not layout:
        return types.InlineKeyboardMarkup()
    keyboard = types.InlineKeyboardMarkup(row_width=max([len(lay) for lay in layout]))
    for row in layout:
        keyboard.row(*[types.InlineKeyboardButton(text, callback_data=data) for text, data in row])
    return keyboard


def dict_to_inline(layout: Iterable):
    if not layout:
        return types.InlineKeyboardMarkup()
    keyboard = types.InlineKeyboardMarkup(row_width=max([len(lay) for lay in layout]))
    for row in layout:
        keyboard.row(*[types.InlineKeyboardButton(**data) for data in row])
    return keyboard
