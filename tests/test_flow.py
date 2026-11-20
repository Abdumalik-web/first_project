"""Handlerlarni to'liq oqimda (haydovchi + yo'lovchi) sinash. Tarmoqqa chiqmaydi."""
import itertools
from datetime import datetime, timedelta

import pytest
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.methods import SendMessage, TelegramMethod
from aiogram.types import CallbackQuery, Chat, Contact, Location, Message, Update, User

from bot.config import Config
from bot.db import Database
from bot.handlers import setup_routers
from bot.regions import today
from bot.service import MatchService

_ids = itertools.count(1)


class RecBot(Bot):
    def __init__(self):
        super().__init__("42:TEST")
        self.calls: list[TelegramMethod] = []

    async def __call__(self, method, request_timeout=None):
        self.calls.append(method)
        if isinstance(method, SendMessage):
            return Message(message_id=next(_ids), date=datetime.now(),
                           chat=Chat(id=method.chat_id, type="private"), text=method.text)
        return True

    def texts_to(self, chat_id):
        return [m.text for m in self.calls if isinstance(m, SendMessage) and m.chat_id == chat_id]

    def last_kb(self, chat_id):
        for m in reversed(self.calls):
            if isinstance(m, SendMessage) and m.chat_id == chat_id and m.reply_markup is not None \
                    and hasattr(m.reply_markup, "inline_keyboard"):
                return m.reply_markup
        return None


@pytest.fixture
async def app(tmp_path):
    db = Database(str(tmp_path / "f.db"))
    await db.connect()
    bot = RecBot()
    cfg = Config(bot_token="42:TEST", db_path="", offer_timeout_min=5, admin_ids=())
    svc = MatchService(bot, db, cfg)
    dp = Dispatcher(storage=MemoryStorage())
    dp["db"], dp["svc"] = db, svc
    dp.include_router(setup_routers())
    yield bot, dp, db
    await db.close()


def _user(uid):
    return User(id=uid, is_bot=False, first_name=f"User{uid}", username=f"user{uid}")


def _msg(uid, **kw):
    return Message(message_id=next(_ids), date=datetime.now(), chat=Chat(id=uid, type="private"),
                   from_user=_user(uid), **kw)


async def send(bot, dp, uid, text=None, **kw):
    await dp.feed_update(bot, Update(update_id=next(_ids), message=_msg(uid, text=text, **kw)))


async def click(bot, dp, uid, data):
    cb = CallbackQuery(id=str(next(_ids)), from_user=_user(uid), chat_instance="x", data=data,
                       message=_msg(uid, text="..."))
    await dp.feed_update(bot, Update(update_id=next(_ids), callback_query=cb))


async def test_full_flow(app):
    bot, dp, db = app
    day = (today() + timedelta(days=1)).isoformat()
    D, PAX = 500, 600

    # --- Haydovchi e'lon beradi: Farg'ona -> Toshkent, Qo'qon/Dang'ara/Buvayda
    await send(bot, dp, D, "/start")
    await send(bot, dp, D, "🚗 Haydovchiman")
    await click(bot, dp, D, "dr:dir:F2T")
    for c in ("qoqon", "dangara", "buvayda"):
        await click(bot, dp, D, f"dr:fd:{c}")
    await click(bot, dp, D, "dr:fd_done")
    await click(bot, dp, D, f"dr:date:{day}")
    await click(bot, dp, D, "dr:slot:morning")
    await click(bot, dp, D, "dr:seats:4")
    await send(bot, dp, D, "Cobalt, oq, 40A123BC")
    await send(bot, dp, D, "150 000")
    await send(bot, dp, D, contact=Contact(phone_number="998901112233", first_name="D"))
    await send(bot, dp, D, location=Location(latitude=40.53, longitude=70.94))
    await click(bot, dp, D, "dr:ok")
    trips = await db.active_trips_of(D)
    assert len(trips) == 1 and trips[0]["districts"] == "qoqon,dangara,buvayda"

    # --- Yo'lovchi: Dang'aradan Chilonzorga
    await send(bot, dp, PAX, "/start")
    await send(bot, dp, PAX, "🧍 Yo'lovchiman")
    await click(bot, dp, PAX, "ps:dir:F2T")
    await click(bot, dp, PAX, "ps:fd:dangara")
    await click(bot, dp, PAX, "ps:td:chilonzor")
    await click(bot, dp, PAX, f"ps:date:{day}")
    await click(bot, dp, PAX, "ps:slot:day")
    await click(bot, dp, PAX, "ps:seats:2")
    await send(bot, dp, PAX, "⏭ O'tkazib yuborish")
    await send(bot, dp, PAX, "yukim bor")
    await send(bot, dp, PAX, "+998 90 444 55 66")
    await click(bot, dp, PAX, "ps:ok")

    assert any("Yangi yo'lovchi" in t for t in bot.texts_to(D))
    kb = bot.last_kb(D)
    accept = kb.inline_keyboard[0][0].callback_data
    assert accept.startswith("of:acc:")
    await click(bot, dp, D, accept)

    assert any("Haydovchi topildi" in t and "+998901112233" in t for t in bot.texts_to(PAX))
    assert any("+998904445566" in t for t in bot.texts_to(D))
    trip = await db.get_trip(trips[0]["id"])
    assert trip["seats_free"] == 2

    # --- "Mening e'lonlarim" va yo'lovchilar ro'yxati
    await send(bot, dp, D, "📋 Mening e'lonlarim")
    await click(bot, dp, D, f"tm:pax:{trip['id']}")
    assert any("yukim bor" in t for t in bot.texts_to(D))
