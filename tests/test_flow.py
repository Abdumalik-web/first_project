"""Handlerlarni to'liq oqimda (haydovchi + yo'lovchi) sinash. Tarmoqqa chiqmaydi."""
import itertools
from datetime import datetime, timedelta

import pytest
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.methods import CopyMessage, SendMessage, TelegramMethod
from aiogram.types import CallbackQuery, Chat, Contact, Location, Message, Update, User

from bot.config import Config
from bot.db import Database
from bot.handlers import setup_routers
from bot.middlewares import BanMiddleware
from bot.regions import today
from bot.service import MatchService

_ids = itertools.count(1)


class RecBot(Bot):
    def __init__(self):
        super().__init__("42:TEST")
        self.calls: list[TelegramMethod] = []

    admin_chats: set = set()

    async def __call__(self, method, request_timeout=None):
        self.calls.append(method)
        from aiogram.methods import GetChatMember, GetMe
        from types import SimpleNamespace
        if isinstance(method, GetMe):
            return User(id=42, is_bot=True, first_name="Bot", username="testbot")
        if isinstance(method, GetChatMember):
            return SimpleNamespace(status="administrator" if method.chat_id in self.admin_chats else "member")
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
    cfg = Config(bot_token="42:TEST", db_path="", offer_timeout_min=5, admin_ids=(900,))
    svc = MatchService(bot, db, cfg)
    dp = Dispatcher(storage=MemoryStorage())
    from bot.ads import AdService
    dp["db"], dp["svc"], dp["config"], dp["ads"] = db, svc, cfg, AdService(bot, db)
    dp.message.outer_middleware(BanMiddleware())
    dp.callback_query.outer_middleware(BanMiddleware())
    dp.include_router(setup_routers())
    yield bot, dp, db
    await db.close()
    # Modul darajasidagi routerlarni keyingi test uchun ajratamiz
    from bot.handlers import admin, common, driver, group, handover, offers, passenger, voice
    for m in (admin, common, driver, group, handover, offers, passenger, voice):
        m.router._parent_router = None


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
    assert "guruhlarga ham joylanadi" in bot.texts_to(D)[-1]
    await click(bot, dp, D, "dr:ok")
    assert (await db.active_trips_of(D))[0]["publish"] == 1
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
    assert sum("Guruhimizga qo'shiling" in t for t in bot.texts_to(PAX)) == 1

    assert any("Yangi yo'lovchi" in t for t in bot.texts_to(D))
    kb = bot.last_kb(D)
    accept = kb.inline_keyboard[0][0].callback_data
    assert accept.startswith("of:acc:")
    await click(bot, dp, D, accept)

    assert any("Haydovchi topildi" in t and "+998901112233" in t for t in bot.texts_to(PAX))
    assert any("+998904445566" in t for t in bot.texts_to(D))
    trip = await db.get_trip(trips[0]["id"])
    assert trip["seats_free"] == 2

    # Ikkinchi so'rovda havola qayta yuborilmaydi
    await send(bot, dp, PAX, "🧍 Yo'lovchiman")
    for d in ("ps:dir:T2F", "ps:fd:quva", "ps:td:yunusobod", f"ps:date:{day}", "ps:slot:day", "ps:seats:1"):
        await click(bot, dp, PAX, d)
    await send(bot, dp, PAX, "⏭ O'tkazib yuborish")
    await send(bot, dp, PAX, "⏭ O'tkazib yuborish")
    await click(bot, dp, PAX, "ps:ok")
    assert sum("Guruhimizga qo'shiling" in t for t in bot.texts_to(PAX)) == 1

    # --- "Mening e'lonlarim" va yo'lovchilar ro'yxati
    await send(bot, dp, D, "📋 Mening e'lonlarim")
    await click(bot, dp, D, f"tm:pax:{trip['id']}")
    assert any("yukim bor" in t for t in bot.texts_to(D))


