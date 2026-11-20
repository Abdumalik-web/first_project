"""Haydovchi e'lon berish jarayoni."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from .. import texts
from ..db import Database
from ..keyboards import (
    BTN_DRIVER,
    BTN_SKIP,
    cancel_kb,
    confirm_kb,
    date_kb,
    direction_kb,
    fergana_kb,
    location_kb,
    main_menu,
    phone_kb,
    seats_kb,
    skip_kb,
    slot_kb,
    trip_manage_kb,
)
from ..regions import DIRECTIONS, fergana_name, fmt_date, slot_name
from ..service import MatchService
from .phone import normalize_phone

router = Router(name="driver")
P = "dr"  # callback prefiksi
MAX_DISTRICTS = 6


class DriverForm(StatesGroup):
    direction = State()
    districts = State()
    date = State()
    slot = State()
    seats = State()
    car = State()
    price = State()
    phone = State()
    location = State()
    confirm = State()


async def next_step(message: Message, state: FSMContext, db: Database, user_id: int) -> None:
    """Birinchi to'ldirilmagan maydonni so'raydi (ovozli xabardan keyin ham ishlaydi)."""
    d = await state.get_data()
    if not d.get("direction"):
        await state.set_state(DriverForm.direction)
        await message.answer("Qaysi yo'nalishda yurasiz?", reply_markup=direction_kb(P))
    elif not d.get("districts_ok"):
        await state.set_state(DriverForm.districts)
        where = "olasiz" if d["direction"] == "F2T" else "eltib qo'yasiz"
        selected = set(d.get("districts") or [])
        await message.answer(
            f"Farg'ona viloyatining qaysi tumanlaridan yo'lovchi {where}? "
            f"(bir nechtasini tanlang, ko'pi bilan {MAX_DISTRICTS} ta, so'ng «➡️ Tayyor»)\n\n"
            "💡 Birinchi tanlagan tumaningiz — sizning asosiy joyingiz hisoblanadi.",
            reply_markup=fergana_kb(P, selected, multi=True),
        )
    elif not d.get("trip_date"):
        await state.set_state(DriverForm.date)
        await message.answer("Qaysi kuni yurasiz?", reply_markup=date_kb(P))
    elif not d.get("slot"):
        await state.set_state(DriverForm.slot)
        await message.answer("Taxminan soat nechada?", reply_markup=slot_kb(P))
    elif not d.get("seats"):
        await state.set_state(DriverForm.seats)
        await message.answer("Nechta bo'sh o'rin bor?", reply_markup=seats_kb(P, 7))
    elif not d.get("car"):
        await state.set_state(DriverForm.car)
        await message.answer(
            "Mashinangiz rusumi, rangi va raqami? (masalan: Cobalt, oq, 40 A 123 BC)",
            reply_markup=cancel_kb(),
        )
    elif "price" not in d:
        await state.set_state(DriverForm.price)
        await message.answer("Bir kishi uchun narx? (masalan: 150 000 so'm)", reply_markup=skip_kb())
    elif not await _has_phone(db, user_id):
        await state.set_state(DriverForm.phone)
        await message.answer(
            "Telefon raqamingizni yuboring (tugmani bosing yoki +998XXXXXXXXX ko'rinishida yozing):",
            reply_markup=phone_kb(),
        )
    elif "lat" not in d:
        await state.set_state(DriverForm.location)
        await message.answer(
            "📍 Hozirgi joylashuvingizni yuboring — shunda sizga <b>eng yaqin</b> yo'lovchilar "
            "yuboriladi. Keyinroq ham «📍 Joylashuvni yangilash» tugmasi bilan yangilashingiz mumkin.",
            reply_markup=location_kb(),
        )
    else:
        await show_confirm(message, state)


async def _has_phone(db: Database, uid: int) -> bool:
    user = await db.get_user(uid)
    return bool(user and user["phone"])


async def _done(cb: CallbackQuery, text: str) -> None:
    try:
        await cb.message.edit_text(text)
    except Exception:  # noqa: BLE001
        pass
    await cb.answer()


@router.message(StateFilter(None), F.text == BTN_DRIVER)
async def start_driver(message: Message, state: FSMContext, db: Database) -> None:
    u = message.from_user
    await db.upsert_user(u.id, u.full_name, u.username)
    await state.set_data({})
    await message.answer("🚗 Yangi e'lon. Bekor qilish uchun ❌ tugmasini bosing.", reply_markup=cancel_kb())
    await next_step(message, state, db, u.id)


@router.callback_query(DriverForm.direction, F.data.startswith(f"{P}:dir:"))
async def set_direction(cb: CallbackQuery, state: FSMContext, db: Database) -> None:
    direction = cb.data.split(":")[2]
    await state.update_data(direction=direction)
    await _done(cb, f"Yo'nalish: <b>{DIRECTIONS[direction]}</b>")
    await next_step(cb.message, state, db, cb.from_user.id)


@router.callback_query(DriverForm.districts, F.data.startswith(f"{P}:fd:"))
async def toggle_district(cb: CallbackQuery, state: FSMContext) -> None:
    code = cb.data.split(":")[2]
    data = await state.get_data()
    selected: list[str] = list(data.get("districts") or [])
    if code in selected:
        selected.remove(code)
    elif len(selected) >= MAX_DISTRICTS:
        await cb.answer(f"Ko'pi bilan {MAX_DISTRICTS} ta tuman tanlash mumkin", show_alert=True)
        return
    else:
        selected.append(code)
    await state.update_data(districts=selected)
    await cb.message.edit_reply_markup(reply_markup=fergana_kb(P, set(selected), multi=True))
    await cb.answer(", ".join(fergana_name(c) for c in selected) or "Hech narsa tanlanmagan")


@router.callback_query(DriverForm.districts, F.data == f"{P}:fd_done")
async def districts_done(cb: CallbackQuery, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    if not data.get("districts"):
        await cb.answer("Kamida bitta tuman tanlang", show_alert=True)
        return
    await state.update_data(districts_ok=True)
    names = ", ".join(fergana_name(c) for c in data["districts"])
    await _done(cb, f"Tumanlar: <b>{names}</b>")
    await next_step(cb.message, state, db, cb.from_user.id)


@router.callback_query(DriverForm.date, F.data.startswith(f"{P}:date:"))
async def set_date(cb: CallbackQuery, state: FSMContext, db: Database) -> None:
    d = cb.data.split(":")[2]
    await state.update_data(trip_date=d)
    await _done(cb, f"Sana: <b>{fmt_date(d)}</b>")
    await next_step(cb.message, state, db, cb.from_user.id)


@router.callback_query(DriverForm.slot, F.data.startswith(f"{P}:slot:"))
async def set_slot(cb: CallbackQuery, state: FSMContext, db: Database) -> None:
    slot = cb.data.split(":")[2]
    await state.update_data(slot=slot)
    await _done(cb, f"Vaqt: <b>{slot_name(slot)}</b>")
    await next_step(cb.message, state, db, cb.from_user.id)


@router.callback_query(DriverForm.seats, F.data.startswith(f"{P}:seats:"))
async def set_seats(cb: CallbackQuery, state: FSMContext, db: Database) -> None:
    seats = int(cb.data.split(":")[2])
    await state.update_data(seats=seats)
    await _done(cb, f"Bo'sh o'rin: <b>{seats}</b>")
    await next_step(cb.message, state, db, cb.from_user.id)


@router.message(DriverForm.car, F.text)
async def set_car(message: Message, state: FSMContext, db: Database) -> None:
    await state.update_data(car=message.text.strip()[:100])
    await next_step(message, state, db, message.from_user.id)


@router.message(DriverForm.price, F.text)
async def set_price(message: Message, state: FSMContext, db: Database) -> None:
    price = None if message.text == BTN_SKIP else message.text.strip()[:50]
    await state.update_data(price=price)
    await next_step(message, state, db, message.from_user.id)


@router.message(DriverForm.phone, F.contact | F.text)
async def set_phone(message: Message, state: FSMContext, db: Database) -> None:
    raw = message.contact.phone_number if message.contact else message.text
    phone = normalize_phone(raw)
    if not phone:
        await message.answer("Raqam noto'g'ri. Masalan: +998901234567", reply_markup=phone_kb())
        return
    await db.set_phone(message.from_user.id, phone)
    await next_step(message, state, db, message.from_user.id)


@router.message(DriverForm.location, F.location | (F.text == BTN_SKIP))
async def set_location(message: Message, state: FSMContext, db: Database) -> None:
    if message.location:
        await state.update_data(lat=message.location.latitude, lon=message.location.longitude)
    else:
        await state.update_data(lat=None, lon=None)
    await next_step(message, state, db, message.from_user.id)


async def show_confirm(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(DriverForm.confirm)
    preview = {
        "id": "—",
        "direction": data["direction"],
        "districts": ",".join(data["districts"]),
        "trip_date": data["trip_date"],
        "slot": data["slot"],
        "seats_free": data["seats"],
        "seats_total": data["seats"],
        "car": data.get("car"),
        "price": data.get("price"),
        "lat": data.get("lat"),
    }
    pub = ("\n\n📢 E'loningiz telefon raqamingiz va Telegram akkauntingiz bilan guruhlarga ham "
           "joylanadi. O'chirish: «📋 Mening e'lonlarim» ➜ «📢 Guruhlarga joylash».")
    await message.answer("Tekshiring:", reply_markup=ReplyKeyboardRemove())
    await message.answer(texts.trip_text(preview) + pub, reply_markup=confirm_kb(P))


@router.callback_query(DriverForm.confirm, F.data.in_({f"{P}:ok", f"{P}:no"}))
async def confirm(cb: CallbackQuery, state: FSMContext, db: Database, svc: MatchService) -> None:
    if cb.data == f"{P}:no":
        await state.clear()
        await cb.message.edit_reply_markup(reply_markup=None)
        await cb.message.answer("E'lon bekor qilindi.", reply_markup=main_menu())
        await cb.answer()
        return
    data = await state.get_data()
    await state.clear()
    trip_id = await db.create_trip(
        cb.from_user.id, data["direction"], data["districts"], data["trip_date"], data["slot"],
        data["seats"], data.get("car"), data.get("price"), data.get("lat"), data.get("lon"),
        publish=True,
    )
    await cb.message.edit_reply_markup(reply_markup=None)
    trip = await db.get_trip(trip_id)
    await cb.message.answer(
        "✅ E'loningiz joylandi! Mos yo'lovchi topilishi bilan sizga yuboramiz.",
        reply_markup=main_menu(),
    )
    await cb.message.answer(texts.trip_text(trip), reply_markup=trip_manage_kb(trip_id))
    await cb.answer()
    sent = await svc.on_new_trip(trip_id)
    if not sent:
        await cb.message.answer("Hozircha kutayotgan mos yo'lovchi yo'q — yangi so'rov tushishi bilan xabar beramiz.")
