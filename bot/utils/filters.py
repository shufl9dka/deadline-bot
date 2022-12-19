from aiogram.types import Message, ChatType
from aiogram.dispatcher.filters import BoundFilter

from modules import local_config
from modules.database import Database


class AdminFilter(BoundFilter):
    key = 'is_admin'

    def __init__(self, is_admin: bool):
        self.is_admin = is_admin

    async def check(self, obj: Message) -> bool:
        return (obj.from_user.id in local_config.admin_ids) == self.is_admin


class PrivateFilter(BoundFilter):
    key = 'is_private'

    def __init__(self, is_private: bool):
        self.is_private = is_private

    async def check(self, obj: Message) -> bool:
        return (obj.chat.type == ChatType.PRIVATE) == self.is_private


class RegisteredFilter(BoundFilter):
    key = 'user_registered'

    def __init__(self, user_registered: bool):
        self.user_registered = user_registered

    async def check(self, obj: Message) -> bool:
        async with Database() as db:
            return (await db.get_user_val(obj.chat.id, 'user_id') is not None) == self.user_registered