async def test_admin_panel(app):
    bot, dp, db = app
    ADMIN, U1, U2 = 900, 701, 702
    for uid in (ADMIN, U1, U2):
        await send(bot, dp, uid, "/start")

    # Oddiy foydalanuvchi admin panelni ko'rmaydi
    n = len(bot.texts_to(U1))
    await send(bot, dp, U1, "/admin")
    assert len(bot.texts_to(U1)) == n

    await send(bot, dp, ADMIN, "/admin")
    assert any("Admin panel" in t for t in bot.texts_to(ADMIN))
    await click(bot, dp, ADMIN, "adm:stats")
    assert any("Foydalanuvchilar: <b>3</b>" in t for t in bot.texts_to(ADMIN))
    await click(bot, dp, ADMIN, "adm:groups")
    assert any("Kuzatilayotgan guruhlar" in t for t in bot.texts_to(ADMIN))

    # Xabar tarqatish
    await click(bot, dp, ADMIN, "adm:bc")
    await send(bot, dp, ADMIN, "Yangilik!")
    await click(bot, dp, ADMIN, "adm:bc_ok")
    copied = {m.chat_id for m in bot.calls if isinstance(m, CopyMessage)}
    assert copied == {ADMIN, U1, U2}

    # Bloklash
    await send(bot, dp, ADMIN, f"/ban {U2}")
    assert await db.is_banned(U2)
    await send(bot, dp, U2, "🧍 Yo'lovchiman")
    assert "bloklangansiz" in bot.texts_to(U2)[-1]
    await send(bot, dp, ADMIN, f"/unban {U2}")
    assert not await db.is_banned(U2)

    await send(bot, dp, ADMIN, "/reklama_vaqt 30")
    assert "30 daqiqada" in bot.texts_to(ADMIN)[-1]
    await send(bot, dp, ADMIN, "/reklama_matn2 Yangi reklama matni")
    await click(bot, dp, ADMIN, "adm:ads")
    assert "Yangi reklama matni" in bot.texts_to(ADMIN)[-1] and "Har <b>30</b>" in bot.texts_to(ADMIN)[-1]

    await send(bot, dp, ADMIN, "/guruh_link")
    assert "toshken_fargonaa_taksi" in bot.texts_to(ADMIN)[-1]
    await send(bot, dp, ADMIN, "/guruh_link https://t.me/yangi_guruh")
    assert await db.get_setting("group_link", "") == "https://t.me/yangi_guruh"
    await send(bot, dp, ADMIN, "/guruh_link https://t.me/toshken_fargonaa_taksi")

    await send(bot, dp, ADMIN, "/tekshir Ertaga Qo'qondan Toshkentga 2 kishi kerak")
    assert "tanildi" in bot.texts_to(ADMIN)[-1]
    await send(bot, dp, ADMIN, "/tekshir Toshkentga ketyapmiz joy bor")
    assert "tanimadi" in bot.texts_to(ADMIN)[-1]

    await send(bot, dp, U1, "/id")
    assert str(U1) in bot.texts_to(U1)[-1]


# --- Ovozli xabar ------------------------------------------------------------
class FakeParser:
    """Tarmoqqa chiqmaydigan soxta ovoz xizmati."""

    def __init__(self, text, data):
        self.text, self.data = text, data

    async def transcribe(self, audio, filename="voice.ogg"):
        assert audio == b"OGG"
        return self.text

    async def extract(self, text, today_):
        from bot.voice import to_parsed
        return to_parsed(self.data, today_)


def _voice_data(**kw):
    base = dict(role="unknown", direction="unknown", fergana_districts=[], tashkent_district="unknown",
                date="unknown", slot="unknown", seats=0, car="", price="", comment="")
    base.update(kw)
    return base


async def send_voice(bot, dp, uid):
    from aiogram.types import Voice
    v = Voice(file_id="f", file_unique_id="u", duration=5)
    await send(bot, dp, uid, voice=v)


