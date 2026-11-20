"""Bot admin bo'lgan guruhlarga muntazam reklama joylash.

- Har `interval` daqiqada bir marta (standart 10).
- Yangi reklamadan oldin eskisi o'chiriladi — guruhda doim bitta reklama turadi.
- Oxirgi reklamadan beri guruhda yangi xabar bo'lmasa, qayta joylanmaydi.
- Faqat bot admin bo'lgan guruhlarda.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .db import Database, now_iso

log = logging.getLogger(__name__)

DEFAULT_TEXT = (
    "🚕 Farg'ona ⇄ Toshkent taksi\n\n"
    "Toshkentdan Farg'onaga va Farg'onadan Toshkentga har kuni yuramiz!\n\n"
    "✅ Sizga eng yaqin haydovchini topamiz\n"
    "✅ Uyingizdan olib ketamiz\n"
    "✅ 1 daqiqada joy band qiling\n\n"
    "👇 Pastdagi tugmani bosing"
)
DEFAULT_BUTTON = "🚕 Joy band qilish"
DEFAULT_INTERVAL_MIN = 10
MIN_INTERVAL_MIN = 5

# settings jadvalidagi kalitlar
K_ENABLED, K_INTERVAL, K_TEXT, K_BUTTON = "ad_enabled", "ad_interval_min", "ad_text", "ad_button"


async def ad_settings(db: Database) -> dict:
    return {
        "enabled": await db.get_setting(K_ENABLED, "1") == "1",
        "interval": int(await db.get_setting(K_INTERVAL, str(DEFAULT_INTERVAL_MIN))),
        "text": await db.get_setting(K_TEXT, DEFAULT_TEXT),
        "button": await db.get_setting(K_BUTTON, DEFAULT_BUTTON),
    }


class AdService:
    def __init__(self, bot: Bot, db: Database):
        self.bot = bot
        self.db = db
        self._me = None

    async def bot_username(self) -> str:
        if self._me is None:
            self._me = await self.bot.me()
        return self._me.username

    async def is_admin_in(self, chat_id: int) -> bool:
        me = await self.bot.me()
        try:
            member = await self.bot.get_chat_member(chat_id, me.id)
        except TelegramAPIError as e:
            log.info("get_chat_member %s: %s", chat_id, e)
            return False
        return member.status in ("administrator", "creator")

    async def post(self, group, cfg: dict) -> bool:
        """Bitta guruhga reklama joylaydi. Muvaffaqiyatli bo'lsa True."""
        chat_id = group["id"]
        if not await self.is_admin_in(chat_id):
            await self.db.set_group_ad(chat_id, None, now_iso())
            return False
        url = f"https://t.me/{await self.bot_username()}?start=g{abs(chat_id)}"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=cfg["button"], url=url)]])
        if group["last_ad_msg_id"]:
            try:
                await self.bot.delete_message(chat_id, group["last_ad_msg_id"])
            except TelegramAPIError:
                pass  # allaqachon o'chirilgan yoki o'chirish huquqi yo'q
        try:
            msg = await self.bot.send_message(chat_id, cfg["text"], reply_markup=kb, parse_mode=None)
        except TelegramAPIError as e:
            log.warning("reklama %s (%s): %s", group["title"], chat_id, e)
            await self.db.set_group_ad(chat_id, None, now_iso())
            return False
        await self.db.set_group_ad(chat_id, msg.message_id, now_iso())
        log.info("Reklama joylandi: %s", group["title"])
        return True

    async def tick(self, force: bool = False) -> int:
        cfg = await ad_settings(self.db)
        if not cfg["enabled"] and not force:
            return 0
        if force:
            groups = await self.db.fetchall("SELECT * FROM groups WHERE active=1")
        else:
            before = (datetime.now(timezone.utc) - timedelta(minutes=cfg["interval"])).isoformat(timespec="seconds")
            groups = await self.db.groups_due_for_ad(before)
        n = 0
        for g in groups:
            if await self.post(g, cfg):
                n += 1
            await asyncio.sleep(0.2)
        return n

    async def run_loop(self, every_sec: int = 60) -> None:
        while True:
            try:
                await self.tick()
            except Exception:  # noqa: BLE001
                log.exception("reklama tsikli xatosi")
            await asyncio.sleep(every_sec)
