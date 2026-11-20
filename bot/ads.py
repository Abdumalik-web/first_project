"""Bot admin bo'lgan guruhlarga muntazam reklama joylash.

- Ikki xil reklama: «Farg'onadan Toshkentga» va «Toshkentdan Farg'onaga».
  Ular navbatma-navbat, har `interval` daqiqada bittadan joylanadi.
- Har yo'nalishning yangi reklamasidan oldin o'sha yo'nalishning eskisi o'chiriladi —
  guruhda har yo'nalishdan bittadan reklama turadi.
- Oxirgi reklamadan beri guruhda yangi xabar bo'lmasa, qayta joylanmaydi.
- Faqat bot admin bo'lgan guruhlarda.
- Tugma botga `?start=g<guruh>_<yo'nalish>` bilan olib boradi: yo'lovchi so'rovi
  yo'nalishi tanlangan holda boshlanadi.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .db import Database, now_iso
from .regions import FROM_TASHKENT, TO_TASHKENT

log = logging.getLogger(__name__)

DEFAULT_TEXTS = {
    TO_TASHKENT: (
        "🚕 Farg'onadan Toshkentga yuramiz!\n\n"
        "Farg'ona viloyatining barcha tumanlaridan Toshkentga har kuni qatnaymiz.\n\n"
        "✅ Sizga eng yaqin haydovchini topamiz\n"
        "✅ Uyingizdan olib ketamiz\n"
        "✅ 1 daqiqada joy band qiling\n\n"
        "👇 Pastdagi tugmani bosing"
    ),
    FROM_TASHKENT: (
        "🚕 Toshkentdan Farg'onaga yuramiz!\n\n"
        "Toshkentning istalgan tumanidan Farg'ona viloyatiga har kuni qatnaymiz.\n\n"
        "✅ Sizga eng yaqin haydovchini topamiz\n"
        "✅ Turgan joyingizdan olib ketamiz\n"
        "✅ 1 daqiqada joy band qiling\n\n"
        "👇 Pastdagi tugmani bosing"
    ),
}
DEFAULT_BUTTONS = {
    TO_TASHKENT: "🚕 Farg'ona ➜ Toshkent: joy band qilish",
    FROM_TASHKENT: "🚕 Toshkent ➜ Farg'ona: joy band qilish",
}
DEFAULT_INTERVAL_MIN = 10
MIN_INTERVAL_MIN = 5

# settings jadvalidagi kalitlar
K_ENABLED, K_INTERVAL = "ad_enabled", "ad_interval_min"


def k_text(direction: str) -> str:
    return f"ad_text_{direction.lower()}"


def k_button(direction: str) -> str:
    return f"ad_button_{direction.lower()}"


async def ad_settings(db: Database) -> dict:
    cfg = {
        "enabled": await db.get_setting(K_ENABLED, "1") == "1",
        "interval": int(await db.get_setting(K_INTERVAL, str(DEFAULT_INTERVAL_MIN))),
        "text": {},
        "button": {},
    }
    for d in (TO_TASHKENT, FROM_TASHKENT):
        cfg["text"][d] = await db.get_setting(k_text(d), DEFAULT_TEXTS[d])
        cfg["button"][d] = await db.get_setting(k_button(d), DEFAULT_BUTTONS[d])
    return cfg


def next_direction(last: str | None) -> str:
    return FROM_TASHKENT if last == TO_TASHKENT else TO_TASHKENT


class AdService:
    def __init__(self, bot: Bot, db: Database):
        self.bot = bot
        self.db = db

    async def is_admin_in(self, chat_id: int) -> bool:
        me = await self.bot.me()
        try:
            member = await self.bot.get_chat_member(chat_id, me.id)
        except TelegramAPIError as e:
            log.info("get_chat_member %s: %s", chat_id, e)
            return False
        return member.status in ("administrator", "creator")

    async def post(self, group, cfg: dict, direction: str) -> bool:
        """Bitta guruhga bitta yo'nalish reklamasini joylaydi. Muvaffaqiyatli bo'lsa True."""
        chat_id = group["id"]
        if not await self.is_admin_in(chat_id):
            await self.db.set_group_ad(chat_id, None, None, now_iso())
            return False
        me = await self.bot.me()
        url = f"https://t.me/{me.username}?start=g{abs(chat_id)}_{direction}"
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=cfg["button"][direction], url=url)
        ]])
        old_id = group["ad_msg_f2t"] if direction == TO_TASHKENT else group["ad_msg_t2f"]
        if old_id:
            try:
                await self.bot.delete_message(chat_id, old_id)
            except TelegramAPIError:
                pass  # allaqachon o'chirilgan yoki o'chirish huquqi yo'q
        try:
            msg = await self.bot.send_message(chat_id, cfg["text"][direction], reply_markup=kb,
                                              parse_mode=None)
        except TelegramAPIError as e:
            log.warning("reklama %s (%s): %s", group["title"], chat_id, e)
            await self.db.set_group_ad(chat_id, None, None, now_iso())
            return False
        await self.db.set_group_ad(chat_id, direction, msg.message_id, now_iso())
        log.info("Reklama joylandi (%s): %s", direction, group["title"])
        return True

    async def tick(self, force: bool = False) -> int:
        """force=True — hamma guruhga ikkala reklamani hozir joylaydi."""
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
            directions = [TO_TASHKENT, FROM_TASHKENT] if force else [next_direction(g["last_ad_dir"])]
            for d in directions:
                g = await self.db.fetchone("SELECT * FROM groups WHERE id=?", g["id"])
                if await self.post(g, cfg, d):
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