async def test_voice_passenger_fills_only_missing(app, monkeypatch):
    bot, dp, db = app
    monkeypatch.setattr(RecBot, "download", lambda self, *a, **k: _bytes(), raising=False)
    dp["voice_parser"] = FakeParser(
        "Ertaga ertalab Qo'qondan Toshkentga Chilonzorga ikki kishimiz",
        _voice_data(role="passenger", direction="F2T", fergana_districts=["qoqon"],
                    tashkent_district="chilonzor", date="tomorrow", slot="morning", seats=2),
    )
    PAX = 801
    await send(bot, dp, PAX, "/start")
    await send(bot, dp, PAX, "+998901112200")  # telefon hali yo'q — keyin so'raladi
    await send_voice(bot, dp, PAX)
    out = bot.texts_to(PAX)
    assert any("Siz aytdingiz" in t for t in out)
    # Barcha asosiy ma'lumot ovozdan olindi — faqat lokatsiya so'raladi
    assert "lokatsiya" in out[-1]
    await send(bot, dp, PAX, "⏭ O'tkazib yuborish")
    assert "Telefon" in bot.texts_to(PAX)[-1]
    await send(bot, dp, PAX, "+998901112200")
    assert "Qo'qon ➜ Toshkent (Chilonzor)" in bot.texts_to(PAX)[-1]
    assert "Kishi soni: 2" in bot.texts_to(PAX)[-1]
    await click(bot, dp, PAX, "ps:ok")
    reqs = await db.open_requests_of(PAX)
    assert len(reqs) == 1 and reqs[0]["fergana_code"] == "qoqon" and reqs[0]["seats"] == 2


async def test_voice_driver_asks_missing_and_role(app, monkeypatch):
    bot, dp, db = app
    monkeypatch.setattr(RecBot, "download", lambda self, *a, **k: _bytes(), raising=False)
    dp["voice_parser"] = FakeParser(
        "Bugun kechqurun Toshkentdan Qo'qon Dang'ara tomonga uchta joy bor",
        _voice_data(direction="T2F", fergana_districts=["qoqon", "dangara"], date="today",
                    slot="evening", seats=3),
    )
    D = 802
    await send(bot, dp, D, "/start")
    await send_voice(bot, dp, D)
    assert "haydovchimisiz" in bot.texts_to(D)[-1]  # rol aniq emas — so'raladi
    await click(bot, dp, D, "vc:role:driver")
    assert "Mashinangiz" in bot.texts_to(D)[-1]  # yo'nalish/tuman/sana/vaqt/o'rin ovozdan olindi


async def test_voice_disabled_message(app):
    bot, dp, db = app
    dp["voice_parser"] = None
    await send_voice(bot, dp, 803)
    assert "hozircha ishlamaydi" in bot.texts_to(803)[-1]


def _bytes():
    import io

    async def _f():
        return io.BytesIO(b"OGG")
    return _f()


# --- Guruhlar ----------------------------------------------------------------
async def group_msg(bot, dp, chat_id, uid, text, title="Taksi Qo'qon-Toshkent", username=None):
    m = Message(message_id=next(_ids), date=datetime.now(),
                chat=Chat(id=chat_id, type="supergroup", title=title, username=username),
                from_user=_user(uid), text=text)
    await dp.feed_update(bot, Update(update_id=next(_ids), message=m))


