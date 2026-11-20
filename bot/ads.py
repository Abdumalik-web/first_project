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

from . import texts
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
K_ENABLED, K_INTERVAL, K_ACTIVITY = "ad_enabled", "ad_interval_min", "ad_require_activity"
# Haydovchi e'lonlarini guruhlarga joylash
K_TRIPS_ENABLED, K_TRIPS_INTERVAL = "trip_post_enabled", "trip_post_interval_min"
DEFAULT_TRIPS_INTERVAL_MIN = 60
# Telegram cheklovi: bitta guruhga daqiqasiga ~20 xabar. Har daqiqada shundan ko'p yubormaymiz.
MAX_TRIP_POSTS_PER_GROUP_PER_TICK = 12


def k_text(direction: str) -> str:
    return f"ad_text_{direction.lower()}"


def k_button(direction: str) -> str:
    return f"ad_button_{direction.lower()}"


async def ad_settings(db: Database) -> dict:
    cfg = {
        "enabled": await db.get_setting(K_ENABLED, "1") == "1",
        "interval": int(await db.get_setting(K_INTERVAL, str(DEFAULT_INTERVAL_MIN))),
        # Oxirgi reklamadan beri guruhda yangi xabar bo'lmasa, qayta joylamaslik
        "require_activity": await db.get_setting(K_ACTIVITY, "1") == "1",
        "text": {},
        "button": {},
    }
    for d in (TO_TASHKENT, FROM_TASHKENT):
        cfg["text"][d] = await db.get_setting(k_text(d), DEFAULT_TEXTS[d])
        cfg["button"][d] = await db.get_setting(k_button(d), DEFAULT_BUTTONS[d])
    return cfg


def _fmt_time(iso: str | None) -> str:
    if not iso:
        return "—"
    from .regions import TZ
    return datetime.fromisoformat(iso).astimezone(TZ).strftime("%d.%m %H:%M")


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

    async def group_status(self) -> list[str]:
        """Har bir guruh uchun reklama holati (admin panel uchun)."""
        cfg = await ad_settings(self.db)
        out = []
        for g in await self.db.fetchall("SELECT * FROM groups WHERE active=1 ORDER BY title"):
            admin = await self.is_admin_in(g["id"])
            last = _fmt_time(g["last_ad_at"]) if g["ad_msg_f2t"] or g["ad_msg_t2f"] else "hali joylanmagan"
            if not admin:
                why = "❌ bot admin emas — reklama joylanmaydi"
            elif cfg["require_activity"] and not g["msgs_since_ad"]:
                why = "⏸ guruhda yangi xabar yo'q — kimdir yozgach joylanadi"
            else:
                why = "✅ navbatdagi reklama vaqti kelganda joylanadi"
            out.append(
                f"• {g['title'] or g['id']}\n  {why}\n"
                f"  Oxirgi reklama: {last}; shundan beri xabarlar: {g['msgs_since_ad']}"
            )
        return out

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
            groups = await self.db.groups_due_for_ad(before, cfg["require_activity"])
        n = 0
        for g in groups:
            directions = [TO_TASHKENT, FROM_TASHKENT] if force else [next_direction(g["last_ad_dir"])]
            for d in directions:
                g = await self.db.fetchone("SELECT * FROM groups WHERE id=?", g["id"])
                if await self.post(g, cfg, d):
                    n += 1
                await asyncio.sleep(0.2)
        return n

    # --- haydovchi e'lonlari ---------------------------------------------------
    async def admin_groups(self) -> list:
        out = []
        for g in await self.db.fetchall("SELECT * FROM groups WHERE active=1"):
            if await self.is_admin_in(g["id"]):
                out.append(g)
        return out

    async def cleanup_trip_posts(self) -> int:
        """Yopilgan / to'lgan e'lonlarni guruhlardan o'chiradi."""
        n = 0
        for p in await self.db.stale_trip_posts():
            try:
                await self.bot.delete_message(p["chat_id"], p["message_id"])
            except TelegramAPIError:
                pass
            await self.db.delete_trip_post(p["trip_id"], p["chat_id"])
            n += 1
        return n

    async def tick_trips(self, force: bool = False) -> int:
        """Rozi bo'lgan haydovchilar e'lonlarini har `interval` daqiqada guruhlarga joylaydi.

        Har e'lonning guruhdagi eski posti o'chirilib, yangisi joylanadi.
        """
        await self.cleanup_trip_posts()
        enabled = await self.db.get_setting(K_TRIPS_ENABLED, "1") == "1"
        if not enabled and not force:
            return 0
        interval = int(await self.db.get_setting(K_TRIPS_INTERVAL, str(DEFAULT_TRIPS_INTERVAL_MIN)))
        trips = await self.db.trips_to_publish()
        if not trips:
            return 0
        groups = await self.admin_groups()
        me = await self.bot.me()
        before = (datetime.now(timezone.utc) - timedelta(minutes=interval)).isoformat(timespec="seconds")
        sent = 0
        for g in groups:
            per_group = 0
            for t in trips:
                if per_group >= MAX_TRIP_POSTS_PER_GROUP_PER_TICK:
                    break  # qolganlari keyingi daqiqada
                old = await self.db.get_trip_post(t["id"], g["id"])
                if old and old["posted_at"] > before and not force:
                    continue
                if old:
                    try:
                        await self.bot.delete_message(g["id"], old["message_id"])
                    except TelegramAPIError:
                        pass
                url = f"https://t.me/{me.username}?start=g{abs(g['id'])}_{t['direction']}"
                kb = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="🚕 Bot orqali joy band qilish", url=url)
                ]])
                try:
                    msg = await self.bot.send_message(g["id"], texts.trip_post_text(t), reply_markup=kb,
                                                      disable_web_page_preview=True)
                except TelegramAPIError as e:
                    log.warning("e'lon #%s -> %s: %s", t["id"], g["title"], e)
                    continue
                await self.db.save_trip_post(t["id"], g["id"], msg.message_id)
                sent += 1
                per_group += 1
                await asyncio.sleep(0.3)
        if sent:
            log.info("Haydovchi e'lonlari guruhlarga joylandi: %d ta", sent)
        return sent

    async def run_loop(self, every_sec: int = 60) -> None:
        while True:
            for job in (self.tick, self.tick_trips):
                try:
                    await job()
                except Exception:  # noqa: BLE001
                    log.exception("reklama tsikli xatosi (%s)", job.__name__)
            await asyncio.sleep(every_sec)
