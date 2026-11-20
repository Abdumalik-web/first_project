"""Haydovchi va yo'lovchini moslashtirish (sof funksiyalar, test qilish oson).

Qoidalar:
  * yo'nalish va sana bir xil bo'lishi kerak;
  * haydovchida yetarli bo'sh o'rin bo'lishi kerak;
  * vaqt oralig'i bir xil yoki qo'shni bo'lishi kerak.
Tuman qat'iy shart emas: Toshkentdan chiqqan yo'lovchi Toshkentdagi, Farg'onadan
chiqqan yo'lovchi Farg'onadagi eng yaqin haydovchiga yuboriladi. Yo'lovchining
tumani haydovchi tanlagan tumanlar ichida bo'lsa, u haydovchi ustun turadi.
Ball: olib ketish nuqtasi bilan haydovchining joylashuvi orasidagi masofa
+ vaqt farqi uchun jarima + tuman mos kelmasa jarima.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .regions import (
    FERGANA,
    TASHKENT,
    TO_TASHKENT,
    haversine_km,
    slot_distance,
)

TASHKENT_CENTER = (41.3111, 69.2797)

# Vaqt oralig'i bitta farq qilsa, uni shuncha km masofaga teng deb hisoblaymiz
SLOT_PENALTY_KM = 40.0
MAX_SLOT_DIFF = 1
# Yo'lovchining tumani haydovchi e'lonida bo'lmasa — shuncha km qo'shiladi
UNCOVERED_PENALTY_KM = 20.0


@dataclass(frozen=True)
class Match:
    trip_id: int
    distance_km: float
    score: float
    covered: bool = True  # yo'lovchining tumani haydovchi e'lonida bormi


def pickup_point(req: Mapping[str, Any]) -> tuple[float, float]:
    """Yo'lovchini olib ketish nuqtasi."""
    if req["lat"] is not None and req["lon"] is not None:
        return req["lat"], req["lon"]
    if req["direction"] == TO_TASHKENT:
        _, lat, lon = FERGANA[req["fergana_code"]]
    else:
        _, lat, lon = TASHKENT[req["tashkent_code"]]
    return lat, lon


def driver_point(trip: Mapping[str, Any]) -> tuple[float, float]:
    """Haydovchining joriy (yoki taxminiy) joylashuvi."""
    if trip["lat"] is not None and trip["lon"] is not None:
        return trip["lat"], trip["lon"]
    if trip["direction"] == TO_TASHKENT:
        # Lokatsiya yo'q bo'lsa — birinchi tanlangan tuman haydovchining bazasi deb olinadi
        first = trip["districts"].split(",")[0]
        _, lat, lon = FERGANA[first]
        return lat, lon
    return TASHKENT_CENTER


def is_compatible(req: Mapping[str, Any], trip: Mapping[str, Any]) -> bool:
    return (
        trip["status"] == "active"
        and trip["direction"] == req["direction"]
        and trip["trip_date"] == req["trip_date"]
        and trip["driver_id"] != req["passenger_id"]
        and trip["seats_free"] >= req["seats"]
        and slot_distance(trip["slot"], req["slot"]) <= MAX_SLOT_DIFF
    )


def score(req: Mapping[str, Any], trip: Mapping[str, Any]) -> Match:
    plat, plon = pickup_point(req)
    dlat, dlon = driver_point(trip)
    dist = haversine_km(plat, plon, dlat, dlon)
    covered = req["fergana_code"] in trip["districts"].split(",")
    s = dist + SLOT_PENALTY_KM * slot_distance(trip["slot"], req["slot"])
    if not covered:
        s += UNCOVERED_PENALTY_KM
    return Match(trip_id=trip["id"], distance_km=round(dist, 1), score=s, covered=covered)


def rank_trips(
    req: Mapping[str, Any],
    trips: Iterable[Mapping[str, Any]],
    exclude_trip_ids: set[int] | frozenset[int] = frozenset(),
) -> list[Match]:
    """Mos haydovchilarni eng yaqinidan boshlab tartiblaydi."""
    out = [
        score(req, t)
        for t in trips
        if t["id"] not in exclude_trip_ids and is_compatible(req, t)
    ]
    out.sort(key=lambda m: (m.score, m.trip_id))
    return out


def rank_trips_for_lead(
    direction: str,
    fergana_code: str,
    tashkent_code: str | None,
    slot: str | None,
    seats: int | None,
    trips: Iterable[Mapping[str, Any]],
) -> list[Match]:
    """Guruhdan topilgan yo'lovchi uchun mos e'lonlar (sana oldindan filtrlangan)."""
    if direction == TO_TASHKENT:
        _, plat, plon = FERGANA[fergana_code]
    elif tashkent_code:
        _, plat, plon = TASHKENT[tashkent_code]
    else:
        plat, plon = TASHKENT_CENTER
    out = []
    for t in trips:
        if t["status"] != "active" or t["direction"] != direction:
            continue
        if seats and t["seats_free"] < seats:
            continue
        diff = slot_distance(t["slot"], slot) if slot else 0
        if diff > MAX_SLOT_DIFF:
            continue
        dlat, dlon = driver_point(t)
        dist = haversine_km(plat, plon, dlat, dlon)
        covered = fergana_code in t["districts"].split(",")
        sc = dist + SLOT_PENALTY_KM * diff + (0 if covered else UNCOVERED_PENALTY_KM)
        out.append(Match(trip_id=t["id"], distance_km=round(dist, 1), score=sc, covered=covered))
    out.sort(key=lambda m: (m.score, m.trip_id))
    return out
