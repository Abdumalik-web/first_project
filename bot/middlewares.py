from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from .db import Database


class BanMiddleware(BaseMiddleware):
    """Bloklangan foydalanuvchilarning xabar va tugmalariga javob bermaydi."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        db: Database = data["db"]
        if user and user.id not in data["config"].admin_ids and await db.is_banned(user.id):
            if isinstance(event, CallbackQuery):
                await event.answer("Siz bloklangansiz.", show_alert=True)
            elif isinstance(event, Message):
                await event.answer("🚫 Siz botdan foydalanishdan bloklangansiz.")
            return None
        return await handler(event, data)
