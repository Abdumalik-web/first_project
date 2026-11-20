"""Yo'lovchi so'rov qoldirish jarayoni.

Har bir qadamdan keyin `next_step` chaqiriladi: u hali to'ldirilmagan birinchi
maydonni so'raydi. Shu tufayli ovozli xabardan olingan ma'lumotlar bilan ham
ishlaydi — faqat yetishmayotgan savollar beriladi.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from .. import texts
from ..db import Database
from ..keyboards import (
    BTN_PASSENGER,
    BTN_SKIP,
    cancel_kb,
    confirm_kb,
    date_kb,
    direction_kb,
    fergana_kb,
    location_kb,
    main_menu,
    phone_kb,
    request_manage_kb,
    seats_kb,
    skip_kb,
    slot_kb,
    tashkent_kb,
)
from ..regions import (
    DIRECTIONS,
    FERGANA,
    TASHKENT,
    TO_TASHKENT,
    fergana_name,
    fmt_date,
    nearest_district,
    slot_name,
    tashkent_name,
)
from ..service import MatchService
from .phone import normalize_phone

router = Router(name="passenger")
P = "ps"


class PassengerForm(StatesGroup):
    direction = State()
    fergana = State()
    tashkent = State()
    date = State()
    slot = State()
    seats = State()
    location = State()
    comment = State()
    phone = State()
    confirm = State()


async def next_step(message: Message, state: FSMContext, db: Database, user_id: int) -> None:
    """Birinchi to'ldirilmagan maydonni so'raydi."""
    d = await state.get_data()
    to_t = d.get("direction") == TO_TASHKENT
    if not d.get("direction"):
        await state.set_state(PassengerForm.direction)
        await message.answer("Qayerga borasiz?", reply_markup=direction_kb(P))
    elif not d.get("fergana_code"):
        await state.set_state(PassengerForm.fergana)
        q = "Farg'ona viloyatining qaysi tumanidan chiqasiz?" if to_t \
            else "Farg'ona viloyatining qaysi tumaniga borasiz?"
        await message.answer(q, reply_markup=fergana_kb(P))
    elif not d.get("tashkent_code"):
        await state.set_state(PassengerForm.tashkent)
        q = "Toshkentning qaysi tumaniga borasiz?" if to_t else "Toshkentning qaysi tumanidan chiqasiz?"
        await message.answer(q, reply_markup=tashkent_kb(P))
    elif not d.get("trip_date"):
        await state.set_state(PassengerForm.date)
        await message.answer("Qaysi kuni?", reply_markup=date_kb(P))
    elif not d.get("slot"):
        await state.set_state(PassengerForm.slot)
        await message.answer("Qaysi vaqtda?", reply_markup=slot_kb(P))
    elif not d.get("seats"):
        await state.set_state(PassengerForm.seats)
        await message.answer("Necha kishisiz?", reply_markup=seats_kb(P, 4))
    elif "lat" not in d:
        await state.set_state(PassengerForm.location)
        where = "uyingiz / chiqadigan joyingiz" if to_t else "Toshkentdagi turgan joyingiz"
        await message.answer(
            f"📍 {where.capitalize()} lokatsiyasini yuboring — shunda sizga <b>eng yaqin</b> "
            "haydovchini topamiz. Xohlamasangiz o'tkazib yuboring.",
            reply_markup=location_kb(),
        )
    elif "comment" not in d:
        await state.set_state(PassengerForm.comment)
        await message.answer(
            "Haydovchi uchun izoh (masalan: «yukim bor», «oldingi o'rindiq») yoki o'tkazib yuboring:",
            reply_markup=skip_kb(),
        )
    elif not await _has_phone(db, user_id):
        await state.set_state(PassengerForm.phone)
        await message.answer(
            "Telefon raqamingizni yuboring (tugmani bosing yoki +998XXXXXXXXX ko'rinishida yozing):",
            reply_markup=phone_kb(),
        )
    else:
        await show_confirm(message, state)


async def _has_phone(db: Database, uid: int) -> bool:
    user = await db.get_user(uid)
    return bool(user and user["phone"])


async def _done(cb: CallbackQuery, text: str) -> None:
    """Tanlangan qiymatni ko'rsatib, tugmalarni olib tashlaydi."""
    try:
        await cb.message.edit_text(text)
    except Exception:  # noqa: BLE001 — xabar o'zgarmagan bo'lsa ham davom etamiz
        pass
    await cb.answer()


@router.message(StateFilter(None), F.text == BTN_PASSENGER)
async def start_passenger(message: Message, state: FSMContext, db: Database) -> None:
    u = message.from_user
    await db.upsert_user(u.id, u.full_name, u.username)
    await state.set_data({})
    await message.answer("🧍 Yangi so'rov. Bekor qilish uchun ❌ tugmasini bosing.", reply_markup=cancel_kb())
    await next_step(message, state, db, u.id)


@router.callback_query(PassengerForm.direction, F.data.startswith(f"{P}:dir:"))
async def set_direction(cb: CallbackQuery, state: FSMContext, db: Database) -> None:
    direction = cb.data.split(":")[2]
    await state.update_data(direction=direction)
    await _done(cb, f"Yo'nalish: <b>{DIRECTIONS[direction]}</b>")
    await next_step(cb.message, state, db, cb.from_user.id)


@router.callback_query(PassengerForm.fergana, F.data.startswith(f"{P}:fd:"))
async def set_fergana(cb: CallbackQuery, state: FSMContext, db: Database) -> None:
    code = cb.data.split(":")[2]
    await state.update_data(fergana_code=code)
    await _done(cb, f"Tuman: <b>{fergana_name(code)}</b>")
    await next_step(cb.message, state, db, cb.from_user.id)


