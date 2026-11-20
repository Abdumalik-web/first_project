import pytest

from bot.group_parser import parse

PASSENGERS = [
    # (xabar, yo'nalish, tuman, kun, vaqt, kishi, telefon)
    ("Ertaga Qo'qondan Toshkentga 2 kishi kerak 90 123 45 67",
     "F2T", "qoqon", 1, None, 2, "+998901234567"),
    ("Toshkentdan Rishtonga bugun kechqurun 1 kishi bor. +998 93 555 66 77",
     "T2F", "rishton", 0, "evening", 1, "+998935556677"),
    ("Тошкентдан Қўқонга эртага эрталаб 3 киши керак",
     "T2F", "qoqon", 1, "morning", 3, None),
    ("Нужно такси из Ташкента в Коканд завтра утром, 2 человека",
     "T2F", "qoqon", 1, "morning", 2, None),
    ("Marg'ilondan Toshkent Chilonzorga ikki kishi mashina kerak",
     "F2T", "margilon", None, None, 2, None),
    ("Beshariq - Toshkent 1 odam kerak (97)1112233",
     "F2T", "beshariq", None, None, 1, "+998971112233"),
    ("Dang'aradan toshkentga ketaman srochno",
     "F2T", "dangara", 0, None, None, None),
]

DRIVERS_OR_NOISE = [
    "Qo'qondan Toshkentga ketyapmiz, 3 ta joy bor, Cobalt. 90 111 22 33",
    "Toshkentdan Farg'onaga olib ketamiz, 2 joy qoldi",
    "Едем из Ташкента в Коканд, есть место",
    "Assalomu alaykum hammaga",
    "Qo'qonda bugun havo yaxshi, 2 kishi kerak emas",  # Toshkent tilga olinmagan
    "Toshkentga 2 kishi kerak",  # Farg'ona tumani aytilmagan
]


@pytest.mark.parametrize("text,direction,code,day,slot,seats,phone", PASSENGERS)
def test_passenger_messages(text, direction, code, day, slot, seats, phone):
    lead = parse(text)
    assert lead is not None, text
    assert lead.direction == direction
    assert lead.fergana_code == code
    assert lead.day_offset == day
    assert lead.slot == slot
    assert lead.seats == seats
    assert (lead.phones[0] if lead.phones else None) == phone


@pytest.mark.parametrize("text", DRIVERS_OR_NOISE)
def test_not_passenger(text):
    assert parse(text) is None


def test_tashkent_district_and_username():
    lead = parse("Toshkent Yunusoboddan Quvaga 1 kishi kerak @ali_valiyev")
    assert lead.direction == "T2F" and lead.fergana_code == "quva"
    assert lead.tashkent_code == "yunusobod"
    assert lead.usernames == ["ali_valiyev"]


def test_quvasoy_not_quva():
    assert parse("Quvasoydan Toshkentga 1 kishi kerak").fergana_code == "quvasoy"
