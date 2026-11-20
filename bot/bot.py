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
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

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
# A'zolar guruhga yozishdan oldin start bosishi shart bo'lgan boshqa botning tokeni (ixtiyoriy).
# Berilsa, o'sha botga start bosmaganlar guruhga yoza olmaydi.
REQUIRED_BOT_TOKEN = os.getenv("REQUIRED_BOT_TOKEN", "").strip().strip('"').strip("'").strip()
# "1" bo'lsa start bosish majburiy (guruhda /majburiy bilan o'zgartiriladi)
REQUIRE_START = os.getenv("REQUIRE_START", "1" if REQUIRED_BOT_TOKEN else "0") == "1"
# Shu botning o'ziga /start bosganlar ro'yxati (REQUIRED_BOT_TOKEN berilmaganda ishlatiladi)
USERS_FILE = os.getenv("USERS_FILE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.json"))
# Ogohlantirish xabari necha soniyadan keyin o'chsin
WARN_TTL = int(os.getenv("WARN_TTL", "10"))
# "Botga start bosing" xabari necha soniyadan keyin o'chsin
START_WARN_TTL = int(os.getenv("START_WARN_TTL", "60"))

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
    defaults = {"photos": DELETE_PHOTOS, "videos": DELETE_VIDEOS, "start": REQUIRE_START}
    return _settings.get(str(chat_id), {}).get(key, defaults[key])


def _load_users() -> set[int]:
    try:
        with open(USERS_FILE, encoding="utf-8") as f:
            return set(json.load(f))
    except (OSError, ValueError):
        return set()


_started_users: set[int] = _load_users()
# Boshqa botga start bosgani tasdiqlangan foydalanuvchilar: user_id -> tekshirilgan vaqt
_verified: dict[int, float] = {}
VERIFY_TTL = 24 * 3600  # tasdiq 24 soatdan keyin qayta tekshiriladi
_required_bot: Bot | None = None
# (chat_id, user_id) -> oxirgi ogohlantirish vaqti (spam bo'lmasligi uchun)
_last_start_warn: dict[tuple[int, int], float] = {}


def mark_started(user_id: int) -> None:
    if user_id in _started_users:
        return
    _started_users.add(user_id)
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(_started_users), f)
    except OSError as e:
        logging.warning("Foydalanuvchini saqlab bo'lmadi: %s", e)


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


_bg_tasks: set[asyncio.Task] = set()
# (chat_id, user_id) -> hali o'chirilmagan "start bosing" xabari
_start_warnings: dict[tuple[int, int], Message] = {}


async def _safe_delete(msg: Message) -> None:
    try:
        await msg.delete()
    except TelegramBadRequest:
        pass


async def _delete_later(msg: Message, delay: int, key: tuple[int, int] | None = None) -> None:
    await asyncio.sleep(delay)
    if key is not None:
        if _start_warnings.get(key) is not msg:
            return  # allaqachon o'chirilgan
        _start_warnings.pop(key, None)
    await _safe_delete(msg)


def schedule_delete(msg: Message, delay: int, key: tuple[int, int] | None = None) -> None:
    # Vazifaga havola saqlanadi, aks holda Python uni vaqtidan oldin yo'q qilishi mumkin
    task = asyncio.create_task(_delete_later(msg, delay, key))
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)


@dp.message(Command("start"), F.chat.type == ChatType.PRIVATE)
async def start(msg: Message) -> None:
    if msg.from_user:
        mark_started(msg.from_user.id)
    await msg.answer(
        "Salom! Guruh egalari uchun: meni guruhga qo'shing va <b>admin</b> qiling "
        "(\"Xabarlarni o'chirish\" huquqi bilan). Men reklama havolalari, "
        "Instagram/YouTube linklari va forward qilingan reklamalarni avtomatik o'chiraman."
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


@dp.message(Command("majburiy"), GROUPS)
async def toggle_require_start(msg: Message, bot: Bot) -> None:
    if not msg.from_user or not await is_admin(bot, msg.chat.id, msg.from_user.id):
        return
    new = not chat_setting(msg.chat.id, "start")
    set_chat_setting(msg.chat.id, "start", new)
    await msg.answer("Yozishdan oldin botga /start bosish: " + ("✅ majburiy" if new else "❌ majburiy emas"))


@dp.message(Command("sozlamalar"), GROUPS)
async def show_settings(msg: Message) -> None:
    req = "✅ majburiy" if chat_setting(msg.chat.id, "start") else "❌ majburiy emas"
    await msg.answer(
        f"Botga /start bosish: {req}  (/majburiy)\n"
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

    user = msg.from_user
    if (
        user
        and not user.is_bot
        and chat_setting(msg.chat.id, "start")
        and not await has_started(user.id)
        and not await is_admin(bot, msg.chat.id, user.id)
    ):
        await _require_start(msg, bot)
        return

    # A'zo start bosib yozdi: unga chiqqan "start bosing" xabarini darhol o'chiramiz
    if user:
        old = _start_warnings.pop((msg.chat.id, user.id), None)
        if old is not None:
            await _safe_delete(old)

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
    schedule_delete(warn, WARN_TTL)


async def has_started(user_id: int) -> bool:
    """Foydalanuvchi kerakli botga start bosganmi?"""
    if _required_bot is None:
        return user_id in _started_users

    now = asyncio.get_running_loop().time()
    if now - _verified.get(user_id, -1e12) < VERIFY_TTL:
        return True
    try:
        # Bot faqat start bosgan foydalanuvchiga "yozmoqda..." ko'rsata oladi.
        await _required_bot.send_chat_action(user_id, "typing")
    except (TelegramForbiddenError, TelegramBadRequest):
        return False
    except Exception as e:  # tarmoq xatosi: a'zoni bekorga bloklamaymiz
        logging.warning("Start tekshiruvi ishlamadi: %s", e)
        return True
    _verified[user_id] = now
    return True


async def _require_start(msg: Message, bot: Bot) -> None:
    """Botga /start bosmagan a'zoning xabarini o'chirib, start tugmasini ko'rsatadi."""
    try:
        await msg.delete()
    except TelegramBadRequest as e:
        logging.warning("O'chirib bo'lmadi (bot adminmi?): %s", e)
        return

    key = (msg.chat.id, msg.from_user.id)
    now = asyncio.get_running_loop().time()
    if now - _last_start_warn.get(key, -1e9) < 60:
        return  # bir daqiqada bir martadan ko'p ogohlantirmaymiz
    _last_start_warn[key] = now

    me = await (_required_bot or bot).me()
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="▶️ Botga start bosish", url=f"https://t.me/{me.username}?start=guruh")
    ]])
    warn = await bot.send_message(
        msg.chat.id,
        f"👋 {msg.from_user.mention_html()}, guruhga yozish uchun avval botga "
        f"<b>start</b> bosing, keyin xabaringizni qayta yuboring.",
        reply_markup=kb,
    )
    _start_warnings[key] = warn
    schedule_delete(warn, START_WARN_TTL, key)


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
    global _required_bot
    if REQUIRED_BOT_TOKEN:
        _required_bot = Bot(REQUIRED_BOT_TOKEN)
        req = await _required_bot.me()
        logging.info("Guruhga yozish uchun start bosilishi kerak bo'lgan bot: @%s", req.username)
    me = await bot.get_me()
    logging.info("Bot ishga tushdi: @%s  (to'xtatish uchun Ctrl+C)", me.username)
    await dp.start_polling(bot, allowed_updates=["message", "edited_message"])


if __name__ == "__main__":
    asyncio.run(main())
