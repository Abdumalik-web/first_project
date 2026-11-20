from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from .. import texts
from ..db import Database
from ..regions import DIRECTIONS
from ..keyboards import (
    cancel_kb,
    BTN_CANCEL,
    BTN_HELP,
    BTN_MY,
    main_menu,
    request_manage_kb,
    trip_manage_kb,
)
from ..service import MatchService

router = Router(name="common")


@router.message(CommandStart())
async def start(message: Message, state: FSMContext, db: Database,
                command: CommandObject | None = None) -> None:
    await state.clear()
    u = message.from_user
    await db.upsert_user(u.id, u.full_name, u.username)
    args = (command.args or "") if command else ""
    group_part, _, direction = args.partition("_")
    if group_part.startswith("g") and group_part[1:].isdigit():
        # Guruhdagi reklama tugmasi orqali kelgan
        await db.set_user_source(u.id, group_part[:32])
        if direction in ("F2T", "T2F"):
            # Yo'nalish reklamadan ma'lum — yo'lovchi so'rovini darhol boshlaymiz
            from .passenger import next_step
            await state.set_data({"direction": direction})
            await message.answer(
                f"Assalomu alaykum, <b>{texts.escape(u.first_name or '')}</b>! 🚕\n"
                f"Yo'nalish: <b>{DIRECTIONS[direction]}</b>. Joy band qilamiz — bir necha savol.\n"
                "Bekor qilish uchun ❌ tugmasini bosing.",
                reply_markup=cancel_kb(),
            )
            await next_step(message, state, db, u.id)
            return
        await message.answer(
            f"Assalomu alaykum, <b>{texts.escape(u.first_name or '')}</b>! 🚕\n\n"
            "<b>Farg'ona ⇄ Toshkent</b> yo'nalishida sizga eng yaqin haydovchini topamiz.\n\n"
            "Joy band qilish uchun pastdagi <b>«🧍 Yo'lovchiman»</b> tugmasini bosing.\n"
            "Haydovchi bo'lsangiz — <b>«🚗 Haydovchiman»</b>.",
            reply_markup=main_menu(),
        )
        return
    await message.answer(
        f"Assalomu alaykum, <b>{texts.escape(u.first_name or '')}</b>!\n\n"
        "Bu bot <b>Farg'ona viloyati ⇄ Toshkent</b> yo'nalishida haydovchi va "
        "yo'lovchilarni bir-biriga topib beradi.\n\n"
        "Kimsiz?",
        reply_markup=main_menu(),
    )


@router.message(Command("help"))
@router.message(F.text == BTN_HELP)
async def help_(message: Message) -> None:
    await message.answer(texts.HELP, reply_markup=main_menu())


@router.message(Command("id"))
async def my_id(message: Message) -> None:
    await message.answer(f"Sizning Telegram ID raqamingiz: <code>{message.from_user.id}</code>")


@router.message(Command("cancel"))
@router.message(F.text == BTN_CANCEL)
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=main_menu())


@router.message(StateFilter(None), F.text == BTN_MY)
@router.message(Command("my"))
async def my_items(message: Message, db: Database) -> None:
    uid = message.from_user.id
    trips = await db.active_trips_of(uid)
    reqs = await db.open_requests_of(uid)
    if not trips and not reqs:
        await message.answer("Sizda faol e'lon yoki so'rov yo'q.", reply_markup=main_menu())
        return
    for t in trips:
        await message.answer(texts.trip_text(t), reply_markup=trip_manage_kb(t["id"]))
    for r in reqs:
        text = texts.request_text(r)
        if r["status"] == "matched" and r["trip_id"]:
            trip = await db.get_trip(r["trip_id"])
            driver = await db.get_user(trip["driver_id"])
            text += f"\n\n<b>Haydovchi:</b> {texts.contact_line(driver)}"
        await message.answer(text, reply_markup=request_manage_kb(r["id"]))


@router.message(StateFilter(None), F.location)
async def update_location(message: Message, db: Database, svc: MatchService) -> None:
    """Haydovchi joylashuvini yangilaydi (faol e'lonlarida)."""
    uid = message.from_user.id
    n = await db.set_trip_location(uid, message.location.latitude, message.location.longitude)
    if n:
        await message.answer(
            "📍 Joylashuvingiz yangilandi. Endi sizga eng yaqin yo'lovchilar yuboriladi.",
            reply_markup=main_menu(),
        )
        for t in await db.active_trips_of(uid):
            await svc.on_new_trip(t["id"])
    else:
        await message.answer(
            "Sizda faol haydovchi e'loni yo'q. Avval «🚗 Haydovchiman» orqali e'lon bering.",
            reply_markup=main_menu(),
        )


# --- e'lon / so'rovni boshqarish ---------------------------------------------
@router.callback_query(F.data.startswith("tm:"))
async def trip_manage(cb: CallbackQuery, db: Database, svc: MatchService) -> None:
    _, action, sid = cb.data.split(":")
    trip_id = int(sid)
    trip = await db.get_trip(trip_id)
    if not trip or trip["driver_id"] != cb.from_user.id:
        await cb.answer("E'lon topilmadi", show_alert=True)
        return
    if action == "pax":
        pax = await db.passengers_of_trip(trip_id)
        if not pax:
            await cb.answer("Hozircha yo'lovchi yo'q", show_alert=True)
            return
        lines = [f"👥 <b>E'lon #{trip_id} yo'lovchilari:</b>"]
        for p in pax:
            lines.append(
                f"\n• {texts.contact_line(p)}\n  {texts.route_text(p)}, {p['seats']} kishi"
                + (f"\n  Izoh: {texts.escape(p['comment'])}" if p["comment"] else "")
            )
        await cb.message.answer("\n".join(lines))
        await cb.answer()
        return
    status = "done" if action == "done" else "cancelled"
    if await svc.close_trip(trip_id, cb.from_user.id, status):
        msg = "🏁 E'lon yakunlandi. Yaxshi yo'l!" if status == "done" else "🗑 E'lon bekor qilindi."
        await cb.message.edit_reply_markup(reply_markup=None)
        await cb.message.answer(msg, reply_markup=main_menu())
    await cb.answer()


@router.callback_query(F.data.startswith("rm:cancel:"))
async def request_cancel(cb: CallbackQuery, svc: MatchService) -> None:
    req_id = int(cb.data.split(":")[2])
    if await svc.cancel_request(req_id, cb.from_user.id):
        await cb.message.edit_reply_markup(reply_markup=None)
        await cb.message.answer(f"🗑 So'rov #{req_id} bekor qilindi.", reply_markup=main_menu())
        await cb.answer()
    else:
        await cb.answer("So'rov allaqachon yopilgan", show_alert=True)
