"""Admin panel: statistika, e'lonlar, xabar tarqatish, bloklash.

Faqat .env dagi ADMIN_IDS ro'yxatidagi foydalanuvchilar uchun.
"""
from __future__ import annotations

import asyncio
from html import escape
from datetime import datetime, timezone

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter
from aiogram.filters import Command, CommandObject, Filter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    TelegramObject,
)

from .. import texts
from ..ads import K_ENABLED as AD_ENABLED, K_INTERVAL as AD_INTERVAL
from ..ads import MIN_INTERVAL_MIN, AdService, ad_settings, k_button, k_text
from ..config import Config
from ..db import Database
from ..keyboards import main_menu
from ..group_parser import parse as parse_group
from ..matching import rank_trips_for_lead
from ..regions import DIRECTIONS, date_options, fergana_name, fmt_date, slot_name, today
from ..service import MatchService

router = Router(name="admin")


class IsAdmin(Filter):
    async def __call__(self, event: TelegramObject, config: Config) -> bool:
        user = getattr(event, "from_user", None)
        return bool(user and user.id in config.admin_ids)


router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


class Broadcast(StatesGroup):
    text = State()
    confirm = State()


def admin_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardButton
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [b(text="📊 Statistika", callback_data="adm:stats")],
            [b(text="🚗 Faol e'lonlar", callback_data="adm:trips"),
             b(text="🧍 Kutayotgan so'rovlar", callback_data="adm:reqs")],
            [b(text="👥 Guruhlar", callback_data="adm:groups"),
             b(text="📣 Guruh reklamasi", callback_data="adm:ads")],
            [b(text="📢 Hammaga xabar yuborish", callback_data="adm:bc")],
            [b(text="🚫 Bloklash bo'yicha yordam", callback_data="adm:banhelp")],
        ]
    )


ADMIN_HELP = (
    "🛠 <b>Admin panel</b>\n\n"
    "Buyruqlar:\n"
    "/admin — shu menyu\n"
    "/user <i>id, @username, ism yoki telefon</i> — foydalanuvchini qidirish\n"
    "/ban <i>id</i> — bloklash (faol e'lon va so'rovlari bekor qilinadi)\n"
    "/unban <i>id</i> — blokdan chiqarish\n"
    "/del_trip <i>raqam</i> — e'lonni o'chirish\n"
    "/del_req <i>raqam</i> — so'rovni o'chirish\n"
    "/tekshir <i>matn</i> — guruh xabarini bot qanday tushunishini ko'rish"
)


@router.message(Command("admin"))
async def admin_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(ADMIN_HELP, reply_markup=admin_kb())


async def _send_chunks(message: Message, lines: list[str], empty: str) -> None:
    if not lines:
        await message.answer(empty)
        return
    chunk = ""
    for line in lines:
        if len(chunk) + len(line) > 3800:
            await message.answer(chunk)
            chunk = ""
        chunk += line + "\n\n"
    if chunk:
        await message.answer(chunk)


@router.callback_query(F.data == "adm:stats")
async def stats(cb: CallbackQuery, db: Database) -> None:
    s = await db.stats(datetime.now(timezone.utc).date().isoformat())
    await cb.message.answer(
        "📊 <b>Statistika</b>\n\n"
        f"👤 Foydalanuvchilar: <b>{s['users']}</b> (bloklangan: {s['banned']})\n"
        f"🚗 Haydovchilar: <b>{s['drivers']}</b>\n"
        f"🧍 Yo'lovchilar: <b>{s['passengers']}</b>\n\n"
        f"Faol e'lonlar: <b>{s['active_trips']}</b>\n"
        f"Haydovchi kutayotgan so'rovlar: <b>{s['searching']}</b>\n"
        f"Jami moslashuvlar: <b>{s['matched_total']}</b>\n\n"
        f"<b>Bugun:</b> {s['trips_today']} ta e'lon, {s['requests_today']} ta so'rov, "
        f"{s['matched_today']} ta moslashuv"
    )
    await cb.answer()


