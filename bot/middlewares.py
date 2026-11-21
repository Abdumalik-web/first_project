from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from . import referral
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
            elif isinstance(event, Message) and event.chat.type == "private":
                await event.answer("🚫 Siz botdan foydalanishdan bloklangansiz.")
            return None
        return await handler(event, data)


class GroupGateMiddleware(BaseMiddleware):
    """Majburiy guruhga qo'shilmagan foydalanuvchi botdan foydalana olmaydi.

    /start va «✅ Qo'shildim» tugmasi o'tkaziladi (ular o'zi tekshiradi). Adminlar tekshirilmaydi.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        if isinstance(event, Message):
            chat = event.chat
            passthrough = (event.text or "").startswith("/start")
        elif isinstance(event, CallbackQuery):
            chat = event.message.chat if event.message else None
            passthrough = (event.data or "").startswith("gate:")
        else:
            return await handler(event, data)
        if (not user or not chat or chat.type != "private" or passthrough
                or user.id in data["config"].admin_ids):
            return await handler(event, data)
        db: Database = data["db"]
        bot = data["bot"]
        if await referral.check_member(bot, db, user.id):
            return await handler(event, data)
        kb = referral.gate_kb(await referral.group_url(db))
        if isinstance(event, CallbackQuery):
            await event.answer("Avval guruhga qo'shiling.", show_alert=True)
            await bot.send_message(user.id, await referral.gate_text(db), reply_markup=kb)
        else:
            await event.answer(await referral.gate_text(db), reply_markup=kb)
        return None