@router.callback_query(PassengerForm.tashkent, F.data.startswith(f"{P}:td:"))
async def set_tashkent(cb: CallbackQuery, state: FSMContext, db: Database) -> None:
    code = cb.data.split(":")[2]
    await state.update_data(tashkent_code=code)
    await _done(cb, f"Toshkent: <b>{tashkent_name(code)}</b>")
    await next_step(cb.message, state, db, cb.from_user.id)


@router.callback_query(PassengerForm.date, F.data.startswith(f"{P}:date:"))
async def set_date(cb: CallbackQuery, state: FSMContext, db: Database) -> None:
    d = cb.data.split(":")[2]
    await state.update_data(trip_date=d)
    await _done(cb, f"Sana: <b>{fmt_date(d)}</b>")
    await next_step(cb.message, state, db, cb.from_user.id)


@router.callback_query(PassengerForm.slot, F.data.startswith(f"{P}:slot:"))
async def set_slot(cb: CallbackQuery, state: FSMContext, db: Database) -> None:
    slot = cb.data.split(":")[2]
    await state.update_data(slot=slot)
    await _done(cb, f"Vaqt: <b>{slot_name(slot)}</b>")
    await next_step(cb.message, state, db, cb.from_user.id)


@router.callback_query(PassengerForm.seats, F.data.startswith(f"{P}:seats:"))
async def set_seats(cb: CallbackQuery, state: FSMContext, db: Database) -> None:
    seats = int(cb.data.split(":")[2])
    await state.update_data(seats=seats)
    await _done(cb, f"Kishi soni: <b>{seats}</b>")
    await next_step(cb.message, state, db, cb.from_user.id)


@router.message(PassengerForm.location, F.location | (F.text == BTN_SKIP))
async def set_location(message: Message, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    if message.location:
        lat, lon = message.location.latitude, message.location.longitude
        await state.update_data(lat=lat, lon=lon)
        # Toshkentdan chiqsa — tumanni lokatsiyaga qarab aniqlaymiz
        if data["direction"] != TO_TASHKENT:
            await state.update_data(tashkent_code=nearest_district(TASHKENT, lat, lon))
        else:
            near = nearest_district(FERGANA, lat, lon)
            if near != data["fergana_code"]:
                await message.answer(
                    f"ℹ️ Lokatsiyangiz {fergana_name(near)} tumaniga yaqinroq. "
                    f"So'rov {fergana_name(data['fergana_code'])} tumani bo'yicha qoladi."
                )
    else:
        await state.update_data(lat=None, lon=None)
    await next_step(message, state, db, message.from_user.id)


@router.message(PassengerForm.comment, F.text)
async def set_comment(message: Message, state: FSMContext, db: Database) -> None:
    comment = None if message.text == BTN_SKIP else message.text.strip()[:200]
    await state.update_data(comment=comment)
    await next_step(message, state, db, message.from_user.id)


@router.message(PassengerForm.phone, F.contact | F.text)
async def set_phone(message: Message, state: FSMContext, db: Database) -> None:
    raw = message.contact.phone_number if message.contact else message.text
    phone = normalize_phone(raw)
    if not phone:
        await message.answer("Raqam noto'g'ri. Masalan: +998901234567", reply_markup=phone_kb())
        return
    await db.set_phone(message.from_user.id, phone)
    await next_step(message, state, db, message.from_user.id)


async def show_confirm(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(PassengerForm.confirm)
    preview = {
        "id": "—",
        "status": "new",
        "direction": data["direction"],
        "fergana_code": data["fergana_code"],
        "tashkent_code": data["tashkent_code"],
        "trip_date": data["trip_date"],
        "slot": data["slot"],
        "seats": data["seats"],
        "comment": data.get("comment"),
    }
    await message.answer("Tekshiring:", reply_markup=ReplyKeyboardRemove())
    await message.answer(
        texts.request_text(preview).replace(" — new", ""), reply_markup=confirm_kb(P)
    )


@router.callback_query(PassengerForm.confirm, F.data.in_({f"{P}:ok", f"{P}:no"}))
async def confirm(cb: CallbackQuery, state: FSMContext, db: Database, svc: MatchService) -> None:
    await cb.message.edit_reply_markup(reply_markup=None)
    if cb.data == f"{P}:no":
        await state.clear()
        await cb.message.answer("So'rov bekor qilindi.", reply_markup=main_menu())
        await cb.answer()
        return
    data = await state.get_data()
    await state.clear()
    req_id = await db.create_request(
        cb.from_user.id, data["direction"], data["fergana_code"], data["tashkent_code"],
        data.get("lat"), data.get("lon"), data["trip_date"], data["slot"], data["seats"],
        data.get("comment"),
    )
    await cb.answer()
    await cb.message.answer(
        f"✅ So'rov #{req_id} qabul qilindi. Eng yaqin haydovchini qidiryapmiz...",
        reply_markup=main_menu(),
    )
    if await svc.dispatch_request(req_id):
        await cb.message.answer(
            "📨 So'rovingiz eng yaqin haydovchiga yuborildi. U qabul qilishi bilan "
            "telefon raqamini sizga yuboramiz.",
            reply_markup=request_manage_kb(req_id),
        )
    # Guruh havolasi — har bir yo'lovchiga faqat bir marta
    link = await db.get_setting(texts.GROUP_LINK_KEY, texts.DEFAULT_GROUP_LINK)
    if link and await db.mark_user_link_notified(cb.from_user.id):
        await cb.message.answer(texts.passenger_link_text(link), disable_web_page_preview=True)