@router.callback_query(F.data == "adm:trips")
async def list_trips(cb: CallbackQuery, db: Database) -> None:
    lines = []
    for t in await db.all_active_trips():
        districts = ", ".join(fergana_name(c) for c in t["districts"].split(","))
        lines.append(
            f"🚗 <b>#{t['id']}</b> {DIRECTIONS[t['direction']]}\n"
            f"{fmt_date(t['trip_date'])}, {slot_name(t['slot'])}\n"
            f"Tumanlar: {districts}\n"
            f"O'rin: {t['seats_free']}/{t['seats_total']}\n"
            f"Haydovchi: {texts.contact_line(t)} (id {t['driver_id']})"
        )
    await _send_chunks(cb.message, lines, "Faol e'lonlar yo'q.")
    await cb.answer()


@router.callback_query(F.data == "adm:reqs")
async def list_requests(cb: CallbackQuery, db: Database) -> None:
    lines = []
    for r in await db.all_searching_requests():
        lines.append(
            f"🧍 <b>#{r['id']}</b> {texts.route_text(r)}\n"
            f"{fmt_date(r['trip_date'])}, {slot_name(r['slot'])}, {r['seats']} kishi\n"
            f"Yo'lovchi: {texts.contact_line(r)} (id {r['passenger_id']})"
        )
    await _send_chunks(cb.message, lines, "Haydovchi kutayotgan so'rovlar yo'q.")
    await cb.answer()


@router.callback_query(F.data == "adm:groups")
async def groups(cb: CallbackQuery, db: Database) -> None:
    s = await db.group_stats(datetime.now(timezone.utc).date().isoformat())
    lines = [
        "👥 <b>Guruhlar</b>\n"
        f"Kuzatilayotgan guruhlar: <b>{s['groups']}</b>\n"
        f"Bugun topilgan yo'lovchilar: <b>{s['leads_today']}</b> "
        f"(haydovchiga yuborilgan: {s['leads_sent_today']})\n"
        f"Jami topilgan: {s['leads_total']}"
    ]
    for g in await db.list_groups():
        status = "✅" if g["active"] else "❌ chiqarilgan"
        name = escape(g["title"] or str(g["id"]))
        lines.append(f"{status} {name} — {g['leads']} ta yo'lovchi, {g['sent']} tasi yuborildi")
    lines.append(
        "\nBotni guruhga qo'shish: guruh → Add members → botingiz. "
        "Avval BotFather'da /setprivacy → Disable qilingan bo'lishi kerak."
    )
    await _send_chunks(cb.message, lines, "")
    await cb.answer()


async def _ads_status_text(db: Database) -> str:
    cfg = await ad_settings(db)
    came = await db.count_users_from_ads()
    return (
        "📣 <b>Guruh reklamasi</b>\n\n"
        "Holati: " + ("✅ yoqilgan" if cfg["enabled"] else "❌ o'chirilgan") + "\n"
        f"Har <b>{cfg['interval']}</b> daqiqada bitta reklama, yo'nalishlar navbatma-navbat "
        "(guruhda yangi xabar bo'lsa)\n"
        f"Reklama orqali botga kelganlar: <b>{came}</b>\n\n"
        "Reklama faqat bot <b>admin</b> bo'lgan guruhlarga joylanadi. Har yo'nalishning "
        "yangisidan oldin eskisi o'chiriladi.\n\n"
        "Buyruqlar:\n"
        "/reklama_on — yoqish, /reklama_off — o'chirish\n"
        f"/reklama_vaqt <i>daqiqa</i> — oraliq (kamida {MIN_INTERVAL_MIN})\n"
        "/reklama_matn1 <i>matn</i> — Farg'ona ➜ Toshkent reklamasi matni\n"
        "/reklama_matn2 <i>matn</i> — Toshkent ➜ Farg'ona reklamasi matni\n"
        "/reklama_tugma1, /reklama_tugma2 <i>matn</i> — tugma yozuvlari\n"
        "/reklama_hozir — hozir barcha guruhlarga ikkala reklamani joylash\n\n"
        "<b>1) Farg'ona ➜ Toshkent:</b>\n" + escape(cfg["text"]["F2T"])
        + f"\n<i>Tugma:</i> {escape(cfg['button']['F2T'])}\n\n"
        "<b>2) Toshkent ➜ Farg'ona:</b>\n" + escape(cfg["text"]["T2F"])
        + f"\n<i>Tugma:</i> {escape(cfg['button']['T2F'])}"
    )


