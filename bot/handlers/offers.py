"""Haydovchining taklifga javobi (Olaman / Rad etish)."""
from aiogram import F, Router
from aiogram.types import CallbackQuery

from ..service import MatchService

router = Router(name="offers")


@router.callback_query(F.data.startswith("of:"))
async def offer_answer(cb: CallbackQuery, svc: MatchService) -> None:
    _, action, sid = cb.data.split(":")
    offer_id = int(sid)
    if action == "acc":
        result = await svc.accept(offer_id, cb.from_user.id)
        if result == "ok":
            await cb.message.edit_reply_markup(reply_markup=None)
            await cb.answer("Yo'lovchi sizga biriktirildi ✅")
        elif result == "no_seats":
            await cb.message.edit_reply_markup(reply_markup=None)
            await cb.answer("Bo'sh o'rin yetarli emas — so'rov boshqa haydovchiga yuborildi", show_alert=True)
        else:
            await cb.message.edit_reply_markup(reply_markup=None)
            await cb.answer("Bu taklif endi amal qilmaydi", show_alert=True)
    else:
        await svc.reject(offer_id, cb.from_user.id)
        await cb.message.edit_reply_markup(reply_markup=None)
        await cb.answer("Rad etildi. So'rov boshqa haydovchiga yuboriladi.")
