"""Guruhlardagi xabarlarni o'qish va topilgan yo'lovchini haydovchilarga yuborish.

Bot guruhda hech narsa yozmaydi — faqat o'qiydi.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from html import escape

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ChatMemberUpdated, InlineKeyboardButton, InlineKeyboardMarkup, Message

from .. import referral
from ..db import Database
from ..group_parser import Lead, normalize, parse
from ..matching import rank_trips_for_lead
from ..regions import DIRECTIONS, date_options, fergana_name, fmt_date, slot_name, tashkent_name, today

log = logging.getLogger(__name__)
router = Router(name="group")
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

MAX_DRIVERS_PER_LEAD = 5
DUPLICATE_WINDOW_H = 6


def message_link(message: Message) -> str | None:
    chat = message.chat
    if chat.username:
        return f"https://t.me/{chat.username}/{message.message_id}"
    cid = str(chat.id)
    if cid.startswith("-100"):
        return f"https://t.me/c/{cid[4:]}/{message.message_id}"
    return None


def lead_text(lead: Lead, message: Message, trip_date: str | None, distance_km: float,
              covered: bool = True) -> str:
    route_t = tashkent_name(lead.tashkent_code) if lead.tashkent_code else "Toshkent"
    route = (f"{fergana_name(lead.fergana_code)} ➜ {route_t}" if lead.direction == "F2T"
             else f"{route_t} ➜ {fergana_name(lead.fergana_code)}")
    lines = [
        f"📢 <b>Guruhdan yo'lovchi</b> — {escape(message.chat.title or '')}",
        "",
        f"Yo'nalish: <b>{route}</b>",
        f"Sana: {fmt_date(trip_date) if trip_date else 'aytilmagan'}"
        + (f", {slot_name(lead.slot)}" if lead.slot else ""),
    ]
    if lead.seats:
        lines.append(f"Kishi soni: {lead.seats}")
    lines.append(f"📏 Sizdan taxminan {distance_km:g} km")
    if not covered:
        lines.append(f"ℹ️ {fergana_name(lead.fergana_code)} tumani e'loningizda yo'q, lekin siz eng yaqin haydovchisiz.")
    body = (message.text or message.caption or "")[:600]
    lines += ["", f"<i>«{escape(body)}»</i>", ""]

    u = message.from_user
    contacts = []
    if u and not u.is_bot:
        name = escape(u.full_name or "Yo'lovchi")
        contacts.append(f'👤 <a href="tg://user?id={u.id}">{name}</a>'
                        + (f" (@{escape(u.username)})" if u.username else ""))
    for name in lead.usernames:
        if not (u and u.username and u.username.lower() == name.lower()):
            contacts.append(f"👤 @{escape(name)}")
    for phone in lead.phones:
        contacts.append(f"📞 {phone}")
    lines += contacts or ["Kontakt yozilmagan — xabarni guruhda oching."]
    lines += ["", "Yo'lovchiga o'zingiz bog'laning."]
    return "\n".join(lines)


@router.chat_member()
async def member_changed(event: ChatMemberUpdated, db: Database, bot: Bot) -> None:
    """Majburiy guruhga kim qo'shildi / chiqdi: a'zolik va taklif ballari."""
    req = await referral.required_group(db)
    member = event.new_chat_member
    if req is None or event.chat.id != req or member.user.is_bot:
        return
    uid = member.user.id
    joined = member.status in referral.MEMBER_STATUSES or (
        member.status == "restricted" and bool(getattr(member, "is_member", False)))
    user = await db.get_user(uid)
    if not joined:
        if user:
            await db.set_group_ok(uid, False)
        return
    if user:
        await db.set_group_ok(uid, True)
        await referral.maybe_award(bot, db, uid)
    elif event.invite_link:
        # Guruhga kimningdir shaxsiy havolasi bilan kirdi, botda hali yo'q — keyin hisoblaymiz
        ref = await db.referrer_by_link(event.invite_link.invite_link)
        if ref and ref != uid:
            await db.add_pending_ref(uid, ref)


@router.my_chat_member()
async def bot_added_or_removed(event: ChatMemberUpdated, db: Database) -> None:
    if event.chat.type not in ("group", "supergroup"):
        return
    active = event.new_chat_member.status in ("member", "administrator")
    await db.upsert_group(event.chat.id, event.chat.title, event.chat.username, active)
    log.info("Guruh %s (%s): %s", event.chat.title, event.chat.id, "qo'shildi" if active else "chiqarildi")


@router.message(F.text | F.caption)
async def on_group_message(message: Message, db: Database, bot: Bot) -> None:
    u = message.from_user
    if u and u.is_bot and u.username != "GroupAnonymousBot":
        return
    # Guruh faolligi: reklama faqat yangi xabarlar bo'lganda qayta joylanadi
    await db.upsert_group(message.chat.id, message.chat.title, message.chat.username, True)
    await db.bump_group_activity(message.chat.id)

    raw = message.text or message.caption or ""
    lead = parse(raw)
    short = raw.replace("\n", " ")[:60]
    if lead is None:
        log.info("Guruh «%s»: xabar keldi, yo'lovchi e'loni emas: %s", message.chat.title, short)
        return

    user_id = u.id if u and not u.is_bot else None
    text_hash = hashlib.sha1(normalize(raw).encode()).hexdigest()
    since = (datetime.now(timezone.utc) - timedelta(hours=DUPLICATE_WINDOW_H)).isoformat(timespec="seconds")
    # Bir xil e'lon bir nechta guruhga tashlansa — haydovchiga bir marta boradi
    if await db.is_duplicate_lead(user_id, text_hash, since):
        log.info("Guruh «%s»: takroriy e'lon, o'tkazib yuborildi: %s", message.chat.title, short)
        return

    base = today()
    trip_date = lead.trip_date(base)
    dates = [trip_date] if trip_date else [iso for iso, _ in date_options(base)[:2]]
    lead_id = await db.add_lead(message.chat.id, message.message_id, user_id, text_hash,
                                lead.direction, lead.fergana_code, trip_date)
    if lead_id is None:
        return

    trips = {t["id"]: t for t in await db.active_trips_on(lead.direction, dates)}
    matches = rank_trips_for_lead(lead.direction, lead.fergana_code, lead.tashkent_code,
                                  lead.slot, lead.seats, trips.values())
    link = message_link(message)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔗 Xabarni guruhda ochish", url=link)
    ]]) if link else None

    sent_to: set[int] = set()
    for m in matches:
        trip = trips[m.trip_id]
        driver_id = trip["driver_id"]
        if driver_id in sent_to or driver_id == user_id:
            continue
        try:
            await bot.send_message(
                driver_id, lead_text(lead, message, trip_date or trip["trip_date"], m.distance_km, m.covered),
                reply_markup=kb, disable_web_page_preview=True,
            )
            sent_to.add(driver_id)
        except TelegramAPIError as e:
            log.warning("lead -> driver %s failed: %s", driver_id, e)
        if len(sent_to) >= MAX_DRIVERS_PER_LEAD:
            break
    await db.set_lead_sent(lead_id, len(sent_to))
    log.info("Guruh e'loni #%s (%s, %s): %d haydovchiga yuborildi",
             lead_id, DIRECTIONS[lead.direction], lead.fergana_code, len(sent_to))