@router.callback_query(F.data == "adm:ads")
async def ads_menu(cb: CallbackQuery, db: Database) -> None:
    await cb.message.answer(await _ads_status_text(db))
    await cb.answer()


@router.message(Command("reklama"))
async def ads_status(message: Message, db: Database) -> None:
    await message.answer(await _ads_status_text(db))


@router.message(Command("reklama_on", "reklama_off"))
async def ads_toggle(message: Message, command: CommandObject, db: Database) -> None:
    on = command.command == "reklama_on"
    await db.set_setting(AD_ENABLED, "1" if on else "0")
    await message.answer("✅ Guruh reklamasi yoqildi." if on else "❌ Guruh reklamasi o'chirildi.")


@router.message(Command("reklama_vaqt"))
async def ads_interval(message: Message, command: CommandObject, db: Database) -> None:
    arg = (command.args or "").strip()
    if not arg.isdigit() or int(arg) < MIN_INTERVAL_MIN:
        await message.answer(f"Masalan: <code>/reklama_vaqt 30</code> (kamida {MIN_INTERVAL_MIN} daqiqa)")
        return
    await db.set_setting(AD_INTERVAL, arg)
    await message.answer(f"✅ Reklama endi har {arg} daqiqada joylanadi.")


@router.message(Command("reklama_matn1", "reklama_matn2", "reklama_tugma1", "reklama_tugma2"))
async def ads_text(message: Message, command: CommandObject, db: Database) -> None:
    # Buyruqdan keyingi matn, qator tashlashlar bilan birga
    parts = (message.text or "").split(maxsplit=1)
    value = parts[1].strip() if len(parts) > 1 else ""
    cmd = command.command
    direction = "F2T" if cmd.endswith("1") else "T2F"
    is_button = cmd.startswith("reklama_tugma")
    limit = 60 if is_button else 1000
    if not value or len(value) > limit:
        await message.answer(f"Buyruqdan keyin matnni yozing ({limit} belgigacha).")
        return
    await db.set_setting(k_button(direction) if is_button else k_text(direction), value)
    await message.answer("✅ Saqlandi. Keyingi reklamada yangi matn chiqadi.")


@router.message(Command("reklama_hozir"))
async def ads_now(message: Message, ads: AdService) -> None:
    n = await ads.tick(force=True)
    await message.answer(
        f"📣 {n} ta guruhga joylandi." if n else
        "Hech bir guruhga joylanmadi. Bot guruhda admin ekanini tekshiring."
    )


@router.callback_query(F.data == "adm:banhelp")
async def ban_help(cb: CallbackQuery) -> None:
    await cb.message.answer(
        "Foydalanuvchini topish: <code>/user @username</code> yoki <code>/user 99890...</code>\n"
        "Bloklash: <code>/ban 123456789</code>\nBlokdan chiqarish: <code>/unban 123456789</code>\n\n"
        "ID raqamlarni «Faol e'lonlar» va «Kutayotgan so'rovlar» ro'yxatida ham ko'rasiz."
    )
    await cb.answer()


