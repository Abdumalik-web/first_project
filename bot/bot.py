"""Guruhdagi reklamalarni avtomatik o'chiradigan Telegram bot.

O'chiradi:
  - Telegram guruh/kanal havolalari (t.me, telegram.me, @username)
  - Instagram, YouTube, TikTok va boshqa havolalar
  - Kanallardan forward qilingan xabarlar
  - (ixtiyoriy) video xabarlar

Adminlar xabarlari tegilmaydi.
"""

import asyncio
import logging
import os
import re

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatMemberStatus, ChatType, MessageEntityType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import Message

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
# "1" bo'lsa barcha havolalar o'chiriladi, "0" bo'lsa faqat BLOCKED_DOMAINS dagilar
BLOCK_ALL_LINKS = os.getenv("BLOCK_ALL_LINKS", "1") == "1"
# "1" bo'lsa oddiy a'zolar yuborgan videolar ham o'chiriladi
DELETE_VIDEOS = os.getenv("DELETE_VIDEOS", "0") == "1"
# Ogohlantirish xabari necha soniyadan keyin o'chsin
WARN_TTL = int(os.getenv("WARN_TTL", "10"))

BLOCKED_DOMAINS = (
    "t.me", "telegram.me", "telegram.dog",
    "instagram.com", "instagr.am",
    "youtube.com", "youtu.be",
    "tiktok.com", "facebook.com", "fb.watch",
    "vk.com", "x.com", "twitter.com",
)

URL_RE = re.compile(
    r"(https?://\S+|www\.\S+|\b[\w-]+\.(?:com|me|ru|uz|org|net|io|be|am|dog|tv)\b\S*)",
    re.IGNORECASE,
)

dp = Dispatcher()


def _is_blocked_url(url: str) -> bool:
    if BLOCK_ALL_LINKS:
        return True
    u = url.lower()
    return any(d in u for d in BLOCKED_DOMAINS)


def find_violation(msg: Message) -> str | None:
    """Xabarda reklama bo'lsa, sababini qaytaradi."""
    # Kanaldan / boshqa chatdan forward
    if msg.forward_origin is not None:
        return "forward"

    if DELETE_VIDEOS and (msg.video or msg.video_note or msg.animation):
        return "video"

    text = msg.text or msg.caption or ""
    entities = msg.entities or msg.caption_entities or []

    for ent in entities:
        if ent.type == MessageEntityType.TEXT_LINK and _is_blocked_url(ent.url or ""):
            return "havola"
        if ent.type == MessageEntityType.URL:
            if _is_blocked_url(ent.extract_from(text)):
                return "havola"
        if ent.type == MessageEntityType.MENTION:
            # @kanal_nomi ko'rinishidagi reklama
            return "@username"

    # Telegram entity sifatida tanimagan yashirin havolalar (masalan "t . me/...")
    compact = re.sub(r"\s+", "", text.lower())
    if any(d + "/" in compact for d in ("t.me", "telegram.me")):
        return "havola"
    for m in URL_RE.findall(text):
        if _is_blocked_url(m):
            return "havola"
    return None


async def is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    member = await bot.get_chat_member(chat_id, user_id)
    return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR)


async def _delete_later(msg: Message, delay: int) -> None:
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except TelegramBadRequest:
        pass


@dp.message(Command("start"))
async def start(msg: Message) -> None:
    await msg.answer(
        "Salom! Meni guruhga qo'shing va <b>admin</b> qiling "
        "(\"Xabarlarni o'chirish\" huquqi bilan).\n"
        "Men reklama havolalari, Instagram/YouTube linklari va "
        "forward qilingan reklamalarni avtomatik o'chiraman."
    )


@dp.message(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
@dp.edited_message(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def moderate(msg: Message, bot: Bot) -> None:
    # Guruhning o'zi nomidan (anonim admin) yoki bog'langan kanaldan kelgan xabarlar
    if msg.sender_chat and msg.sender_chat.id == msg.chat.id:
        return
    if msg.is_automatic_forward:
        return

    reason = find_violation(msg)
    if not reason:
        return

    if msg.from_user and await is_admin(bot, msg.chat.id, msg.from_user.id):
        return

    try:
        await msg.delete()
    except TelegramBadRequest as e:
        logging.warning("O'chirib bo'lmadi (bot adminmi?): %s", e)
        return

    name = msg.from_user.mention_html() if msg.from_user else "Foydalanuvchi"
    warn = await bot.send_message(
        msg.chat.id, f"⚠️ {name}, guruhda reklama ({reason}) taqiqlangan!"
    )
    asyncio.create_task(_delete_later(warn, WARN_TTL))


async def main() -> None:
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN muhit o'zgaruvchisini o'rnating (.env.example ga qarang)")
    from aiogram.client.default import DefaultBotProperties

    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    await dp.start_polling(bot, allowed_updates=["message", "edited_message"])


if __name__ == "__main__":
    asyncio.run(main())
