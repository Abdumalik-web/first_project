"""Taklif (referal) havolalari va majburiy guruh a'zoligi.

- Har bir foydalanuvchiga shaxsiy havola: botga (t.me/<bot>?start=r<id>) va guruhga
  (bot yaratgan shaxsiy taklif havolasi).
- Shu havola orqali kelgan **yangi** odam botga ham, guruhga ham qo'shilgach,
  taklif qilganga ball yoziladi (standart 5).
- Majburiy guruh belgilangan bo'lsa, guruhga qo'shilmagan odam botdan foydalana olmaydi.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from html import escape
from urllib.parse import quote

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from . import texts
from .db import Database

log = logging.getLogger(__name__)

K_REQUIRED_GROUP = "required_group_id"
K_REF_POINTS = "ref_points"
DEFAULT_REF_POINTS = 5
RECHECK_HOURS = 6
MEMBER_STATUSES = {"member", "administrator", "creator"}


async def required_group(db: Database) -> int | None:
    v = await db.get_setting(K_REQUIRED_GROUP, "")
    return int(v) if v.lstrip("-").isdigit() else None


async def ref_points(db: Database) -> int:
    return int(await db.get_setting(K_REF_POINTS, str(DEFAULT_REF_POINTS)))


async def group_url(db: Database) -> str:
    return await db.get_setting(texts.GROUP_LINK_KEY, texts.DEFAULT_GROUP_LINK)


async def is_member(bot: Bot, chat_id: int, uid: int) -> bool | None:
    """True/False — a'zomi; None — tekshirib bo'lmadi (bot guruhda yo'q va h.k.)."""
    try:
        m = await bot.get_chat_member(chat_id, uid)
    except TelegramAPIError as e:
        log.warning("a'zolikni tekshirib bo'lmadi (%s, %s): %s", chat_id, uid, e)
        return None
    if m.status in MEMBER_STATUSES:
        return True
    return m.status == "restricted" and bool(getattr(m, "is_member", False))


async def check_member(bot: Bot, db: Database, uid: int, force: bool = False) -> bool:
    """Majburiy guruh a'zoligini tekshiradi (natija bir necha soat keshlanadi).

    Guruh belgilanmagan yoki tekshirib bo'lmasa — True (hech kimni qulflab qo'ymaslik uchun).
    """
    chat_id = await required_group(db)
    if chat_id is None:
        return True
    user = await db.get_user(uid)
    if user and user["group_ok"] and not force and user["group_checked_at"]:
        checked = datetime.fromisoformat(user["group_checked_at"])
        if datetime.now(timezone.utc) - checked < timedelta(hours=RECHECK_HOURS):
            return True
    ok = await is_member(bot, chat_id, uid)
    if ok is None:
        return True
    if user:
        await db.set_group_ok(uid, ok)
    return ok


async def maybe_award(bot: Bot, db: Database, uid: int) -> bool:
    """Taklif qilingan odam botda va guruhda bo'lsa — taklif qilganga bir marta ball."""
    user = await db.get_user(uid)
    if not user or not user["referrer_id"] or user["ref_awarded"]:
        return False
    if await required_group(db) is not None and not user["group_ok"]:
        return False
    if not await db.mark_ref_awarded(uid):
        return False
    pts = await ref_points(db)
    ref = user["referrer_id"]
    await db.add_bonus(ref, pts, "invite", note=user["full_name"] or str(uid))
    balance = await db.bonus_balance(ref)
    try:
        await bot.send_message(
            ref,
            f"👥 Siz taklif qilgan <b>{escape(user['full_name'] or 'foydalanuvchi')}</b> botga va "
            f"guruhga qo'shildi!\n💰 <b>+{pts} ball</b>. Jami: <b>{balance} ball</b>.",
        )
    except TelegramAPIError:
        pass
    return True


async def personal_group_link(bot: Bot, db: Database, uid: int) -> str | None:
    """Foydalanuvchining shaxsiy guruh taklif havolasi (bot admin va «Invite users» huquqi kerak)."""
    chat_id = await required_group(db)
    if chat_id is None:
        return None
    link = await db.get_ref_link(uid, chat_id)
    if link:
        return link
    try:
        inv = await bot.create_chat_invite_link(chat_id, name=f"ref {uid}"[:32])
    except TelegramAPIError as e:
        log.info("shaxsiy taklif havolasini yaratib bo'lmadi: %s", e)
        return None
    await db.save_ref_link(uid, chat_id, inv.invite_link)
    return inv.invite_link


def gate_kb(url: str, args: str = "") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Guruhga qo'shilish", url=url)],
        [InlineKeyboardButton(text="✅ Qo'shildim", callback_data=f"gate:{args}"[:64])],
    ])


async def gate_text(db: Database) -> str:
    return (
        "👋 Botdan foydalanish uchun avval <b>guruhimizga qo'shiling</b>.\n\n"
        "Guruhda har kuni Farg'ona ⇄ Toshkent haydovchilari va yo'lovchilari e'lonlari chiqadi.\n\n"
        "1️⃣ «👥 Guruhga qo'shilish» ni bosing va guruhga kiring\n"
        "2️⃣ Keyin shu yerga qaytib «✅ Qo'shildim» ni bosing"
    )


async def invite_text(bot: Bot, db: Database, uid: int) -> tuple[str, InlineKeyboardMarkup]:
    """«👥 Do'stlarni taklif qilish» ekrani."""
    me = await bot.me()
    bot_link = f"https://t.me/{me.username}?start=r{uid}"
    grp = await personal_group_link(bot, db, uid) or await group_url(db)
    pts = await ref_points(db)
    invited, awarded = await db.referral_stats(uid)
    text = (
        "👥 <b>Do'stlaringizni taklif qiling va ball yig'ing!</b>\n\n"
        f"Sizning havolangiz orqali qo'shilgan har bir yangi odam uchun — <b>{pts} ball</b> "
        "(u botga ham, guruhga ham qo'shilgach).\n\n"
        f"🤖 Botga shaxsiy havolangiz:\n{bot_link}\n\n"
        f"👥 Guruhga havola:\n{escape(grp)}\n\n"
        f"📊 Siz taklif qilganlar: <b>{invited}</b>, shundan ball berilgani: <b>{awarded}</b>\n"
        f"💰 Balansingiz: <b>{await db.bonus_balance(uid)} ball</b>"
    )
    share = ("https://t.me/share/url?url=" + quote(bot_link) + "&text="
             + quote("🚕 Farg'ona ⇄ Toshkent taksi boti — eng yaqin haydovchi va yo'lovchini topadi!"))
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📤 Do'stlarga ulashish", url=share)]])
    return text, kb