@router.message(Command("tekshir"))
async def check_text(message: Message, command: CommandObject, db: Database) -> None:
    """Guruh xabarini bot qanday tushunishini va kimga yuborilishini ko'rsatadi."""
    if not command.args:
        await message.answer(
            "Masalan:\n<code>/tekshir Ertaga Qo'qondan Toshkentga 2 kishi kerak 90 123 45 67</code>"
        )
        return
    lead = parse_group(command.args)
    if lead is None:
        await message.answer(
            "❌ Bot bu xabarni <b>yo'lovchi e'loni deb tanimadi</b>.\n\n"
            "Xabarda Farg'ona tumani, Toshkent va «kerak», «kishi» kabi so'z bo'lishi kerak. "
            "«joy bor», «ketyapmiz», mashina nomi kabi so'zlar bo'lsa — haydovchi e'loni deb hisoblanadi."
        )
        return
    base = today()
    trip_date = lead.trip_date(base)
    dates = [trip_date] if trip_date else [iso for iso, _ in date_options(base)[:2]]
    trips = {t["id"]: t for t in await db.active_trips_on(lead.direction, dates)}
    matches = rank_trips_for_lead(lead.direction, lead.fergana_code, lead.tashkent_code,
                                  lead.slot, lead.seats, trips.values())
    lines = [
        "✅ <b>Yo'lovchi e'loni deb tanildi</b>",
        f"Yo'nalish: {DIRECTIONS[lead.direction]}",
        f"Tuman: {fergana_name(lead.fergana_code)}",
        f"Sana: {fmt_date(trip_date) if trip_date else 'aytilmagan (bugun va ertaga qidiriladi)'}",
        f"Vaqt: {slot_name(lead.slot) if lead.slot else 'aytilmagan'}",
        f"Kishi: {lead.seats or 'aytilmagan'}",
        "Telefon: " + (", ".join(lead.phones) or "yo'q"),
        "",
        f"Shu yo'nalish va sanada faol e'lonlar: {len(trips)}",
        f"Ulardan mos keladiganlar: <b>{len(matches)}</b>",
    ]
    for m in matches[:5]:
        t = trips[m.trip_id]
        mark = "" if m.covered else " (tumani e'lonida yo'q)"
        lines.append(f"• E'lon #{t['id']} (haydovchi id {t['driver_id']}), {m.distance_km:g} km{mark}")
    if not matches:
        lines.append(
            "\nMos haydovchi yo'q. Shu yo'nalishda faol e'lon bormi, sanasi va vaqti "
            "to'g'ri keladimi, bo'sh o'rni yetarlimi — tekshiring."
        )
    await message.answer("\n".join(lines))


# --- foydalanuvchilar ---------------------------------------------------------
@router.message(Command("user"))
async def find_user(message: Message, command: CommandObject, db: Database) -> None:
    if not command.args:
        await message.answer("Masalan: <code>/user @username</code>")
        return
    users = await db.find_users(command.args)
    if not users:
        await message.answer("Topilmadi.")
        return
    for u in users:
        trips = await db.active_trips_of(u["id"])
        reqs = await db.open_requests_of(u["id"])
        await message.answer(
            f"{texts.contact_line(u)}\nID: <code>{u['id']}</code>\n"
            f"Holati: {'🚫 bloklangan' if u['banned'] else '✅ faol'}\n"
            f"Faol e'lonlar: {len(trips)}, ochiq so'rovlar: {len(reqs)}"
        )


def _parse_id(command: CommandObject) -> int | None:
    arg = (command.args or "").strip()
    return int(arg) if arg.isdigit() else None


@router.message(Command("ban"))
async def ban(message: Message, command: CommandObject, db: Database,
              svc: MatchService, config: Config) -> None:
    uid = _parse_id(command)
    if uid is None:
        await message.answer("Masalan: <code>/ban 123456789</code>")
        return
    if uid in config.admin_ids:
        await message.answer("Adminni bloklab bo'lmaydi.")
        return
    if not await db.set_banned(uid, True):
        await message.answer("Bunday foydalanuvchi bazada yo'q.")
        return
    for t in await db.active_trips_of(uid):
        await svc.close_trip(t["id"], uid, "cancelled")
    for r in await db.open_requests_of(uid):
        await svc.cancel_request(r["id"], uid)
    await message.answer(f"🚫 {uid} bloklandi, faol e'lon va so'rovlari bekor qilindi.")