async def test_group_lead_forwarded_to_matching_driver(app):
    bot, dp, db = app
    tomorrow = (today() + timedelta(days=1)).isoformat()
    D1, D2, D_OTHER = 901, 902, 903
    for d in (D1, D2, D_OTHER):
        await db.upsert_user(d, f"D{d}", None)
    await db.create_trip(D1, "F2T", ["qoqon", "dangara"], tomorrow, "morning", 4, "Cobalt", None, None, None)
    await db.create_trip(D2, "F2T", ["fargona_sh", "qoqon"], tomorrow, "morning", 4, None, None, None, None)
    await db.create_trip(D_OTHER, "F2T", ["quva"], tomorrow, "morning", 4, None, None, None, None)

    G1, G2, PAX = -1001234567890, -1009999999999, 950
    await group_msg(bot, dp, G1, PAX, "Ertaga ertalab Qo'qondan Toshkentga 2 kishi kerak 90 123 45 67")

    # Bot guruhga hech narsa yozmaydi
    assert bot.texts_to(G1) == []
    d1 = bot.texts_to(D1)
    assert d1 and "Guruhdan yo'lovchi" in d1[-1] and "+998901234567" in d1[-1]
    assert "Qo'qon ➜ Toshkent" in d1[-1]
    assert bot.texts_to(D2)  # u ham Qo'qonni oladi
    # Quvadagi haydovchi ham oladi (tuman shart emas), lekin oxirida va ogohlantirish bilan
    assert bot.texts_to(D_OTHER) and "e'loningizda yo'q" in bot.texts_to(D_OTHER)[-1]
    order = [m.chat_id for m in bot.calls if isinstance(m, SendMessage) and m.chat_id in (D1, D2, D_OTHER)]
    assert order[-1] == D_OTHER
    # Eng yaqin haydovchi birinchi (D1 bazasi Qo'qon, D2 bazasi Farg'ona)
    first = next(m.chat_id for m in bot.calls if isinstance(m, SendMessage) and m.chat_id in (D1, D2))
    assert first == D1
    # Xabarga havola: https://t.me/c/1234567890/<id>
    kb = next(m.reply_markup for m in bot.calls if isinstance(m, SendMessage) and m.chat_id == D1)
    assert kb.inline_keyboard[0][0].url.startswith("https://t.me/c/1234567890/")

    # Shu e'lon boshqa guruhga ham tashlansa — qayta yuborilmaydi
    n = len(bot.texts_to(D1))
    await group_msg(bot, dp, G2, PAX, "Ertaga ertalab Qo'qondan Toshkentga 2 kishi kerak 90 123 45 67")
    assert len(bot.texts_to(D1)) == n

    # Haydovchining e'loni va oddiy gaplar e'tiborsiz qoladi
    await group_msg(bot, dp, G1, 951, "Qo'qondan Toshkentga ketyapmiz 3 joy bor Cobalt")
    await group_msg(bot, dp, G1, 952, "/start")
    assert len(bot.texts_to(D1)) == n
    assert bot.texts_to(G1) == [] and bot.texts_to(G2) == []

    s = await db.group_stats(datetime.now().date().isoformat())
    assert s["groups"] == 2 and s["leads_total"] == 1



async def test_group_ads(app):
    from aiogram.methods import DeleteMessage
    from bot.ads import AdService
    bot, dp, db = app
    ads = AdService(bot, db)
    G_ADMIN, G_MEMBER = -1001111111111, -1002222222222
    bot.admin_chats = {G_ADMIN}
    await group_msg(bot, dp, G_ADMIN, 960, "Salom")
    await group_msg(bot, dp, G_MEMBER, 961, "Salom")

    def posts():
        return [m for m in bot.calls if isinstance(m, SendMessage) and m.chat_id == G_ADMIN]

    async def due_with_activity():
        await group_msg(bot, dp, G_ADMIN, 960, "xabar")
        await db.execute("UPDATE groups SET last_ad_at='2000-01-01T00:00:00+00:00'")

    # 1-reklama: Farg'ona -> Toshkent, faqat admin bo'lgan guruhga
    assert await ads.tick() == 1
    assert "Farg'onadan Toshkentga" in posts()[-1].text
    url = posts()[-1].reply_markup.inline_keyboard[0][0].url
    assert url == "https://t.me/testbot?start=g1001111111111_F2T"
    assert not [m for m in bot.calls if isinstance(m, SendMessage) and m.chat_id == G_MEMBER]

    # Vaqti kelmagan — qayta joylanmaydi
    assert await ads.tick() == 0
    # Vaqti o'tdi, lekin guruhda yangi xabar yo'q — joylanmaydi
    await db.execute("UPDATE groups SET last_ad_at='2000-01-01T00:00:00+00:00'")
    assert await ads.tick() == 0

    # 2-reklama: Toshkent -> Farg'ona (alohida xabar), 1-si o'chirilmaydi
    await due_with_activity()
    assert await ads.tick() == 1
    assert "Toshkentdan Farg'onaga" in posts()[-1].text
    assert not [m for m in bot.calls if isinstance(m, DeleteMessage)]

    # 3-reklama: yana Farg'ona -> Toshkent, eski Farg'ona reklamasi o'chiriladi
    await due_with_activity()
    first_id = (await db.fetchone("SELECT ad_msg_f2t FROM groups WHERE id=?", G_ADMIN))[0]
    assert await ads.tick() == 1
    dels = [m for m in bot.calls if isinstance(m, DeleteMessage)]
    assert len(dels) == 1 and dels[0].message_id == first_id
    await click(bot, dp, 900, "adm:ads")
    assert "Guruhlar:" in bot.texts_to(900)[-1]

    # Faollik qoidasi o'chirilsa — yangi xabarsiz ham joylanadi
    await db.set_setting("ad_require_activity", "0")
    await db.execute("UPDATE groups SET last_ad_at='2000-01-01T00:00:00+00:00'")
    assert await ads.tick() == 1
    status = await ads.group_status()
    assert any("admin emas" in x for x in status) and any("navbatdagi" in x for x in status)
    await db.set_setting("ad_require_activity", "1")
    await db.execute("UPDATE groups SET last_ad_at='2000-01-01T00:00:00+00:00'")
    assert await ads.tick() == 0
    assert any("yangi xabar yo'q" in x for x in await ads.group_status())

    # /reklama_hozir — ikkalasi birdan
    assert await ads.tick(force=True) == 2

    # O'chirilgan bo'lsa — joylanmaydi
    await db.set_setting("ad_enabled", "0")
    await due_with_activity()
    assert await ads.tick() == 0

    # Reklama tugmasi orqali kelgan yo'lovchi: yo'nalish tanlangan, tuman so'raladi
    await send(bot, dp, 970, "/start g1001111111111_T2F")
    out = bot.texts_to(970)
    assert "Toshkent ➜ Farg'ona" in out[-2] and "qaysi tumaniga" in out[-1]
    assert await db.count_users_from_ads() == 1



