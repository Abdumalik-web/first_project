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


@router.message(StateFilter(None), F.text == BTN_DRIVER)
async def start_driver(message: Message, state: FSMContext, db: Database) -> None:
    u = message.from_user
    await db.upsert_user(u.id, u.full_name, u.username)
    await state.set_state(DriverForm.direction)
    await message.answer("🚗 Yangi e'lon. Bekor qilish uchun ❌ tugmasini bosing.", reply_markup=cancel_kb())
    await message.answer("Qaysi yo'nalishda yurasiz?", reply_markup=direction_kb(P))


@router.callback_query(DriverForm.direction, F.data.startswith(f"{P}:dir:"))
async def set_direction(cb: CallbackQuery, state: FSMContext) -> None:
    direction = cb.data.split(":")[2]
    await state.update_data(direction=direction, districts=[])
    await state.set_state(DriverForm.districts)
    where = "olasiz" if direction == "F2T" else "eltib qo'yasiz"
    await cb.message.edit_text(
        f"Yo'nalish: <b>{DIRECTIONS[direction]}</b>\n\n"
        f"Farg'ona viloyatining qaysi tumanlaridan yo'lovchi {where}? "
        f"(bir nechtasini tanlang, ko'pi bilan {MAX_DISTRICTS} ta)\n\n"
        "💡 Birinchi tanlagan tumaningiz — sizning asosiy joyingiz hisoblanadi.",
        reply_markup=fergana_kb(P, multi=True),
    )
    await cb.answer()


@router.callback_query(DriverForm.districts, F.data.startswith(f"{P}:fd:"))
async def toggle_district(cb: CallbackQuery, state: FSMContext) -> None:
    code = cb.data.split(":")[2]
    data = await state.get_data()
    selected: list[str] = data.get("districts", [])
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
async def districts_done(cb: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if not data.get("districts"):
        await cb.answer("Kamida bitta tuman tanlang", show_alert=True)
        return
    await state.set_state(DriverForm.date)
    names = ", ".join(fergana_name(c) for c in data["districts"])
    await cb.message.edit_text(f"Tumanlar: <b>{names}</b>\n\nQaysi kuni yurasiz?", reply_markup=date_kb(P))
    await cb.answer()


@router.callback_query(DriverForm.date, F.data.startswith(f"{P}:date:"))
async def set_date(cb: CallbackQuery, state: FSMContext) -> None:
    d = cb.data.split(":")[2]
    await state.update_data(trip_date=d)
    await state.set_state(DriverForm.slot)
    await cb.message.edit_text(f"Sana: <b>{fmt_date(d)}</b>\n\nTaxminan soat nechada?", reply_markup=slot_kb(P))
    await cb.answer()


@router.callback_query(DriverForm.slot, F.data.startswith(f"{P}:slot:"))
async def set_slot(cb: CallbackQuery, state: FSMContext) -> None:
    slot = cb.data.split(":")[2]
    await state.update_data(slot=slot)
    await state.set_state(DriverForm.seats)
    await cb.message.edit_text(f"Vaqt: <b>{slot_name(slot)}</b>\n\nNechta bo'sh o'rin bor?", reply_markup=seats_kb(P, 7))
    await cb.answer()


@router.callback_query(DriverForm.seats, F.data.startswith(f"{P}:seats:"))
async def set_seats(cb: CallbackQuery, state: FSMContext) -> None:
    seats = int(cb.data.split(":")[2])
    await state.update_data(seats=seats)
    await state.set_state(DriverForm.car)
    await cb.message.edit_text(f"Bo'sh o'rin: <b>{seats}</b>")
    await cb.message.answer(
        "Mashinangiz rusumi, rangi va raqami? (masalan: Cobalt, oq, 40 A 123 BC)",
        reply_markup=cancel_kb(),
    )
    await cb.answer()


@router.message(DriverForm.car, F.text)
async def set_car(message: Message, state: FSMContext) -> None:
    await state.update_data(car=message.text.strip()[:100])
    await state.set_state(DriverForm.price)
    await message.answer("Bir kishi uchun narx? (masalan: 150 000 so'm)", reply_markup=skip_kb())


@router.message(DriverForm.price, F.text)
async def set_price(message: Message, state: FSMContext, db: Database) -> None:
    price = None if message.text == BTN_SKIP else message.text.strip()[:50]
    await state.update_data(price=price)
    user = await db.get_user(message.from_user.id)
    if user and user["phone"]:
        await ask_location(message, state)
    else:
        await state.set_state(DriverForm.phone)
        await message.answer(
            "Telefon raqamingizni yuboring (tugmani bosing yoki +998XXXXXXXXX ko'rinishida yozing):",
            reply_markup=phone_kb(),
        )


@router.message(DriverForm.phone, F.contact | F.text)
async def set_phone(message: Message, state: FSMContext, db: Database) -> None:
    raw = message.contact.phone_number if message.contact else message.text
    phone = normalize_phone(raw)
    if not phone:
        await message.answer("Raqam noto'g'ri. Masalan: +998901234567", reply_markup=phone_kb())
        return
    await db.set_phone(message.from_user.id, phone)
    await ask_location(message, state)


async def ask_location(message: Message, state: FSMContext) -> None:
    await state.set_state(DriverForm.location)
    await message.answer(
        "📍 Hozirgi joylashuvingizni yuboring — shunda sizga <b>eng yaqin</b> yo'lovchilar "
        "yuboriladi. Keyinroq ham «📍 Joylashuvni yangilash» tugmasi bilan yangilashingiz mumkin.",
        reply_markup=location_kb(),
    )


@router.message(DriverForm.location, F.location | (F.text == BTN_SKIP))
async def set_location(message: Message, state: FSMContext) -> None:
    if message.location:
        await state.update_data(lat=message.location.latitude, lon=message.location.longitude)
    else:
        await state.update_data(lat=None, lon=None)
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
    await message.answer("Tekshiring:", reply_markup=ReplyKeyboardRemove())
    await message.answer(texts.trip_text(preview), reply_markup=confirm_kb(P))


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