@router.message(Command("unban"))
async def unban(message: Message, command: CommandObject, db: Database) -> None:
    uid = _parse_id(command)
    if uid is None:
        await message.answer("Masalan: <code>/unban 123456789</code>")
        return
    ok = await db.set_banned(uid, False)
    await message.answer(f"✅ {uid} blokdan chiqarildi." if ok else "Bunday foydalanuvchi bazada yo'q.")


@router.message(Command("del_trip"))
async def del_trip(message: Message, command: CommandObject, db: Database, svc: MatchService) -> None:
    tid = _parse_id(command)
    trip = await db.get_trip(tid) if tid else None
    if not trip or trip["status"] != "active":
        await message.answer("Faol e'lon topilmadi. Masalan: <code>/del_trip 12</code>")
        return
    await svc.close_trip(tid, trip["driver_id"], "cancelled")
    await svc._send(trip["driver_id"], f"ℹ️ E'loningiz #{tid} admin tomonidan o'chirildi.")
    await message.answer(f"🗑 E'lon #{tid} o'chirildi.")


@router.message(Command("del_req"))
async def del_req(message: Message, command: CommandObject, db: Database, svc: MatchService) -> None:
    rid = _parse_id(command)
    req = await db.get_request(rid) if rid else None
    if not req or not await svc.cancel_request(rid, req["passenger_id"]):
        await message.answer("Ochiq so'rov topilmadi. Masalan: <code>/del_req 7</code>")
        return
    await svc._send(req["passenger_id"], f"ℹ️ So'rovingiz #{rid} admin tomonidan o'chirildi.")
    await message.answer(f"🗑 So'rov #{rid} o'chirildi.")


# --- xabar tarqatish ----------------------------------------------------------
@router.callback_query(F.data == "adm:bc")
async def bc_start(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Broadcast.text)
    await cb.message.answer(
        "📢 Hamma foydalanuvchilarga yuboriladigan xabarni yozing (matn, rasm yoki video).\n"
        "Bekor qilish: /cancel"
    )
    await cb.answer()


@router.message(Broadcast.text)
async def bc_preview(message: Message, state: FSMContext, db: Database) -> None:
    await state.update_data(chat_id=message.chat.id, msg_id=message.message_id)
    await state.set_state(Broadcast.confirm)
    n = len(await db.all_user_ids())
    await message.answer(
        f"Shu xabar <b>{n}</b> ta foydalanuvchiga yuborilsinmi?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Yuborish", callback_data="adm:bc_ok"),
            InlineKeyboardButton(text="❌ Bekor", callback_data="adm:bc_no"),
        ]]),
    )


@router.callback_query(Broadcast.confirm, F.data.in_({"adm:bc_ok", "adm:bc_no"}))
async def bc_send(cb: CallbackQuery, state: FSMContext, db: Database, bot: Bot) -> None:
    data = await state.get_data()
    await state.clear()
    await cb.message.edit_reply_markup(reply_markup=None)
    if cb.data == "adm:bc_no":
        await cb.message.answer("Bekor qilindi.", reply_markup=main_menu())
        await cb.answer()
        return
    await cb.answer("Yuborilmoqda...")
    ok = fail = 0
    for uid in await db.all_user_ids():
        try:
            await bot.copy_message(uid, data["chat_id"], data["msg_id"])
            ok += 1
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            try:
                await bot.copy_message(uid, data["chat_id"], data["msg_id"])
                ok += 1
            except TelegramAPIError:
                fail += 1
        except TelegramAPIError:
            fail += 1
        await asyncio.sleep(0.05)  # Telegram limitiga tushmaslik uchun
    await cb.message.answer(f"📢 Yuborildi: {ok}, yetkazilmadi: {fail}", reply_markup=main_menu())