async def test_driver_trips_posted_to_admin_groups(app):
    from aiogram.methods import DeleteMessage
    from bot.ads import AdService
    bot, dp, db = app
    ads = AdService(bot, db)
    G = -1003333333333
    bot.admin_chats = {G}
    await group_msg(bot, dp, G, 980, "Salom")
    tomorrow = (today() + timedelta(days=1)).isoformat()
    D_YES, D_NO = 981, 982
    for d, name in ((D_YES, "Ali"), (D_NO, "Vali")):
        await db.upsert_user(d, name, f"user{d}")
        await db.set_phone(d, f"+99890000{d:04d}")
    t_yes = await db.create_trip(D_YES, "T2F", ["qoqon", "dangara"], tomorrow, "evening", 3,
                                 "Cobalt oq", "150 000", None, None, publish=True)
    await db.create_trip(D_NO, "F2T", ["quva"], tomorrow, "morning", 4, None, None, None, None, publish=False)

    def posts():
        return [m for m in bot.calls if isinstance(m, SendMessage) and m.chat_id == G]

    assert await ads.tick_trips() == 1  # o'chirib qo'ygan haydovchi joylanmaydi
    txt = posts()[-1].text
    # Haydovchiga bir martalik xabar: e'lon joylandi + guruh havolasi
    assert any("guruhlarimizga joylandi" in x and "t.me/toshken_fargonaa_taksi" in x
               for x in bot.texts_to(D_YES))
    assert "Toshkent ➜ Qo'qon, Dang'ara" in txt and "+998900000981" in txt and "@user981" in txt
    assert "Cobalt oq" in txt and "150 000" in txt and "Bo'sh joy: <b>3</b>" in txt
    assert "+998900000982" not in txt

    # Soat o'tmagan — qayta joylanmaydi
    assert await ads.tick_trips() == 0
    # Soat o'tdi — eski post o'chiriladi, yangisi joylanadi
    await db.execute("UPDATE trip_posts SET posted_at='2000-01-01T00:00:00+00:00'")
    first_msg = (await db.get_trip_post(t_yes, G))["message_id"]
    assert await ads.tick_trips() == 1
    assert any(isinstance(m, DeleteMessage) and m.message_id == first_msg for m in bot.calls)
    assert sum("guruhlarimizga joylandi" in x for x in bot.texts_to(D_YES)) == 1  # takrorlanmaydi
    # Shu haydovchining ikkinchi e'loni ham — havola qayta yuborilmaydi
    await db.create_trip(D_YES, "F2T", ["quva"], tomorrow, "morning", 2, None, None, None, None, publish=True)
    await ads.tick_trips()
    assert sum("guruhlarimizga joylandi" in x for x in bot.texts_to(D_YES)) == 1

    # Joylar to'lsa — guruhdan o'chiriladi va boshqa joylanmaydi
    await db.execute("UPDATE trips SET seats_free=0 WHERE id=?", t_yes)
    last_msg = (await db.get_trip_post(t_yes, G))["message_id"]
    assert await ads.tick_trips() == 0
    assert any(isinstance(m, DeleteMessage) and m.message_id == last_msg for m in bot.calls)
    assert await db.get_trip_post(t_yes, G) is None

    # Admin: /elon holati va /elon_hozir
    await send(bot, dp, 900, "/elon")
    assert "Haydovchi e'lonlarini" in bot.texts_to(900)[-1]
    await db.execute("UPDATE trips SET seats_free=2 WHERE id=?", t_yes)
    await send(bot, dp, 900, "/elon_hozir")
    assert "ta e'lon guruhlarga joylandi" in bot.texts_to(900)[-1]

    # Haydovchi "Mening e'lonlarim"dan o'chirib-yoqishi mumkin
    await db.execute("UPDATE trips SET seats_free=2 WHERE id=?", t_yes)
    await click(bot, dp, D_YES, f"tm:pub:{t_yes}")
    assert (await db.get_trip(t_yes))["publish"] == 0
    assert await ads.tick_trips() == 0



