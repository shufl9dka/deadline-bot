import pytz
from datetime import datetime

from aiogram import types
from modules.database import Database


def resolve_timezone(tz_string: str):
    return datetime.strptime(tz_string, '%z').tzinfo if len(tz_string) == 5 and tz_string[0] in ['+', '-'] and tz_string[1:].isdigit() else pytz.timezone(tz_string)


async def check_message(_message: types.Message):
    return True, ''


async def get_user_timezone(user_id: int):
    async with Database() as db:
        return resolve_timezone(await db.get_user_val(user_id, 'timezone', default='UTC'))


def parse_date(dstring: str, tz=None):
    if '/' in dstring:
        result = dstring.split('/')
        if len(result) != 2 or any([not x.isdigit() for x in result]):
            return False
        result[0], result[1] = result[1], result[0]
    else:
        result = dstring.split('.')
        if len(result) != 2 or any([not x.isdigit() for x in result]):
            return False
    try:
        inp = datetime.strptime(result[0] + '.' + result[1], "%d.%m")
    except Exception:
        return False
    now = datetime.now(tz=tz)
    result.append(str(now.year + int((inp.month, inp.day) < (now.month, now.day))))
    try:
        return list(map(int, result))
    except Exception:
        return False
