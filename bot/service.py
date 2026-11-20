"""Yo'lovchi so'rovlarini haydovchilarga taqsimlash."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from . import texts
from .config import Config
from .db import Database
from .keyboards import offer_kb
from .matching import rank_trips
from .regions import today

log = logging.getLogger(__name__)


class MatchService:
    def __init__(self, bot: Bot, db: Database, config: Config):
        self.bot = bot
        self.db = db
        self.config = config
        # Bitta so'rov bir vaqtda ikki marta taqsimlanmasligi uchun
        self._lock = asyncio.Lock()

    async def _send(self, chat_id: int, text: str, **kw):
        try:
            return await self.bot.send_message(chat_id, text, **kw)
        except TelegramAPIError as e:  # foydalanuvchi botni bloklagan bo'lishi mumkin
            log.warning("send_message %s failed: %s", chat_id, e)
            return None

    async def _edit_offer_msg(self, offer, suffix: str) -> None:
        if not offer["driver_msg_id"]:
            return
        trip = await self.db.get_trip(offer["trip_id"])
        try:
            await self.bot.edit_message_reply_markup(
                chat_id=trip["driver_id"], message_id=offer["driver_msg_id"], reply_markup=None
            )
            await self.bot.send_message(
                trip["driver_id"], suffix, reply_to_message_id=offer["driver_msg_id"]
            )
        except TelegramAPIError as e:
            log.debug("edit offer msg failed: %s", e)

    # ------------------------------------------------------------------ #
    async def dispatch_request(self, req_id: int) -> bool:
        """So'rovni navbatdagi eng yaqin mos haydovchiga yuboradi.

        True — taklif yuborildi, False — mos haydovchi yo'q (yoki so'rov yopiq).
        """
        async with self._lock:
            req = await self.db.get_request(req_id)
            if not req or req["status"] != "searching":
                return False
            if await self.db.pending_offer_for(req_id):
                return True

            trips = await self.db.candidate_trips(req["direction"], req["trip_date"])
            tried = await self.db.offered_trip_ids(req_id)
            matches = rank_trips(req, trips, tried)

            for m in matches:
                offer_id = await self.db.create_offer(req_id, m.trip_id, m.distance_km)
                trip = await self.db.get_trip(m.trip_id)
                passenger = await self.db.get_user(req["passenger_id"])
                msg = await self._send(
                    trip["driver_id"],
                    texts.offer_text(req, passenger, m.distance_km, self.config.offer_timeout_min),
                    reply_markup=offer_kb(offer_id),
                )
                if msg is None:  # haydovchiga yetkazib bo'lmadi — keyingisiga
                    await self.db.close_offer(offer_id, "expired")
                    continue
                await self.db.set_offer_msg(offer_id, msg.message_id)
                if req["lat"] is not None:
                    try:
                        await self.bot.send_location(
                            trip["driver_id"], req["lat"], req["lon"],
                            reply_to_message_id=msg.message_id,
                        )
                    except TelegramAPIError:
                        pass
                return True

            if not req["wait_notified"]:
                await self.db.execute("UPDATE requests SET wait_notified=1 WHERE id=?", req_id)
                await self._send(
                    req["passenger_id"],
                    f"⏳ So'rov #{req_id}: hozircha mos haydovchi topilmadi. "
                    "Yangi haydovchi e'lon bersa, darhol unga yuboramiz va sizga xabar beramiz.",
                )
            return False

    async def on_new_trip(self, trip_id: int) -> int:
        """Yangi e'lon paydo bo'lganda kutayotgan yo'lovchilarni qayta taqsimlaydi."""
        trip = await self.db.get_trip(trip_id)
        if not trip:
            return 0
        sent = 0
        for req in await self.db.searching_requests(trip["direction"], trip["trip_date"]):
            if await self.dispatch_request(req["id"]):
                sent += 1
        return sent

    # ------------------------------------------------------------------ #
    async def accept(self, offer_id: int, driver_id: int) -> str:
        offer = await self.db.get_offer(offer_id)
        if not offer:
            return "closed"
        trip = await self.db.get_trip(offer["trip_id"])
        if trip["driver_id"] != driver_id:
            return "closed"
        result = await self.db.accept_offer(offer_id)
        req = await self.db.get_request(offer["request_id"])
        if result == "no_seats":
            await self.dispatch_request(req["id"])
            return result
        if result != "ok":
            return result

        trip = await self.db.get_trip(trip["id"])
        driver = await self.db.get_user(trip["driver_id"])
        passenger = await self.db.get_user(req["passenger_id"])
        await self._send(
            req["passenger_id"],
            "🎉 <b>Haydovchi topildi!</b>\n\n"
            f"{texts.request_text(req)}\n\n"
            f"<b>Haydovchi:</b> {texts.contact_line(driver)}\n"
            + (f"Mashina: {texts.escape(trip['car'])}\n" if trip["car"] else "")
            + (f"Narx: {texts.escape(trip['price'])}\n" if trip["price"] else "")
            + "\nHaydovchi siz bilan bog'lanadi. Yaxshi yo'l!",
        )
        if trip["lat"] is not None:
            try:
                await self.bot.send_location(req["passenger_id"], trip["lat"], trip["lon"])
            except TelegramAPIError:
                pass
        await self._send(
            driver_id,
            f"✅ So'rov #{req['id']} sizga biriktirildi.\n\n"
            f"<b>Yo'lovchi:</b> {texts.contact_line(passenger)}\n"
            f"Yo'nalish: {texts.route_text(req)}\n"
            f"Kishi soni: {req['seats']}\n"
            f"Qolgan bo'sh o'rin: {trip['seats_free']}",
        )
        return "ok"

    async def reject(self, offer_id: int, driver_id: int) -> bool:
        offer = await self.db.get_offer(offer_id)
        if not offer:
            return False
        trip = await self.db.get_trip(offer["trip_id"])
        if trip["driver_id"] != driver_id:
            return False
        if not await self.db.close_offer(offer_id, "rejected"):
            return False
        await self.dispatch_request(offer["request_id"])
        return True

    # ------------------------------------------------------------------ #
    async def cancel_request(self, req_id: int, passenger_id: int) -> bool:
        req = await self.db.get_request(req_id)
        if not req or req["passenger_id"] != passenger_id or req["status"] not in ("searching", "matched"):
            return False
        offer = await self.db.pending_offer_for(req_id)
        if offer and await self.db.close_offer(offer["id"], "expired"):
            await self._edit_offer_msg(offer, f"ℹ️ Yo'lovchi so'rov #{req_id} ni bekor qildi.")
        was_matched = req["status"] == "matched"
        trip_id = req["trip_id"]
        await self.db.unmatch_request(req_id, "cancelled")
        if was_matched and trip_id:
            trip = await self.db.get_trip(trip_id)
            await self._send(
                trip["driver_id"],
                f"⚠️ Yo'lovchi so'rov #{req_id} ni bekor qildi. "
                f"{req['seats']} ta o'rin yana bo'sh deb belgilandi.",
            )
            await self.on_new_trip(trip_id)
        return True

    async def close_trip(self, trip_id: int, driver_id: int, status: str) -> bool:
        """Haydovchi e'lonini yopadi (status: 'done' yoki 'cancelled')."""
        trip = await self.db.get_trip(trip_id)
        if not trip or trip["driver_id"] != driver_id or trip["status"] != "active":
            return False
        await self.db.set_trip_status(trip_id, status)
        for offer in await self.db.pending_offers_of_trip(trip_id):
            if await self.db.close_offer(offer["id"], "expired"):
                await self.dispatch_request(offer["request_id"])
        if status == "cancelled":
            # Biriktirilgan yo'lovchilar uchun boshqa haydovchi qidiramiz
            for p in await self.db.passengers_of_trip(trip_id):
                await self.db.unmatch_request(p["id"], "searching")
                await self._send(
                    p["passenger_id"],
                    f"⚠️ Haydovchi e'lonini bekor qildi. So'rov #{p['id']} uchun "
                    "boshqa haydovchi qidirilmoqda...",
                )
                await self.dispatch_request(p["id"])
        return True

    # ------------------------------------------------------------------ #
    async def housekeeping(self) -> None:
        """Javobsiz takliflarni keyingi haydovchiga o'tkazadi va eski e'lonlarni yopadi."""
        cutoff = (
            datetime.now(timezone.utc) - timedelta(minutes=self.config.offer_timeout_min)
        ).isoformat(timespec="seconds")
        for offer in await self.db.stale_offers(cutoff):
            if await self.db.close_offer(offer["id"], "expired"):
                await self._edit_offer_msg(offer, "⌛️ Javob berilmadi, so'rov boshqa haydovchiga yuborildi.")
                await self.dispatch_request(offer["request_id"])

        for req in await self.db.expire_old(today().isoformat()):
            await self._send(
                req["passenger_id"],
                f"⌛️ So'rov #{req['id']} muddati o'tdi, haydovchi topilmadi. "
                "Kerak bo'lsa yangi so'rov qoldiring.",
            )

    async def run_housekeeping_loop(self, interval_sec: int = 30) -> None:
        while True:
            try:
                await self.housekeeping()
            except Exception:  # noqa: BLE001
                log.exception("housekeeping failed")
            await asyncio.sleep(interval_sec)