async def test_admin_users_list(app):
    from aiogram.methods import EditMessageText, SendDocument
    bot, dp, db = app
    ADMIN = 900
    await send(bot, dp, ADMIN, "/start")
    for i in range(20):
        await db.upsert_user(5000 + i, f"Odam {i}", f"odam{i}" if i % 2 else None)
    await db.set_phone(5001, "+998901112233")
    tomorrow = (today() + timedelta(days=1)).isoformat()
    await db.create_trip(5001, "F2T", ["qoqon"], tomorrow, "morning", 3, None, None, None, None)
    await db.create_request(5002, "F2T", "qoqon", "chilonzor", None, None, tomorrow, "morning", 1, None)
    await db.set_banned(5003, True)

    # Oddiy foydalanuvchi ro'yxatni ko'ra olmaydi
    n = len(bot.texts_to(5004))
    await send(bot, dp, 5004, "/users")
    assert len(bot.texts_to(5004)) == n

    await send(bot, dp, ADMIN, "/users")
    out = bot.texts_to(ADMIN)[-1]
    assert "21 ta" in out and "sahifa 1/2" in out  # 20 + admin
    await click(bot, dp, ADMIN, "usr:all:1")
    await click(bot, dp, ADMIN, "usr:drv:0")
    await click(bot, dp, ADMIN, "usr:pax:0")
    await click(bot, dp, ADMIN, "usr:ban:0")
    shown = [m.text for m in bot.calls if isinstance(m, (SendMessage, EditMessageText)) and m.chat_id == ADMIN]
    drv = next(t for t in shown if "Haydovchilar</b>: 1 ta" in t)
    assert "Odam 1" in drv and "+998901112233" in drv and "1 e'lon" in drv
    assert any("Yo'lovchilar</b>: 1 ta" in t and "Odam 2" in t for t in shown)
    assert any("Bloklangan</b>: 1 ta" in t and "Odam 3" in t for t in shown)

    await click(bot, dp, ADMIN, "usr_csv")
    doc = next(m for m in bot.calls if isinstance(m, SendDocument))
    content = doc.document.data.decode("utf-8-sig")
    assert content.count("\n") == 22  # sarlavha + 21 qator
    assert "Odam 1;@odam1;+998901112233;1;0" in content


