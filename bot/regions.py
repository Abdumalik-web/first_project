"""Yo'nalish, tuman va vaqt oraliqlari.

Koordinatalar tuman markazlarining taxminiy nuqtalari. Ular faqat
"eng yaqin" haydovchini aniqlash uchun ishlatiladi; foydalanuvchi o'z
joylashuvini (lokatsiya) yuborsa, aniq nuqta ishlatiladi.
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Tashkent")


def today() -> date:
    """O'zbekiston vaqti bo'yicha bugungi sana (server qaysi mintaqada bo'lishidan qat'i nazar)."""
    return datetime.now(TZ).date()


# Yo'nalishlar
TO_TASHKENT = "F2T"  # Farg'ona -> Toshkent
FROM_TASHKENT = "T2F"  # Toshkent -> Farg'ona

DIRECTIONS = {
    TO_TASHKENT: "Farg'ona ➜ Toshkent",
    FROM_TASHKENT: "Toshkent ➜ Farg'ona",
}

# Farg'ona viloyati shahar va tumanlari: kod -> (nomi, lat, lon)
FERGANA: dict[str, tuple[str, float, float]] = {
    "fargona_sh": ("Farg'ona sh.", 40.3864, 71.7864),
    "margilon": ("Marg'ilon", 40.4711, 71.7247),
    "qoqon": ("Qo'qon", 40.5286, 70.9425),
    "quvasoy": ("Quvasoy", 40.2972, 71.9800),
    "oltiariq": ("Oltiariq", 40.3906, 71.4747),
    "bagdod": ("Bag'dod", 40.4600, 71.2167),
    "beshariq": ("Beshariq", 40.4358, 70.6103),
    "buvayda": ("Buvayda", 40.6200, 71.0500),
    "dangara": ("Dang'ara", 40.5833, 70.9167),
    "fargona_t": ("Farg'ona t.", 40.1806, 71.7275),
    "furqat": ("Furqat", 40.5600, 70.7800),
    "qoshtepa": ("Qo'shtepa", 40.5000, 71.6300),
    "quva": ("Quva", 40.5228, 72.0711),
    "rishton": ("Rishton", 40.3567, 71.2847),
    "sox": ("So'x", 39.9667, 71.1333),
    "toshloq": ("Toshloq", 40.4747, 71.7678),
    "uchkoprik": ("Uchko'prik", 40.5333, 71.0500),
    "ozbekiston": ("O'zbekiston", 40.3667, 70.8333),
    "yozyovon": ("Yozyovon", 40.6575, 71.7436),
}

# Toshkent shahri tumanlari
TASHKENT: dict[str, tuple[str, float, float]] = {
    "bektemir": ("Bektemir", 41.2090, 69.3340),
    "chilonzor": ("Chilonzor", 41.2730, 69.2040),
    "mirobod": ("Mirobod", 41.2890, 69.2900),
    "mirzo_ulugbek": ("Mirzo Ulug'bek", 41.3380, 69.3350),
    "olmazor": ("Olmazor", 41.3540, 69.2150),
    "sergeli": ("Sergeli", 41.2270, 69.2220),
    "shayxontohur": ("Shayxontohur", 41.3260, 69.2290),
    "uchtepa": ("Uchtepa", 41.2870, 69.1710),
    "yakkasaroy": ("Yakkasaroy", 41.2880, 69.2580),
    "yashnobod": ("Yashnobod", 41.3000, 69.3380),
    "yunusobod": ("Yunusobod", 41.3640, 69.2850),
    "yangihayot": ("Yangihayot", 41.2050, 69.2600),
}

# Vaqt oraliqlari: kod -> (nomi, tartib raqami)
TIME_SLOTS: dict[str, tuple[str, int]] = {
    "morning": ("🌅 Ertalab (05:00–09:00)", 0),
    "day": ("☀️ Kunduzi (09:00–14:00)", 1),
    "evening": ("🌇 Kechqurun (14:00–20:00)", 2),
    "night": ("🌙 Tunda (20:00–05:00)", 3),
}


def fergana_name(code: str) -> str:
    return FERGANA[code][0] if code in FERGANA else code


def tashkent_name(code: str) -> str:
    return TASHKENT[code][0] if code in TASHKENT else code


def slot_name(code: str) -> str:
    return TIME_SLOTS[code][0] if code in TIME_SLOTS else code


def slot_distance(a: str, b: str) -> int:
    """Ikki vaqt oralig'i orasidagi farq (0 = bir xil, 1 = qo'shni ...)."""
    return abs(TIME_SLOTS[a][1] - TIME_SLOTS[b][1])


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def nearest_district(table: dict[str, tuple[str, float, float]], lat: float, lon: float) -> str:
    """Berilgan nuqtaga eng yaqin tuman kodi."""
    return min(table, key=lambda c: haversine_km(lat, lon, table[c][1], table[c][2]))


def date_options(base: date | None = None) -> list[tuple[str, str]]:
    """Bugun, ertaga, indinga sanalari: [(iso, label), ...]."""
    base = base or today()
    labels = ["Bugun", "Ertaga", "Indinga"]
    out = []
    for i, lbl in enumerate(labels):
        d = base + timedelta(days=i)
        out.append((d.isoformat(), f"{lbl} ({d.strftime('%d.%m')})"))
    return out


def fmt_date(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{d}.{m}.{y}"
