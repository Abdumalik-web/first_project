"""Haydovchi va yo'lovchini moslashtirish (sof funksiyalar, test qilish oson).

Qoidalar:
  * yo'nalish va sana bir xil bo'lishi kerak;
  * yo'lovchining Farg'ona tumani haydovchi yuradigan tumanlar ichida bo'lishi kerak;
  * haydovchida yetarli bo'sh o'rin bo'lishi kerak;
  * vaqt oralig'i bir xil yoki qo'shni bo'lishi kerak.
Mos kelganlar orasida eng yaqini tanlanadi: olib ketish nuqtasi bilan
haydovchining joylashuvi orasidagi masofa + vaqt farqi uchun jarima.
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


@dataclass(frozen=True)
class Match:
    trip_id: int
    distance_km: float
    score: float


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
        and req["fergana_code"] in trip["districts"].split(",")
        and slot_distance(trip["slot"], req["slot"]) <= MAX_SLOT_DIFF
    )


def score(req: Mapping[str, Any], trip: Mapping[str, Any]) -> Match:
    plat, plon = pickup_point(req)
    dlat, dlon = driver_point(trip)
    dist = haversine_km(plat, plon, dlat, dlon)
    s = dist + SLOT_PENALTY_KM * slot_distance(trip["slot"], req["slot"])
    return Match(trip_id=trip["id"], distance_km=round(dist, 1), score=s)


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
