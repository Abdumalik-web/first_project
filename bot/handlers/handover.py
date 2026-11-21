"""Yo'lovchi uzatish: haydovchi o'zi olib keta olmaydigan (botda bo'lmagan) yo'lovchini
botga kiritadi, bot uni eng yaqin boshqa haydovchiga yuboradi, uzatgan haydovchi bonus oladi.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from .. import bonus, texts
from ..db import Database
from ..keyboards import (
    BTN_HANDOVER,
    BTN_SKIP,
    cancel_kb,
    confirm_kb,
    date_kb,
    direction_kb,
    fergana_kb,
    main_menu,
    seats_kb,
    skip_kb,
    slot_kb,
    tashkent_kb,
)
from ..regions import DIRECTIONS, TO_TASHKENT, fergana_name, fmt_date, slot_name, tashkent_name
from ..service import MatchService
from .phone import normalize_phone

router = Router(name="handover")
P = "ho"


class Handover(StatesGroup):
    direction = State()
    fergana = State()
    tashkent = State()
    date = State()
    slot = State()
    seats = State()
    phone = State()
    name = State()
    confirm = State()


async def next_step(message: Message, state: FSMContext) -> None:
    d = await state.get_data()
    to_t = d.get("direction") == TO_TASHKENT
    if not d.get("direction"):
        await state.set_state(Handover.direction)
        await message.answer("Yo'lovchi qayerga boradi?", reply_markup=direction_kb(P))
    elif not d.get("fergana_code"):
        await state.set_state(Handover.fergana)
        q = "Yo'lovchi Farg'onaning qaysi tumanidan chiqadi?" if to_t \
            else "Yo'lovchi Farg'onaning qaysi tumaniga boradi?"
        await message.answer(q, reply_markup=fergana_kb(P))
    elif not d.get("tashkent_code"):
        await state.set_state(Handover.tashkent)
        q = "Toshkentning qaysi tumaniga boradi?" if to_t else "Toshkentning qaysi tumanidan chiqadi?"
        await message.answer(q, reply_markup=tashkent_kb(P))
    elif not d.get("trip_date"):
        await state.set_state(Handover.date)
        await message.answer("Qaysi kuni?", reply_markup=date_kb(P))
    elif not d.get("slot"):
        await state.set_state(Handover.slot)
        await message.answer("Qaysi vaqtda?", reply_markup=slot_kb(P))
    elif not d.get("seats"):
        await state.set_state(Handover.seats)
        await message.answer("Necha kishi?", reply_markup=seats_kb(P, 4))
    elif not d.get("ext_phone"):
        await state.set_state(Handover.phone)
        await message.answer(
            "📞 Yo'lovchining telefon raqamini yozing (masalan: +998901234567).\n"
            "Raqam faqat yo'lovchini olgan haydovchiga ko'rsatiladi.",
            reply_markup=cancel_kb(),
        )
    elif "ext_name" not in d:
        await state.set_state(Handover.name)
        await message.answer(
            "Yo'lovchining ismi va qo'shimcha ma'lumot (masalan: «Akmal aka, yuki bor») "
            "yoki o'tkazib yuboring:",
            reply_markup=skip_kb(),
        )
    else:
        await state.set_state(Handover.confirm)
        preview = {
            "id": "—", "status": "new", "direction": d["direction"], "fergana_code": d["fergana_code"],
            "tashkent_code": d["tashkent_code"], "trip_date": d["trip_date"], "slot": d["slot"],
            "seats": d["seats"], "comment": d.get("ext_name"),
        }
        await message.answer("Tekshiring:", reply_markup=ReplyKeyboardRemove())
        await message.answer(
            texts.request_text(preview).replace(" — new", "").replace("So'rov #—", "Uzatilayotgan yo'lovchi")
            + f"\n📞 {texts.escape(d['ext_phone'])}",
            reply_markup=confirm_kb(P),
        )


async def _done(cb: CallbackQuery, text: str) -> None:
    try:
        await cb.message.edit_text(text)
    except Exception:  # noqa: BLE001
        pass
    await cb.answer()


async def _start(message: Message, state: FSMContext, db: Database, user) -> None:
    await db.upsert_user(user.id, user.full_name, user.username)
    await state.set_data({})
    pts = await bonus.per_handover(db)
    await message.answer(
        "📤 <b>Yo'lovchi uzatish</b>\n\n"
        "O'zingiz olib keta olmaydigan yo'lovchini kiriting — bot uni eng yaqin haydovchiga yuboradi. "
        f"Haydovchi olsa, sizga <b>{pts} ball</b> yoziladi.\n"
        "Bekor qilish uchun ❌ tugmasini bosing.",
        reply_markup=cancel_kb(),
    )
    await next_step(message, state)


@router.message(StateFilter(None), F.text == BTN_HANDOVER)
@router.message(StateFilter(None), Command("uzatish"))
async def start_msg(message: Message, state: FSMContext, db: Database) -> None:
    await _start(message, state, db, message.from_user)


@router.callback_query(F.data == bonus.HANDOVER_CB)
async def start_cb(cb: CallbackQuery, state: FSMContext, db: Database) -> None:
    await cb.answer()
    await _start(cb.message, state, db, cb.from_user)


@router.callback_query(Handover.direction, F.data.startswith(f"{P}:dir:"))
async def set_direction(cb: CallbackQuery, state: FSMContext) -> None:
    d = cb.data.split(":")[2]
    await state.update_data(direction=d)
    await _done(cb, f"Yo'nalish: <b>{DIRECTIONS[d]}</b>")
    await next_step(cb.message, state)


@router.callback_query(Handover.fergana, F.data.startswith(f"{P}:fd:"))
async def set_fergana(cb: CallbackQuery, state: FSMContext) -> None:
    code = cb.data.split(":")[2]
    await state.update_data(fergana_code=code)
    await _done(cb, f"Tuman: <b>{fergana_name(code)}</b>")
    await next_step(cb.message, state)


@router.callback_query(Handover.tashkent, F.data.startswith(f"{P}:td:"))
async def set_tashkent(cb: CallbackQuery, state: FSMContext) -> None:
    code = cb.data.split(":")[2]
    await state.update_data(tashkent_code=code)
    await _done(cb, f"Toshkent: <b>{tashkent_name(code)}</b>")
    await next_step(cb.message, state)


@router.callback_query(Handover.date, F.data.startswith(f"{P}:date:"))
async def set_date(cb: CallbackQuery, state: FSMContext) -> None:
    d = cb.data.split(":")[2]
    await state.update_data(trip_date=d)
    await _done(cb, f"Sana: <b>{fmt_date(d)}</b>")
    await next_step(cb.message, state)


@router.callback_query(Handover.slot, F.data.startswith(f"{P}:slot:"))
async def set_slot(cb: CallbackQuery, state: FSMContext) -> None:
    slot = cb.data.split(":")[2]
    await state.update_data(slot=slot)
    await _done(cb, f"Vaqt: <b>{slot_name(slot)}</b>")
    await next_step(cb.message, state)


@router.callback_query(Handover.seats, F.data.startswith(f"{P}:seats:"))
async def set_seats(cb: CallbackQuery, state: FSMContext) -> None:
    seats = int(cb.data.split(":")[2])
    await state.update_data(seats=seats)
    await _done(cb, f"Kishi soni: <b>{seats}</b>")
    await next_step(cb.message, state)


@router.message(Handover.phone, F.text | F.contact)
async def set_phone(message: Message, state: FSMContext, db: Database) -> None:
    raw = message.contact.phone_number if message.contact else message.text
    phone = normalize_phone(raw)
    if not phone:
        await message.answer("Raqam noto'g'ri. Masalan: +998901234567")
        return
    me = await db.get_user(message.from_user.id)
    if me and me["phone"] == phone:
        await message.answer("Bu sizning raqamingiz. Yo'lovchining raqamini yozing.")
        return
    d = await state.get_data()
    if await db.referral_exists(phone, d["trip_date"]):
        await message.answer(
            "⚠️ Bu yo'lovchi shu kunga allaqachon botga kiritilgan. Boshqa yo'lovchini kiriting "
            "yoki ❌ bilan bekor qiling."
        )
        return
    await state.update_data(ext_phone=phone)
    await next_step(message, state)


@router.message(Handover.name, F.text)
async def set_name(message: Message, state: FSMContext) -> None:
    name = None if message.text == BTN_SKIP else message.text.strip()[:100]
    await state.update_data(ext_name=name)
    await next_step(message, state)


@router.callback_query(Handover.confirm, F.data.in_({f"{P}:ok", f"{P}:no"}))
async def confirm(cb: CallbackQuery, state: FSMContext, db: Database, svc: MatchService) -> None:
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.answer()
    if cb.data == f"{P}:no":
        await state.clear()
        await cb.message.answer("Bekor qilindi.", reply_markup=main_menu())
        return
    d = await state.get_data()
    await state.clear()
    req_id = await db.create_request(
        cb.from_user.id, d["direction"], d["fergana_code"], d["tashkent_code"], None, None,
        d["trip_date"], d["slot"], d["seats"], d.get("ext_name"),
        ext_name=d.get("ext_name"), ext_phone=d["ext_phone"],
    )
    pts = await bonus.per_handover(db)
    await cb.message.answer(
        f"✅ Yo'lovchi #{req_id} botga uzatildi. Eng yaqin haydovchini qidiryapmiz.\n"
        f"Haydovchi olishi bilan sizga xabar beramiz va <b>{pts} ball</b> yoziladi.",
        reply_markup=main_menu(),
    )
    await svc.dispatch_request(req_id)
