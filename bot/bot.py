"""Guruhdagi reklamalarni avtomatik o'chiradigan Telegram bot.

O'chiradi:
  - Telegram guruh/kanal havolalari (t.me, telegram.me, @username)
  - Instagram, YouTube, TikTok va boshqa havolalar
  - Kanallardan forward qilingan xabarlar
  - "Guruhga qo'shildi" / "guruhdan chiqdi" tizim xabarlari
  - (ixtiyoriy) rasm va video xabarlar  (adminlar: /rasm, /video, /sozlamalar)

Adminlar xabarlari tegilmaydi.
"""

import asyncio
import json
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
# "1" bo'lsa oddiy a'zolar yuborgan rasmlar ham o'chiriladi
DELETE_PHOTOS = os.getenv("DELETE_PHOTOS", "0") == "1"
# Guruhlar sozlamalari saqlanadigan fayl
SETTINGS_FILE = os.getenv("SETTINGS_FILE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json"))
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


def _load_settings() -> dict:
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


_settings: dict = _load_settings()


def chat_setting(chat_id: int, key: str) -> bool:
    defaults = {"photos": DELETE_PHOTOS, "videos": DELETE_VIDEOS}
    return _settings.get(str(chat_id), {}).get(key, defaults[key])


def set_chat_setting(chat_id: int, key: str, value: bool) -> None:
    _settings.setdefault(str(chat_id), {})[key] = value
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(_settings, f, indent=2)
    except OSError as e:
        logging.warning("Sozlamani saqlab bo'lmadi: %s", e)


def _is_blocked_url(url: str) -> bool:
    if BLOCK_ALL_LINKS:
        return True
    u = url.lower()
    return any(d in u for d in BLOCKED_DOMAINS)


def find_violation(msg: Message, delete_photos: bool = False, delete_videos: bool = False) -> str | None:
    """Xabarda reklama bo'lsa, sababini qaytaradi."""
    # Kanaldan / boshqa chatdan forward
    if msg.forward_origin is not None:
        return "forward"

    if delete_videos and (msg.video or msg.video_note or msg.animation):
        return "video"
    if delete_photos and (msg.photo or (msg.document and (msg.document.mime_type or "").startswith("image/"))):
        return "rasm"

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


GROUPS = F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP})


def _on_off(v: bool) -> str:
    return "✅ o'chiriladi" if v else "❌ o'chirilmaydi"


async def _toggle(msg: Message, bot: Bot, key: str, label: str) -> None:
    if not msg.from_user or not await is_admin(bot, msg.chat.id, msg.from_user.id):
        return
    new = not chat_setting(msg.chat.id, key)
    set_chat_setting(msg.chat.id, key, new)
    await msg.answer(f"{label}: {_on_off(new)}")


@dp.message(Command("rasm"), GROUPS)
async def toggle_photos(msg: Message, bot: Bot) -> None:
    await _toggle(msg, bot, "photos", "Rasmlar")


@dp.message(Command("video"), GROUPS)
async def toggle_videos(msg: Message, bot: Bot) -> None:
    await _toggle(msg, bot, "videos", "Videolar")


@dp.message(Command("sozlamalar"), GROUPS)
async def show_settings(msg: Message) -> None:
    await msg.answer(
        "Havolalar va reklama: ✅ o'chiriladi\n"
        f"Rasmlar: {_on_off(chat_setting(msg.chat.id, 'photos'))}  (/rasm)\n"
        f"Videolar: {_on_off(chat_setting(msg.chat.id, 'videos'))}  (/video)\n"
        "Buyruqlar faqat adminlar uchun ishlaydi."
    )


@dp.message(GROUPS, F.new_chat_members | F.left_chat_member)
async def clean_service(msg: Message) -> None:
    """"Guruhga qo'shildi" / "guruhdan chiqdi" tizim xabarlarini o'chiradi."""
    try:
        await msg.delete()
    except TelegramBadRequest as e:
        logging.warning("Tizim xabarini o'chirib bo'lmadi (bot adminmi?): %s", e)


@dp.message(GROUPS)
@dp.edited_message(GROUPS)
async def moderate(msg: Message, bot: Bot) -> None:
    # Guruhning o'zi nomidan (anonim admin) yoki bog'langan kanaldan kelgan xabarlar
    if msg.sender_chat and msg.sender_chat.id == msg.chat.id:
        return
    if msg.is_automatic_forward:
        return

    reason = find_violation(
        msg,
        delete_photos=chat_setting(msg.chat.id, "photos"),
        delete_videos=chat_setting(msg.chat.id, "videos"),
    )
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
    token = BOT_TOKEN
    if not token:
        import sys
        from getpass import getpass

        if not sys.stdin.isatty():
            raise SystemExit("BOT_TOKEN o'rnatilmagan (serverda uni muhit o'zgaruvchisi qilib bering).")

        # Token ekranda ko'rinmaydi (skrinshotda chiqib qolmasligi uchun)
        token = getpass("Bot tokenini kiriting (yozganingiz ko'rinmaydi) va Enter bosing: ")
    token = token.strip().strip('"').strip("'").strip()
    if not token:
        raise SystemExit("Token kiritilmadi.")
    from aiogram.client.default import DefaultBotProperties

    bot = Bot(token, default=DefaultBotProperties(parse_mode="HTML"))
    me = await bot.get_me()
    print(f"Bot ishga tushdi: @{me.username}  (to'xtatish uchun Ctrl+C)")
    await dp.start_polling(bot, allowed_updates=["message", "edited_message"])


if __name__ == "__main__":
    asyncio.run(main())
