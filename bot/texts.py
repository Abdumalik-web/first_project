from __future__ import annotations

from html import escape
from typing import Any, Mapping

from .regions import DIRECTIONS, fergana_name, fmt_date, slot_name, tashkent_name

HELP = (
    "<b>Bot qanday ishlaydi?</b>\n\n"
    "🚗 <b>Haydovchi</b> e'lon beradi: yo'nalish (Farg'ona ➜ Toshkent yoki aksincha), "
    "qaysi tumanlardan yo'lovchi oladi (masalan 3–4 ta tuman), sana, vaqt va bo'sh o'rinlar.\n\n"
    "🧍 <b>Yo'lovchi</b> so'rov qoldiradi: tumani, Toshkentdagi manzili, sana, vaqt va necha kishi.\n\n"
    "🤝 Bot yo'lovchiga mos keladigan <b>eng yaqin</b> haydovchini topadi va so'rovni "
    "haydovchiga yuboradi. Haydovchi «Olaman» desa, ikkalasiga bir-birining telefon raqami "
    "yuboriladi. Rad etsa yoki javob bermasa — keyingi eng yaqin haydovchiga o'tiladi.\n\n"
    "📍 Haydovchilar «Joylashuvni yangilash» tugmasi orqali hozirgi joyini yuborsa, "
    "eng yaqin yo'lovchilar aniqroq topiladi.\n\n"
    "Buyruqlar: /start — bosh menyu, /cancel — joriy amalni bekor qilish."
)


def user_link(name: str | None, username: str | None) -> str:
    name = escape(name or "Foydalanuvchi")
    return f"{name} (@{escape(username)})" if username else name


def trip_text(t: Mapping[str, Any]) -> str:
    districts = ", ".join(fergana_name(c) for c in t["districts"].split(","))
    lines = [
        f"🚗 <b>E'lon #{t['id']}</b>",
        f"Yo'nalish: <b>{DIRECTIONS[t['direction']]}</b>",
        f"Tumanlar: {districts}",
        f"Sana: {fmt_date(t['trip_date'])}, {slot_name(t['slot'])}",
        f"Bo'sh o'rin: {t['seats_free']} / {t['seats_total']}",
    ]
    if t["car"]:
        lines.append(f"Mashina: {escape(t['car'])}")
    if t["price"]:
        lines.append(f"Narx: {escape(t['price'])}")
    lines.append("📍 Joylashuv: " + ("bor" if t["lat"] is not None else "yuborilmagan"))
    return "\n".join(lines)


def route_text(r: Mapping[str, Any]) -> str:
    f, t = fergana_name(r["fergana_code"]), tashkent_name(r["tashkent_code"])
    if r["direction"] == "F2T":
        return f"{f} ➜ Toshkent ({t})"
    return f"Toshkent ({t}) ➜ {f}"


def request_text(r: Mapping[str, Any]) -> str:
    status = {
        "searching": "🔎 haydovchi qidirilmoqda",
        "matched": "✅ haydovchi topildi",
        "cancelled": "bekor qilingan",
        "expired": "muddati o'tgan",
    }.get(r["status"], r["status"])
    lines = [
        f"🧍 <b>So'rov #{r['id']}</b> — {status}",
        f"Yo'nalish: <b>{route_text(r)}</b>",
        f"Sana: {fmt_date(r['trip_date'])}, {slot_name(r['slot'])}",
        f"Kishi soni: {r['seats']}",
    ]
    if r["comment"]:
        lines.append(f"Izoh: {escape(r['comment'])}")
    return "\n".join(lines)


def offer_text(r: Mapping[str, Any], passenger: Mapping[str, Any], distance_km: float,
               timeout_min: int, covered: bool = True) -> str:
    note = "" if covered else (
        f"ℹ️ {fergana_name(r['fergana_code'])} tumani e'loningizda yo'q, lekin siz eng yaqin haydovchisiz.\n"
    )
    return (
        "🔔 <b>Yangi yo'lovchi!</b>\n\n"
        f"{request_text(r)}\n"
        f"Yo'lovchi: {escape(passenger['full_name'] or '')}\n"
        f"📏 Sizdan taxminan <b>{distance_km:g} km</b>\n{note}\n"
        f"Olasizmi? {timeout_min} daqiqa ichida javob bering, aks holda so'rov boshqa haydovchiga o'tadi."
    )


def contact_line(u: Mapping[str, Any]) -> str:
    phone = escape(u["phone"]) if u["phone"] else "ko'rsatilmagan"
    return f"{user_link(u['full_name'], u['username'])}\n📞 {phone}"


def trip_post_text(t: Mapping[str, Any]) -> str:
    """Haydovchi e'loni guruhga joylanadigan ko'rinishda (t — trips + users ustunlari)."""
    districts = ", ".join(fergana_name(c) for c in t["districts"].split(","))
    route = f"{districts} ➜ Toshkent" if t["direction"] == "F2T" else f"Toshkent ➜ {districts}"
    lines = [
        "🚗 <b>Haydovchi e'loni</b>",
        "",
        f"🛣 <b>{route}</b>",
        f"📅 {fmt_date(t['trip_date'])}, {slot_name(t['slot'])}",
        f"💺 Bo'sh joy: <b>{t['seats_free']}</b>",
    ]
    if t["car"]:
        lines.append(f"🚘 Mashina: {escape(t['car'])}")
    if t["price"]:
        lines.append(f"💵 Narx: {escape(t['price'])}")
    lines.append("")
    if t["phone"]:
        lines.append(f"📞 {escape(t['phone'])}")
    name = escape(t["full_name"] or "Haydovchi")
    account = f'<a href="tg://user?id={t["driver_id"]}">{name}</a>'
    if t["username"]:
        account += f" — @{escape(t['username'])}"
    lines.append(f"👤 {account}")
    return "\n".join(lines)
