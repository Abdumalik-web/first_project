"""Ovozli xabar orqali e'lon yoki so'rov berish."""
from __future__ import annotations

import logging
from dataclasses import asdict
from html import escape

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from ..db import Database
from ..keyboards import cancel_kb, main_menu
from ..regions import date_options, today
from ..voice import Parsed, VoiceError, VoiceParser
from . import driver, passenger

log = logging.getLogger(__name__)
router = Router(name="voice")

MAX_VOICE_SEC = 90


class VoiceRole(StatesGroup):
    choose = State()


def role_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🚗 Haydovchiman", callback_data="vc:role:driver"),
        InlineKeyboardButton(text="🧍 Yo'lovchiman", callback_data="vc:role:passenger"),
    ]])


def _form_role(state_name: str | None) -> str | None:
    if not state_name:
        return None
    if state_name.startswith("DriverForm"):
        return "driver"
    if state_name.startswith("PassengerForm"):
        return "passenger"
    return "other"


def passenger_updates(p: Parsed, current: dict) -> dict:
    valid_dates = {iso for iso, _ in date_options()}
    upd: dict = {}
    if p.direction:
        upd["direction"] = p.direction
    if p.fergana:
        upd["fergana_code"] = p.fergana[0]
    if p.tashkent:
        upd["tashkent_code"] = p.tashkent
    if p.trip_date in valid_dates:
        upd["trip_date"] = p.trip_date
    if p.slot:
        upd["slot"] = p.slot
    if p.seats:
        upd["seats"] = min(p.seats, 4)
    if p.comment or "comment" not in current:
        upd["comment"] = p.comment  # ovozda izoh bo'lmasa, alohida so'ramaymiz
    return upd


def driver_updates(p: Parsed, current: dict) -> dict:
    valid_dates = {iso for iso, _ in date_options()}
    upd: dict = {}
    if p.direction:
        upd["direction"] = p.direction
    if p.fergana:
        upd["districts"] = p.fergana[: driver.MAX_DISTRICTS]
        upd["districts_ok"] = True
    if p.trip_date in valid_dates:
        upd["trip_date"] = p.trip_date
    if p.slot:
        upd["slot"] = p.slot
    if p.seats:
        upd["seats"] = min(p.seats, 7)
    if p.car:
        upd["car"] = p.car
    if p.price:
        upd["price"] = p.price
    return upd


async def apply(role: str, parsed: Parsed, message: Message, state: FSMContext,
                db: Database, user_id: int, fresh: bool) -> None:
    data = await state.get_data()
    if role == "driver":
        await state.update_data(**driver_updates(parsed, data))
        if fresh:
            await message.answer("🚗 Yangi e'lon. Bekor qilish uchun ❌ tugmasini bosing.",
                                 reply_markup=cancel_kb())
        await driver.next_step(message, state, db, user_id)
    else:
        await state.update_data(**passenger_updates(parsed, data))
        if fresh:
            await message.answer("🧍 Yangi so'rov. Bekor qilish uchun ❌ tugmasini bosing.",
                                 reply_markup=cancel_kb())
        await passenger.next_step(message, state, db, user_id)


@router.message(F.voice | F.audio)
async def on_voice(message: Message, state: FSMContext, db: Database,
                   voice_parser: VoiceParser | None = None) -> None:
    form_role = _form_role(await state.get_state())
    if form_role == "other":
        return
    if voice_parser is None:
        await message.answer(
            "🎤 Ovozli xabar hozircha ishlamaydi. Iltimos, tugmalar orqali tanlang.",
            reply_markup=None if form_role else main_menu(),
        )
        return
    media = message.voice or message.audio
    if media.duration and media.duration > MAX_VOICE_SEC:
        await message.answer(f"Ovozli xabar {MAX_VOICE_SEC} soniyadan qisqa bo'lsin.")
        return

    u = message.from_user
    await db.upsert_user(u.id, u.full_name, u.username)
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    try:
        buf = await message.bot.download(media)
        text = await voice_parser.transcribe(buf.read())
        parsed = await voice_parser.extract(text, today())
    except VoiceError as e:
        await message.answer(f"😕 {e} Iltimos, qaytadan aniqroq gapiring yoki tugmalardan foydalaning.")
        return
    except Exception:  # noqa: BLE001
        log.exception("voice processing failed")
        await message.answer("😕 Xatolik yuz berdi. Iltimos, tugmalardan foydalaning.")
        return

    await message.answer(f"🎤 Siz aytdingiz: «{escape(text)}»")

    role = form_role or parsed.role
    if role is None:
        await state.set_state(VoiceRole.choose)
        await state.set_data({"voice_pending": asdict(parsed)})
        await message.answer("Siz haydovchimisiz yoki yo'lovchi?", reply_markup=role_kb())
        return
    if form_role is None:
        await state.set_data({})
    await apply(role, parsed, message, state, db, u.id, fresh=form_role is None)


@router.callback_query(VoiceRole.choose, F.data.startswith("vc:role:"))
async def choose_role(cb: CallbackQuery, state: FSMContext, db: Database) -> None:
    role = cb.data.split(":")[2]
    data = await state.get_data()
    parsed = Parsed(**data.get("voice_pending", {}))
    await state.set_data({})
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.answer()
    await apply(role, parsed, cb.message, state, db, cb.from_user.id, fresh=True)