# --- Yo'lovchi uzatish va bonus ----------------------------------------------
async def test_handover_bonus_flow(app):
    bot, dp, db = app
    ADMIN, A, B = 900, 1101, 1102  # A — Toshkentdagi haydovchi (uzatadi), B — Qo'qondagi haydovchi
    tomorrow = (today() + timedelta(days=1)).isoformat()
    for u in (ADMIN, A, B):
        await send(bot, dp, u, "/start")
    await db.set_phone(A, "+998901110000")
    await db.set_phone(B, "+998902220000")
    t_b = await db.create_trip(B, "F2T", ["qoqon"], tomorrow, "morning", 2, "Nexia", None, None, None)

    async def handover(phone, name="Akmal aka"):
        await send(bot, dp, A, "📤 Yo'lovchi uzatish")
        for d in ("ho:dir:F2T", "ho:fd:qoqon", "ho:td:chilonzor", f"ho:date:{tomorrow}",
                  "ho:slot:morning", "ho:seats:2"):
            await click(bot, dp, A, d)
        await send(bot, dp, A, phone)

    # 1) A begona yo'lovchini uzatadi
    await handover("90 333 44 55")
    await send(bot, dp, A, "Akmal aka, yuki bor")
    assert "+998903334455" in bot.texts_to(A)[-1]
    await click(bot, dp, A, "ho:ok")
    assert "uzatildi" in bot.texts_to(A)[-1] and "20 ball" in bot.texts_to(A)[-1]

    # 2) B ga taklif keladi — kim uzatgani aytiladi, raqam hali ko'rinmaydi
    offer = bot.texts_to(B)[-1]
    assert "boshqa haydovchi uzatgan" in offer and "+998903334455" not in offer
    await click(bot, dp, B, bot.last_kb(B).inline_keyboard[0][0].callback_data)
    out_b = bot.texts_to(B)
    assert any("+998903334455" in t and "Akmal aka" in t for t in out_b)
    # Mashina to'ldi (2 o'rin) — oq yo'l va bonus taklifi avtomatik
    assert any("oq yo'l" in t for t in out_b)
    # A ga bonus
    assert any("+20 ball" in t and "+998902220000" in t for t in bot.texts_to(A))
    assert await db.bonus_balance(A) == 20

    # 3) Shu raqamni shu kunga qayta uzatib bo'lmaydi
    await handover("+998903334455")
    assert "allaqachon" in bot.texts_to(A)[-1]
    await send(bot, dp, A, "❌ Bekor qilish")

    # 4) «💰 Bonusim»
    await send(bot, dp, A, "💰 Bonusim")
    assert "Bonus ballaringiz: 20" in bot.texts_to(A)[-1]

    # 5) B «To'ldim» ni qo'lda bosadi (yangi e'lon bilan)
    t_b2 = await db.create_trip(B, "T2F", ["quva"], tomorrow, "evening", 4, None, None, None, None)
    n = len(bot.texts_to(B))
    await click(bot, dp, B, f"tm:full:{t_b2}")
    assert (await db.get_trip(t_b2))["seats_free"] == 0
    assert len(bot.texts_to(B)) == n + 1 and "oq yo'l" in bot.texts_to(B)[-1]

    # 6) B birinchi e'lonni bekor qilsa — A ning bonusi qaytarib olinadi
    await click(bot, dp, B, f"tm:cancel:{t_b}")
    assert await db.bonus_balance(A) == 0
    assert any("qaytarib olindi" in t for t in bot.texts_to(A))

    # 7) Admin: qo'shish, to'lash, ko'rish
    await send(bot, dp, ADMIN, f"/bonus_qosh {A} 50 sinov")
    await send(bot, dp, ADMIN, f"/bonus_tolash {A} 100")
    assert "faqat 50 ball" in bot.texts_to(ADMIN)[-1]
    await send(bot, dp, ADMIN, f"/bonus_tolash {A} 30 karta")
    assert await db.bonus_balance(A) == 20
    assert any("30 ball pulga aylantirildi" in t for t in bot.texts_to(A))
    await send(bot, dp, ADMIN, "/bonus_ball 15")
    await send(bot, dp, ADMIN, "/bonus_info 1 ball = 1000 so'm")
    await click(bot, dp, ADMIN, "adm:bonus")
    txt = bot.texts_to(ADMIN)[-1]
    assert "15 ball / kishi" in txt and "1000 so'm" in txt and str(A) in txt
