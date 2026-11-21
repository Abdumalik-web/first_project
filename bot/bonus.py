"""Bonus ballar: haydovchi o'zi olib keta olmaydigan yo'lovchini botga uzatsa.

Ball faqat uzatilgan yo'lovchini **boshqa haydovchi qabul qilganda** beriladi
(soxta raqamlar bilan ball yig'ib bo'lmasligi uchun). Qabul qilingan yo'lovchi
keyin bekor qilinsa, ball qaytarib olinadi. Ballarni pulga admin almashtiradi.
"""
from __future__ import annotations

from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .db import Database

K_PER_SEAT = "bonus_per_seat"
K_INFO = "bonus_info"
DEFAULT_PER_SEAT = 10
DEFAULT_INFO = "Ballarni pulga aylantirish uchun admin bilan bog'laning."

HANDOVER_CB = "ho:start"


async def per_seat(db: Database) -> int:
    return int(await db.get_setting(K_PER_SEAT, str(DEFAULT_PER_SEAT)))


async def info_text(db: Database) -> str:
    return await db.get_setting(K_INFO, DEFAULT_INFO)


def handover_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📤 Yo'lovchi uzatish (bonus)", callback_data=HANDOVER_CB)
    ]])


async def full_trip_text(db: Database) -> str:
    """Haydovchi to'lganda: oq yo'l + bonus taklifi."""
    pts = await per_seat(db)
    return (
        "🎉 <b>Mashinangiz to'ldi — oq yo'l!</b> 🚗💨\n\n"
        "💰 <b>Qo'shimcha daromad imkoniyati:</b> sizga qo'ng'iroq qilgan, lekin endi olib keta "
        "olmaydigan yo'lovchilar bormi? Ularni botga uzating — qayerdan qayerga, necha kishi va "
        "telefon raqami. Bot ularni eng yaqin haydovchiga yuboradi.\n\n"
        f"Uzatgan yo'lovchingizni boshqa haydovchi olsa — <b>har bir kishi uchun {pts} ball</b> "
        "olasiz. Ballarni pulga aylantirish mumkin.\n\n"
        f"ℹ️ {escape(await info_text(db))}"
    )


async def explain_text(db: Database, uid: int) -> str:
    """«💰 Bonusim» ekrani."""
    pts = await per_seat(db)
    balance = await db.bonus_balance(uid)
    lines = [
        f"💰 <b>Bonus ballaringiz: {balance}</b>\n",
        "<b>Qanday ball yig'iladi?</b>",
        "Sizga qo'ng'iroq qilgan yo'lovchini o'zingiz olib keta olmasangiz (mashina to'lgan, "
        "boshqa yo'nalish, siz Toshkentda — u Farg'onada va h.k.), uni "
        "<b>«📤 Yo'lovchi uzatish»</b> orqali botga kiriting.",
        f"Bot uni eng yaqin haydovchiga yuboradi. Haydovchi olsa — <b>har bir kishi uchun {pts} ball</b>.",
        "Yo'lovchi keyin bekor qilinsa, ball qaytarib olinadi.\n",
        f"ℹ️ {escape(await info_text(db))}",
    ]
    history = await db.bonus_history(uid, 8)
    if history:
        lines.append("\n<b>Oxirgi harakatlar:</b>")
        names = {"referral": "yo'lovchi uzatildi", "revoke": "bekor qilindi",
                 "payout": "to'lab berildi", "manual": "admin"}
        for h in history:
            sign = "+" if h["points"] > 0 else ""
            what = names.get(h["reason"], h["reason"])
            ref = f" (so'rov #{h['request_id']})" if h["request_id"] else ""
            note = f" — {escape(h['note'])}" if h["note"] else ""
            lines.append(f"{h['created_at'][:10]}: {sign}{h['points']} — {what}{ref}{note}")
    return "\n".join(lines)
