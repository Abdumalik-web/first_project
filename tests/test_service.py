"""Taqsimlash oqimini soxta Bot bilan tekshirish."""
from types import SimpleNamespace

import pytest

from bot.config import Config
from bot.db import Database
from bot.service import MatchService

DAY = "2026-11-21"


class FakeBot:
    def __init__(self):
        self.sent = []  # (chat_id, text, reply_markup)
        self._mid = 0

    async def send_message(self, chat_id, text, reply_markup=None, **kw):
        self._mid += 1
        self.sent.append((chat_id, text, reply_markup))
        return SimpleNamespace(message_id=self._mid)

    async def send_location(self, *a, **kw):
        return None

    async def edit_message_reply_markup(self, **kw):
        return None

    def to(self, chat_id):
        return [t for c, t, _ in self.sent if c == chat_id]

    def last_offer_id(self, chat_id):
        for c, _, kb in reversed(self.sent):
            if c == chat_id and kb is not None:
                return int(kb.inline_keyboard[0][0].callback_data.split(":")[2])
        return None


@pytest.fixture
async def env(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    await db.connect()
    bot = FakeBot()
    cfg = Config(bot_token="x", db_path="", offer_timeout_min=5, admin_ids=())
    svc = MatchService(bot, db, cfg)
    for uid in (1, 2, 10, 11):
        await db.upsert_user(uid, f"U{uid}", None)
        await db.set_phone(uid, f"+99890000{uid:04d}")
    yield db, bot, svc
    await db.close()


async def test_offer_goes_to_nearest_then_next_on_reject(env):
    db, bot, svc = env
    # 10 — Farg'onada, 11 — Qo'qonda; ikkalasi ham Qo'qondan oladi
    await db.create_trip(10, "F2T", ["fargona_sh", "qoqon"], DAY, "morning", 4, "Cobalt", "150k", None, None)
    await db.create_trip(11, "F2T", ["qoqon", "dangara"], DAY, "morning", 4, "Nexia", "140k", None, None)
    rid = await db.create_request(1, "F2T", "qoqon", "chilonzor", None, None, DAY, "morning", 2, None)

    assert await svc.dispatch_request(rid)
    oid = bot.last_offer_id(11)
    assert oid is not None and bot.last_offer_id(10) is None

    assert await svc.reject(oid, 11)
    oid2 = bot.last_offer_id(10)
    assert oid2 is not None

    assert await svc.accept(oid2, 10) == "ok"
    r = await db.get_request(rid)
    t = await db.get_trip(r["trip_id"])
    assert r["status"] == "matched" and t["driver_id"] == 10 and t["seats_free"] == 2
    assert any("+998900000010" in m for m in bot.to(1))  # yo'lovchi haydovchi raqamini oldi
    assert any("+998900000001" in m for m in bot.to(10))


async def test_waiting_request_dispatched_when_trip_appears(env):
    db, bot, svc = env
    rid = await db.create_request(1, "T2F", "rishton", "yunusobod", None, None, DAY, "evening", 1, None)
    assert not await svc.dispatch_request(rid)
    assert any("topilmadi" in m for m in bot.to(1))

    tid = await db.create_trip(10, "T2F", ["rishton", "bagdod"], DAY, "day", 3, "Gentra", None, None, None)
    assert await svc.on_new_trip(tid) == 1
    assert bot.last_offer_id(10) is not None


async def test_double_accept_and_cancel_restores_seat(env):
    db, bot, svc = env
    tid = await db.create_trip(10, "F2T", ["quva"], DAY, "morning", 1, None, None, None, None)
    r1 = await db.create_request(1, "F2T", "quva", "mirobod", None, None, DAY, "morning", 1, None)
    r2 = await db.create_request(2, "F2T", "quva", "mirobod", None, None, DAY, "morning", 1, None)
    await svc.dispatch_request(r1)
    o1 = bot.last_offer_id(10)
    await svc.dispatch_request(r2)
    o2 = bot.last_offer_id(10)
    assert o1 != o2
    assert await svc.accept(o1, 10) == "ok"
    assert await svc.accept(o1, 10) == "closed"
    assert await svc.accept(o2, 10) == "no_seats"
    assert (await db.get_trip(tid))["seats_free"] == 0

    # Yo'lovchi 1 bekor qilsa — o'rin bo'shaydi va 2-yo'lovchi qayta taklif qilinadi
    await db.execute("UPDATE requests SET wait_notified=0 WHERE id=?", r2)
    assert await svc.cancel_request(r1, 1)
    assert (await db.get_trip(tid))["seats_free"] == 1
    o3 = bot.last_offer_id(10)
    assert o3 not in (o1, o2)
    assert await svc.accept(o3, 10) == "ok"
    assert (await db.get_request(r2))["status"] == "matched"


async def test_driver_cannot_answer_foreign_offer(env):
    db, bot, svc = env
    await db.create_trip(10, "F2T", ["quva"], DAY, "morning", 4, None, None, None, None)
    rid = await db.create_request(1, "F2T", "quva", "mirobod", None, None, DAY, "morning", 1, None)
    await svc.dispatch_request(rid)
    oid = bot.last_offer_id(10)
    assert await svc.accept(oid, 11) == "closed"
    assert not await svc.reject(oid, 11)
