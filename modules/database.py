import asyncpg

from datetime import datetime
from modules.local_config import cfg


class Database:
    def __init__(self):
        self.conn: asyncpg.Connection = ...

    async def connect(self):
        self.conn: asyncpg.Connection = await asyncpg.connect(
            host=cfg['Database']['host'],
            user=cfg['Database']['user'],
            database=cfg['Database']['name'],
            password=cfg['Database']['password']
        )

    async def create_user(self, user_id: int, lang_code: str, timezone: str):
        await self.conn.execute(
            "INSERT INTO users(user_id, registered, lang_code, timezone) VALUES ($1, $2, $3, $4) ON CONFLICT DO NOTHING",
            user_id, datetime.utcnow(), lang_code, timezone
        )

    async def get_user_val(self, user_id: int, column: str, default=None):
        try:
            res = await self.conn.fetchval(f"SELECT {column} FROM users WHERE user_id=$1", user_id)
            return res if res is not None else default
        except Exception:
            return default

    async def get_user(self, user_id: int):
        try:
            return dict(await self.conn.fetchrow(f"SELECT * FROM users WHERE user_id=$1", user_id))
        except Exception:
            return None

    async def set_user_val(self, user_id: int, column: str, value):
        await self.conn.execute(f"UPDATE users SET {column}=$2 WHERE user_id=$1", user_id, value)

    async def update_user(self, user_id: int, **kwargs):
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        # user_id = kwargs.pop('user_id')
        update_string = ', '.join(f"{k}=${i}" for i, k in enumerate(kwargs.keys(), 2) if isinstance(k, str))
        await self.conn.execute(f"UPDATE users SET {update_string} WHERE user_id=$1", *(user_id, *kwargs.values()))

    async def get_user_timezones(self) -> dict[int, str]:
        res = await self.conn.fetch("SELECT user_id, timezone FROM users")
        return {entry.get('user_id'): entry.get('timezone') for entry in res}

    async def create_deadline(self, user_id: int, title: str, deadline: datetime, repeat_in: int = None, remind_in: int = None):
        return await self.conn.fetchval(
            "INSERT INTO deadlines(user_id, title, deadline, repeat_in, remind_in) VALUES ($1, $2, $3, $4, $5) RETURNING deadline_id",
            user_id, title, deadline, repeat_in, remind_in
        )

    async def get_deadlines(self, user_id: int = None):
        if user_id is None:
            res = await self.conn.fetch("SELECT * FROM deadlines")
        else:
            res = await self.conn.fetch("SELECT * FROM deadlines WHERE user_id=$1", user_id)
        return [dict(entry) for entry in res]

    async def get_deadline_val(self, deadline_id: int, column: str, default=None):
        try:
            res = await self.conn.fetchval(f"SELECT {column} FROM deadlines WHERE deadline_id=$1", deadline_id)
            return res if res is not None else default
        except Exception:
            return default

    async def update_deadline(self, deadline_id: int, **kwargs):
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        update_string = ', '.join(f"{k}=${i}" for i, k in enumerate(kwargs.keys(), 2) if isinstance(k, str))
        await self.conn.execute(f"UPDATE deadlines SET {update_string} WHERE deadline_id=$1", *(deadline_id, *kwargs.values()))

    async def remove_deadline(self, deadline_id: int):
        await self.conn.execute(f"DELETE FROM deadlines WHERE deadline_id=$1", deadline_id)

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.conn.close()
