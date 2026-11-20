from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from .regions import DIRECTIONS, FERGANA, TASHKENT, TIME_SLOTS, date_options

# Asosiy menyu tugmalari
BTN_DRIVER = "🚗 Haydovchiman"
BTN_PASSENGER = "🧍 Yo'lovchiman"
BTN_MY = "📋 Mening e'lonlarim"
BTN_HELP = "ℹ️ Yordam"
BTN_LOCATION = "📍 Joylashuvni yangilash"
BTN_CANCEL = "❌ Bekor qilish"
BTN_SKIP = "⏭ O'tkazib yuborish"
BTN_SEND_LOC = "📍 Joylashuvni yuborish"
BTN_SEND_PHONE = "📱 Telefon raqamni yuborish"


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_DRIVER), KeyboardButton(text=BTN_PASSENGER)],
            [KeyboardButton(text=BTN_MY), KeyboardButton(text=BTN_HELP)],
            [KeyboardButton(text=BTN_LOCATION, request_location=True)],
        ],
        resize_keyboard=True,
    )


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BTN_CANCEL)]], resize_keyboard=True)


def skip_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_SKIP)], [KeyboardButton(text=BTN_CANCEL)]],
        resize_keyboard=True,
    )


def location_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_SEND_LOC, request_location=True)],
            [KeyboardButton(text=BTN_SKIP)],
            [KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
    )


def phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_SEND_PHONE, request_contact=True)],
            [KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
    )


def _grid(buttons: list[InlineKeyboardButton], cols: int) -> list[list[InlineKeyboardButton]]:
    return [buttons[i : i + cols] for i in range(0, len(buttons), cols)]


def direction_kb(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=name, callback_data=f"{prefix}:dir:{code}")]
            for code, name in DIRECTIONS.items()
        ]
    )


def fergana_kb(prefix: str, selected: set[str] | None = None, multi: bool = False) -> InlineKeyboardMarkup:
    selected = selected or set()
    btns = [
        InlineKeyboardButton(
            text=("✅ " if code in selected else "") + name,
            callback_data=f"{prefix}:fd:{code}",
        )
        for code, (name, _, _) in FERGANA.items()
    ]
    rows = _grid(btns, 3)
    if multi:
        rows.append([InlineKeyboardButton(text="➡️ Tayyor", callback_data=f"{prefix}:fd_done")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def tashkent_kb(prefix: str) -> InlineKeyboardMarkup:
    btns = [
        InlineKeyboardButton(text=name, callback_data=f"{prefix}:td:{code}")
        for code, (name, _, _) in TASHKENT.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=_grid(btns, 3))


def date_kb(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"{prefix}:date:{iso}")]
            for iso, label in date_options()
        ]
    )


def slot_kb(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=name, callback_data=f"{prefix}:slot:{code}")]
            for code, (name, _) in TIME_SLOTS.items()
        ]
    )


def seats_kb(prefix: str, max_seats: int) -> InlineKeyboardMarkup:
    btns = [
        InlineKeyboardButton(text=str(i), callback_data=f"{prefix}:seats:{i}")
        for i in range(1, max_seats + 1)
    ]
    return InlineKeyboardMarkup(inline_keyboard=_grid(btns, 4))


def confirm_kb(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"{prefix}:ok"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"{prefix}:no"),
            ]
        ]
    )


def offer_kb(offer_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Olaman", callback_data=f"of:acc:{offer_id}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"of:rej:{offer_id}"),
            ]
        ]
    )


def trip_manage_kb(trip_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 Yo'lovchilarim", callback_data=f"tm:pax:{trip_id}")],
            [
                InlineKeyboardButton(text="🏁 Yo'lga chiqdim / yakunlash", callback_data=f"tm:done:{trip_id}"),
            ],
            [InlineKeyboardButton(text="🗑 E'lonni bekor qilish", callback_data=f"tm:cancel:{trip_id}")],
        ]
    )


def request_manage_kb(req_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗑 So'rovni bekor qilish", callback_data=f"rm:cancel:{req_id}")]
        ]
    )
