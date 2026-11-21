"""SQLite bilan ishlash (aiosqlite)."""
from __future__ import annotations

from datetime import datetime, timezone

import asyncio

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY,           -- Telegram user id
    full_name   TEXT,
    username    TEXT,
    phone       TEXT,
    banned      INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trips (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    driver_id   INTEGER NOT NULL REFERENCES users(id),
    direction   TEXT NOT NULL,                 -- F2T / T2F
    districts   TEXT NOT NULL,                 -- Farg'ona tumanlari: "qoqon,dangara,..."
    trip_date   TEXT NOT NULL,                 -- YYYY-MM-DD
    slot        TEXT NOT NULL,
    seats_total INTEGER NOT NULL,
    seats_free  INTEGER NOT NULL,
    car         TEXT,
    price       TEXT,
    lat         REAL,
    lon         REAL,
    status      TEXT NOT NULL DEFAULT 'active',  -- active / done / cancelled
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS requests (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    passenger_id    INTEGER NOT NULL REFERENCES users(id),
    direction       TEXT NOT NULL,
    fergana_code    TEXT NOT NULL,
    tashkent_code   TEXT NOT NULL,
    lat             REAL,
    lon             REAL,
    trip_date       TEXT NOT NULL,
    slot            TEXT NOT NULL,
    seats           INTEGER NOT NULL,
    comment         TEXT,
    status          TEXT NOT NULL DEFAULT 'searching', -- searching / matched / cancelled / expired
    trip_id         INTEGER REFERENCES trips(id),
    wait_notified   INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS offers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id      INTEGER NOT NULL REFERENCES requests(id),
    trip_id         INTEGER NOT NULL REFERENCES trips(id),
    status          TEXT NOT NULL DEFAULT 'pending',  -- pending / accepted / rejected / expired / no_seats
    distance_km     REAL,
    driver_msg_id   INTEGER,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS groups (
    id          INTEGER PRIMARY KEY,           -- Telegram chat id
    title       TEXT,
    username    TEXT,
    active      INTEGER NOT NULL DEFAULT 1,
    added_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trip_posts (
    trip_id     INTEGER NOT NULL,
    chat_id     INTEGER NOT NULL,
    message_id  INTEGER NOT NULL,
    posted_at   TEXT NOT NULL,
    PRIMARY KEY (trip_id, chat_id)
);

CREATE TABLE IF NOT EXISTS bonus_ledger (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    points      INTEGER NOT NULL,              -- musbat: qo'shildi, manfiy: yechildi
    reason      TEXT NOT NULL,                 -- referral / revoke / payout / manual
    request_id  INTEGER,
    note        TEXT,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_bonus_user ON bonus_ledger(user_id);

CREATE TABLE IF NOT EXISTS ref_links (
    user_id     INTEGER NOT NULL,
    chat_id     INTEGER NOT NULL,
    invite_link TEXT NOT NULL UNIQUE,
    PRIMARY KEY (user_id, chat_id)
);

CREATE TABLE IF NOT EXISTS pending_refs (
    user_id     INTEGER PRIMARY KEY,   -- guruhga taklif havolasi orqali kirgan, botda hali yo'q
    referrer_id INTEGER NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key     TEXT PRIMARY KEY,
    value   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS group_leads (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id         INTEGER NOT NULL,
    message_id      INTEGER NOT NULL,
    user_id         INTEGER,
    text_hash       TEXT NOT NULL,
    direction       TEXT NOT NULL,
    fergana_code    TEXT NOT NULL,
    trip_date       TEXT,
    sent_count      INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL,
    UNIQUE(chat_id, message_id)
);
CREATE INDEX IF NOT EXISTS ix_leads_dup ON group_leads(user_id, text_hash, created_at);

CREATE INDEX IF NOT EXISTS ix_trips_match ON trips(status, direction, trip_date);
CREATE INDEX IF NOT EXISTS ix_requests_status ON requests(status, trip_date);
CREATE INDEX IF NOT EXISTS ix_offers_req ON offers(request_id, status);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    def __init__(self, path: str):
        self.path = path
        self.conn: aiosqlite.Connection | None = None
        # Bitta ulanish: yozish ketma-ketliklari aralashib ketmasligi uchun qulf
        self.lock = asyncio.Lock()

    async def connect(self) -> None:
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA foreign_keys = ON")
        await self.conn.executescript(SCHEMA)
        # Eski bazalar uchun: yangi ustunlarni qo'shamiz
        await self._ensure_column("users", "banned", "INTEGER NOT NULL DEFAULT 0")
        await self._ensure_column("users", "source", "TEXT")
        await self._ensure_column("users", "link_notified", "INTEGER NOT NULL DEFAULT 0")
        # Taklif (referal) va majburiy guruh a'zoligi
        await self._ensure_column("users", "referrer_id", "INTEGER")
        await self._ensure_column("users", "ref_awarded", "INTEGER NOT NULL DEFAULT 0")
        await self._ensure_column("users", "group_ok", "INTEGER NOT NULL DEFAULT 0")
        await self._ensure_column("users", "group_checked_at", "TEXT")
        # Haydovchi uzatgan (botda bo'lmagan) yo'lovchi: passenger_id — uzatgan haydovchi
        await self._ensure_column("requests", "ext_name", "TEXT")
        await self._ensure_column("requests", "ext_phone", "TEXT")
        await self._ensure_column("groups", "last_ad_msg_id", "INTEGER")
        await self._ensure_column("groups", "last_ad_at", "TEXT")
        await self._ensure_column("groups", "msgs_since_ad", "INTEGER NOT NULL DEFAULT 1")
        await self._ensure_column("groups", "ad_msg_f2t", "INTEGER")
        await self._ensure_column("groups", "ad_msg_t2f", "INTEGER")
        await self._ensure_column("groups", "last_ad_dir", "TEXT")
        await self._ensure_column("trips", "publish", "INTEGER NOT NULL DEFAULT 0")
        await self._ensure_column("trips", "publish_notified", "INTEGER NOT NULL DEFAULT 0")
        # Bir martalik: e'lonlar endi so'ramasdan guruhlarga joylanadi — mavjud faollarini yoqamiz
        done = await self.fetchone("SELECT 1 FROM settings WHERE key='migr_publish_all'")
        if not done:
            await self.conn.execute("UPDATE trips SET publish=1 WHERE status='active'")
            await self.conn.execute("INSERT INTO settings(key, value) VALUES('migr_publish_all','1')")
        await self.conn.commit()

    async def _ensure_column(self, table: str, column: str, ddl: str) -> None:
        cols = {r["name"] for r in await self.fetchall(f"PRAGMA table_info({table})")}
        if column not in cols:
            await self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")

    async def close(self) -> None:
        if self.conn:
            await self.conn.close()

    # --- umumiy yordamchilar -------------------------------------------------
    async def fetchone(self, sql: str, *args) -> aiosqlite.Row | None:
        async with self.conn.execute(sql, args) as cur:
            return await cur.fetchone()

    async def fetchall(self, sql: str, *args) -> list[aiosqlite.Row]:
        async with self.conn.execute(sql, args) as cur:
            return list(await cur.fetchall())

    async def execute(self, sql: str, *args) -> int:
        async with self.lock:
            cur = await self.conn.execute(sql, args)
            await self.conn.commit()
            return cur.lastrowid

    async def _exec_count(self, sql: str, *args) -> int:
        async with self.lock:
            cur = await self.conn.execute(sql, args)
            await self.conn.commit()
            return cur.rowcount

    # --- users ---------------------------------------------------------------
    async def upsert_user(self, uid: int, full_name: str, username: str | None) -> None:
        await self.execute(
            """INSERT INTO users(id, full_name, username, created_at) VALUES(?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET full_name=excluded.full_name,
                                             username=excluded.username""",
            uid, full_name, username, now_iso(),
        )

    async def set_phone(self, uid: int, phone: str) -> None:
        await self.execute("UPDATE users SET phone=? WHERE id=?", phone, uid)

    async def get_user(self, uid: int):
        return await self.fetchone("SELECT * FROM users WHERE id=?", uid)

    # --- trips ---------------------------------------------------------------
    async def create_trip(self, driver_id: int, direction: str, districts: list[str],
                          trip_date: str, slot: str, seats: int, car: str, price: str,
                          lat: float | None, lon: float | None, publish: bool = False) -> int:
        return await self.execute(
            """INSERT INTO trips(driver_id, direction, districts, trip_date, slot, seats_total,
                   seats_free, car, price, lat, lon, publish, created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            driver_id, direction, ",".join(districts), trip_date, slot, seats, seats,
            car, price, lat, lon, int(publish), now_iso(),
        )

    async def get_trip(self, trip_id: int):
        return await self.fetchone("SELECT * FROM trips WHERE id=?", trip_id)

    async def active_trips_of(self, driver_id: int):
        return await self.fetchall(
            "SELECT * FROM trips WHERE driver_id=? AND status='active' ORDER BY trip_date, id",
            driver_id,
        )

    async def candidate_trips(self, direction: str, trip_date: str):
        return await self.fetchall(
            "SELECT * FROM trips WHERE status='active' AND direction=? AND trip_date=?"
            " AND seats_free > 0",
            direction, trip_date,
        )

    async def set_trip_location(self, driver_id: int, lat: float, lon: float) -> int:
        return await self._exec_count(
            "UPDATE trips SET lat=?, lon=? WHERE driver_id=? AND status='active'",
            lat, lon, driver_id,
        )

    async def set_trip_status(self, trip_id: int, status: str) -> None:
        await self.execute("UPDATE trips SET status=? WHERE id=?", status, trip_id)

    # --- requests ------------------------------------------------------------
    async def create_request(self, passenger_id: int, direction: str, fergana_code: str,
                             tashkent_code: str, lat: float | None, lon: float | None,
                             trip_date: str, slot: str, seats: int, comment: str | None,
                             ext_name: str | None = None, ext_phone: str | None = None) -> int:
        return await self.execute(
            """INSERT INTO requests(passenger_id, direction, fergana_code, tashkent_code, lat, lon,
                   trip_date, slot, seats, comment, ext_name, ext_phone, created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            passenger_id, direction, fergana_code, tashkent_code, lat, lon,
            trip_date, slot, seats, comment, ext_name, ext_phone, now_iso(),
        )

    async def get_request(self, req_id: int):
        return await self.fetchone("SELECT * FROM requests WHERE id=?", req_id)

    async def open_requests_of(self, passenger_id: int):
        return await self.fetchall(
            "SELECT * FROM requests WHERE passenger_id=? AND status IN ('searching','matched')"
            " ORDER BY trip_date, id",
            passenger_id,
        )

    async def searching_requests(self, direction: str, trip_date: str):
        """Hozir hech bir haydovchiga taklif qilinmayotgan, kutayotgan so'rovlar."""
        return await self.fetchall(
            """SELECT r.* FROM requests r
               WHERE r.status='searching' AND r.direction=? AND r.trip_date=?
                 AND NOT EXISTS (SELECT 1 FROM offers o
                                 WHERE o.request_id=r.id AND o.status='pending')
               ORDER BY r.id""",
            direction, trip_date,
        )

    async def passengers_of_trip(self, trip_id: int):
        return await self.fetchall(
            """SELECT r.*,
                      COALESCE(r.ext_name, CASE WHEN r.ext_phone IS NOT NULL THEN 'Uzatilgan yo''lovchi' END,
                               u.full_name) AS full_name,
                      CASE WHEN r.ext_phone IS NULL THEN u.username END AS username,
                      COALESCE(r.ext_phone, u.phone) AS phone
               FROM requests r
               JOIN users u ON u.id = r.passenger_id
               WHERE r.trip_id=? AND r.status='matched' ORDER BY r.id""",
            trip_id,
        )

    # --- offers --------------------------------------------------------------
    async def offered_trip_ids(self, req_id: int) -> set[int]:
        # 'no_seats' takliflar hisobga olinmaydi: o'rin bo'shasa, yana taklif qilish mumkin
        rows = await self.fetchall(
            "SELECT trip_id FROM offers WHERE request_id=? AND status != 'no_seats'", req_id
        )
        return {r["trip_id"] for r in rows}

    async def pending_offer_for(self, req_id: int):
        return await self.fetchone(
            "SELECT * FROM offers WHERE request_id=? AND status='pending'", req_id
        )

    async def create_offer(self, req_id: int, trip_id: int, distance_km: float) -> int:
        return await self.execute(
            "INSERT INTO offers(request_id, trip_id, distance_km, created_at) VALUES(?,?,?,?)",
            req_id, trip_id, distance_km, now_iso(),
        )

    async def get_offer(self, offer_id: int):
        return await self.fetchone("SELECT * FROM offers WHERE id=?", offer_id)

    async def set_offer_msg(self, offer_id: int, msg_id: int) -> None:
        await self.execute("UPDATE offers SET driver_msg_id=? WHERE id=?", msg_id, offer_id)

    async def close_offer(self, offer_id: int, status: str) -> bool:
        """Faqat 'pending' bo'lsa yopadi. Muvaffaqiyatli bo'lsa True."""
        n = await self._exec_count(
            "UPDATE offers SET status=? WHERE id=? AND status='pending'", status, offer_id
        )
        return n == 1

    async def stale_offers(self, older_than_iso: str):
        return await self.fetchall(
            "SELECT * FROM offers WHERE status='pending' AND created_at < ?", older_than_iso
        )

    async def pending_offers_of_trip(self, trip_id: int):
        return await self.fetchall(
            "SELECT * FROM offers WHERE trip_id=? AND status='pending'", trip_id
        )

    # --- atomar biriktirish --------------------------------------------------
    async def accept_offer(self, offer_id: int) -> str:
        """Taklifni qabul qiladi. Natija: 'ok' / 'closed' / 'no_seats'."""
        async with self.lock:
            return await self._accept_offer(offer_id)

    async def _accept_offer(self, offer_id: int) -> str:
        try:
            offer = await self.fetchone("SELECT * FROM offers WHERE id=?", offer_id)
            if not offer or offer["status"] != "pending":
                await self.conn.rollback()
                return "closed"
            req = await self.fetchone("SELECT * FROM requests WHERE id=?", offer["request_id"])
            trip = await self.fetchone("SELECT * FROM trips WHERE id=?", offer["trip_id"])
            if req["status"] != "searching" or trip["status"] != "active":
                await self.conn.execute("UPDATE offers SET status='expired' WHERE id=?", (offer_id,))
                await self.conn.commit()
                return "closed"
            if trip["seats_free"] < req["seats"]:
                await self.conn.execute("UPDATE offers SET status='no_seats' WHERE id=?", (offer_id,))
                await self.conn.commit()
                return "no_seats"
            await self.conn.execute("UPDATE offers SET status='accepted' WHERE id=?", (offer_id,))
            await self.conn.execute(
                "UPDATE trips SET seats_free = seats_free - ? WHERE id=?", (req["seats"], trip["id"])
            )
            await self.conn.execute(
                "UPDATE requests SET status='matched', trip_id=? WHERE id=?", (trip["id"], req["id"])
            )
            await self.conn.commit()
            return "ok"
        except Exception:
            await self.conn.rollback()
            raise

    async def unmatch_request(self, req_id: int, new_status: str) -> None:
        """Biriktirilgan so'rovni ajratadi va haydovchining o'rnini qaytaradi."""
        async with self.lock:
            await self._unmatch_request(req_id, new_status)

    async def _unmatch_request(self, req_id: int, new_status: str) -> None:
        req = await self.fetchone("SELECT * FROM requests WHERE id=?", req_id)
        if req and req["status"] == "matched" and req["trip_id"]:
            await self.conn.execute(
                "UPDATE trips SET seats_free = MIN(seats_total, seats_free + ?) WHERE id=?",
                (req["seats"], req["trip_id"]),
            )
        await self.conn.execute(
            "UPDATE requests SET status=?, trip_id=NULL, wait_notified=0 WHERE id=?",
            (new_status, req_id),
        )
        await self.conn.commit()

    async def expire_old(self, today_iso: str) -> list:
        """O'tib ketgan sanadagi e'lonlarni yopadi. Muddati o'tgan 'searching' so'rovlarni qaytaradi."""
        async with self.lock:
            return await self._expire_old(today_iso)

    async def _expire_old(self, today_iso: str) -> list:
        expired = await self.fetchall(
            "SELECT * FROM requests WHERE status='searching' AND trip_date < ?", today_iso
        )
        await self.conn.execute(
            "UPDATE requests SET status='expired' WHERE status='searching' AND trip_date < ?",
            (today_iso,),
        )
        await self.conn.execute(
            "UPDATE trips SET status='done' WHERE status='active' AND trip_date < ?", (today_iso,)
        )
        await self.conn.execute(
            """UPDATE offers SET status='expired' WHERE status='pending'
               AND request_id IN (SELECT id FROM requests WHERE status='expired')"""
        )
        await self.conn.commit()
        return expired

    # --- admin ---------------------------------------------------------------
    async def is_banned(self, uid: int) -> bool:
        row = await self.fetchone("SELECT banned FROM users WHERE id=?", uid)
        return bool(row and row["banned"])

    async def set_banned(self, uid: int, banned: bool) -> bool:
        n = await self._exec_count("UPDATE users SET banned=? WHERE id=?", int(banned), uid)
        return n == 1

    async def all_user_ids(self) -> list[int]:
        rows = await self.fetchall("SELECT id FROM users WHERE banned=0")
        return [r["id"] for r in rows]

    async def stats(self, today_iso: str) -> dict[str, int]:
        q = {
            "users": "SELECT COUNT(*) FROM users",
            "banned": "SELECT COUNT(*) FROM users WHERE banned=1",
            "drivers": "SELECT COUNT(DISTINCT driver_id) FROM trips",
            "passengers": "SELECT COUNT(DISTINCT passenger_id) FROM requests",
            "active_trips": "SELECT COUNT(*) FROM trips WHERE status='active'",
            "searching": "SELECT COUNT(*) FROM requests WHERE status='searching'",
            "matched_total": "SELECT COUNT(*) FROM offers WHERE status='accepted'",
            "requests_today": "SELECT COUNT(*) FROM requests WHERE substr(created_at,1,10)=?",
            "trips_today": "SELECT COUNT(*) FROM trips WHERE substr(created_at,1,10)=?",
            "matched_today": "SELECT COUNT(*) FROM offers WHERE status='accepted'"
                             " AND substr(created_at,1,10)=?",
        }
        out = {}
        for k, sql in q.items():
            args = (today_iso,) if "?" in sql else ()
            row = await self.fetchone(sql, *args)
            out[k] = row[0]
        return out

    async def all_active_trips(self, limit: int = 30):
        return await self.fetchall(
            """SELECT t.*, u.full_name, u.username, u.phone FROM trips t
               JOIN users u ON u.id=t.driver_id
               WHERE t.status='active' ORDER BY t.trip_date, t.id LIMIT ?""",
            limit,
        )

    async def all_searching_requests(self, limit: int = 30):
        return await self.fetchall(
            """SELECT r.*, u.full_name, u.username, u.phone FROM requests r
               JOIN users u ON u.id=r.passenger_id
               WHERE r.status='searching' ORDER BY r.trip_date, r.id LIMIT ?""",
            limit,
        )

    async def find_users(self, query: str, limit: int = 10):
        q = query.strip().lstrip("@")
        if q.isdigit():
            return await self.fetchall("SELECT * FROM users WHERE id=?", int(q))
        like = f"%{q}%"
        return await self.fetchall(
            "SELECT * FROM users WHERE username LIKE ? OR full_name LIKE ? OR phone LIKE ? LIMIT ?",
            like, like, like, limit,
        )

    # --- guruhlar ------------------------------------------------------------
    async def upsert_group(self, chat_id: int, title: str | None, username: str | None,
                           active: bool = True) -> None:
        await self.execute(
            """INSERT INTO groups(id, title, username, active, added_at) VALUES(?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET title=excluded.title, username=excluded.username,
                                             active=excluded.active""",
            chat_id, title, username, int(active), now_iso(),
        )

    async def is_duplicate_lead(self, user_id: int | None, text_hash: str, since_iso: str) -> bool:
        row = await self.fetchone(
            "SELECT 1 FROM group_leads WHERE user_id IS ? AND text_hash=? AND created_at >= ?",
            user_id, text_hash, since_iso,
        )
        return row is not None

    async def add_lead(self, chat_id: int, message_id: int, user_id: int | None, text_hash: str,
                       direction: str, fergana_code: str, trip_date: str | None) -> int | None:
        """Yangi bo'lsa id qaytaradi, shu xabar oldin qayta ishlangan bo'lsa None."""
        async with self.lock:
            cur = await self.conn.execute(
                """INSERT OR IGNORE INTO group_leads(chat_id, message_id, user_id, text_hash,
                       direction, fergana_code, trip_date, created_at) VALUES(?,?,?,?,?,?,?,?)""",
                (chat_id, message_id, user_id, text_hash, direction, fergana_code, trip_date, now_iso()),
            )
            await self.conn.commit()
            return cur.lastrowid if cur.rowcount == 1 else None

    async def set_lead_sent(self, lead_id: int, n: int) -> None:
        await self.execute("UPDATE group_leads SET sent_count=? WHERE id=?", n, lead_id)

    async def active_trips_on(self, direction: str, dates: list[str]):
        marks = ",".join("?" * len(dates))
        return await self.fetchall(
            f"SELECT * FROM trips WHERE status='active' AND direction=? AND seats_free > 0"
            f" AND trip_date IN ({marks})",
            direction, *dates,
        )

    async def group_stats(self, today_iso: str) -> dict[str, int]:
        q = {
            "groups": "SELECT COUNT(*) FROM groups WHERE active=1",
            "leads_today": "SELECT COUNT(*) FROM group_leads WHERE substr(created_at,1,10)=?",
            "leads_sent_today": "SELECT COUNT(*) FROM group_leads WHERE sent_count>0"
                                " AND substr(created_at,1,10)=?",
            "leads_total": "SELECT COUNT(*) FROM group_leads",
        }
        out = {}
        for k, sql in q.items():
            row = await self.fetchone(sql, *((today_iso,) if "?" in sql else ()))
            out[k] = row[0]
        return out

    async def list_groups(self):
        return await self.fetchall(
            """SELECT g.*, (SELECT COUNT(*) FROM group_leads l WHERE l.chat_id=g.id) AS leads,
                      (SELECT COUNT(*) FROM group_leads l WHERE l.chat_id=g.id AND l.sent_count>0) AS sent
               FROM groups g ORDER BY g.active DESC, leads DESC"""
        )

    # --- sozlamalar ----------------------------------------------------------
    async def get_setting(self, key: str, default: str) -> str:
        row = await self.fetchone("SELECT value FROM settings WHERE key=?", key)
        return row["value"] if row else default

    async def set_setting(self, key: str, value: str) -> None:
        await self.execute(
            "INSERT INTO settings(key, value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            key, value,
        )

    # --- guruh reklamasi -----------------------------------------------------
    async def bump_group_activity(self, chat_id: int) -> None:
        await self.execute("UPDATE groups SET msgs_since_ad = msgs_since_ad + 1 WHERE id=?", chat_id)

    async def groups_due_for_ad(self, before_iso: str, require_activity: bool = True):
        """Faol va vaqti kelgan guruhlar (require_activity — oxirgi reklamadan beri yangi xabar bo'lgan)."""
        activity = "AND msgs_since_ad > 0" if require_activity else ""
        return await self.fetchall(
            f"""SELECT * FROM groups WHERE active=1 {activity}
               AND (last_ad_at IS NULL OR last_ad_at <= ?)""",
            before_iso,
        )

    async def set_group_ad(self, chat_id: int, direction: str | None, msg_id: int | None,
                           at_iso: str) -> None:
        """msg_id None bo'lsa — reklama joylanmadi (admin emas), faqat vaqt yangilanadi."""
        if msg_id is None:
            await self.execute("UPDATE groups SET last_ad_at=? WHERE id=?", at_iso, chat_id)
            return
        col = "ad_msg_f2t" if direction == "F2T" else "ad_msg_t2f"
        await self.execute(
            f"UPDATE groups SET {col}=?, last_ad_dir=?, last_ad_at=?, msgs_since_ad=0 WHERE id=?",
            msg_id, direction, at_iso, chat_id,
        )

    async def set_user_source(self, uid: int, source: str) -> None:
        await self.execute("UPDATE users SET source=? WHERE id=? AND source IS NULL", source, uid)

    async def count_users_from_ads(self) -> int:
        row = await self.fetchone("SELECT COUNT(*) FROM users WHERE source LIKE 'g%'")
        return row[0]

    # --- haydovchi e'lonlarini guruhlarga joylash -----------------------------
    async def trips_to_publish(self):
        """Guruhga joylashga rozi bo'lgan, faol va bo'sh joyi bor e'lonlar (haydovchi ma'lumoti bilan)."""
        return await self.fetchall(
            """SELECT t.*, u.full_name, u.username, u.phone FROM trips t
               JOIN users u ON u.id = t.driver_id
               WHERE t.status='active' AND t.publish=1 AND t.seats_free > 0 AND u.banned=0
               ORDER BY t.id"""
        )

    async def get_trip_post(self, trip_id: int, chat_id: int):
        return await self.fetchone(
            "SELECT * FROM trip_posts WHERE trip_id=? AND chat_id=?", trip_id, chat_id
        )

    async def save_trip_post(self, trip_id: int, chat_id: int, message_id: int) -> None:
        await self.execute(
            """INSERT INTO trip_posts(trip_id, chat_id, message_id, posted_at) VALUES(?,?,?,?)
               ON CONFLICT(trip_id, chat_id) DO UPDATE SET message_id=excluded.message_id,
                                                         posted_at=excluded.posted_at""",
            trip_id, chat_id, message_id, now_iso(),
        )

    async def stale_trip_posts(self):
        """O'chirilishi kerak bo'lgan postlar: e'lon yopilgan, joy qolmagan yoki rozilik yo'q."""
        return await self.fetchall(
            """SELECT p.* FROM trip_posts p JOIN trips t ON t.id = p.trip_id
               JOIN users u ON u.id = t.driver_id
               WHERE t.status != 'active' OR t.seats_free <= 0 OR t.publish = 0 OR u.banned = 1"""
        )

    async def delete_trip_post(self, trip_id: int, chat_id: int) -> None:
        await self.execute("DELETE FROM trip_posts WHERE trip_id=? AND chat_id=?", trip_id, chat_id)

    async def toggle_trip_publish(self, trip_id: int) -> bool:
        """Guruhga joylashni almashtiradi, yangi holatni qaytaradi."""
        await self.execute("UPDATE trips SET publish = 1 - publish WHERE id=?", trip_id)
        row = await self.fetchone("SELECT publish FROM trips WHERE id=?", trip_id)
        return bool(row and row["publish"])

    async def mark_publish_notified(self, trip_id: int) -> bool:
        """Haydovchiga «guruhga joylandi» xabari hali yuborilmagan bo'lsa True qaytaradi va belgilaydi."""
        n = await self._exec_count(
            "UPDATE trips SET publish_notified=1 WHERE id=? AND publish_notified=0", trip_id
        )
        return n == 1

    async def mark_user_link_notified(self, uid: int) -> bool:
        """Guruh havolasi hali yuborilmagan bo'lsa True qaytaradi va belgilaydi (har odamga bir marta)."""
        n = await self._exec_count(
            "UPDATE users SET link_notified=1 WHERE id=? AND link_notified=0", uid
        )
        return n == 1

    # --- foydalanuvchilar ro'yxati (admin) -------------------------------------
    _USER_FILTERS = {
        "all": "1=1",
        "drv": "EXISTS (SELECT 1 FROM trips t WHERE t.driver_id=u.id)",
        "pax": "EXISTS (SELECT 1 FROM requests r WHERE r.passenger_id=u.id)",
        "ban": "u.banned=1",
    }

    async def list_users(self, flt: str = "all", limit: int = 15, offset: int = 0):
        where = self._USER_FILTERS.get(flt, "1=1")
        return await self.fetchall(
            f"""SELECT u.*,
                   (SELECT COUNT(*) FROM trips t WHERE t.driver_id=u.id) AS trips_n,
                   (SELECT COUNT(*) FROM requests r WHERE r.passenger_id=u.id) AS reqs_n
               FROM users u WHERE {where}
               ORDER BY u.created_at DESC LIMIT ? OFFSET ?""",
            limit, offset,
        )

    async def count_users(self, flt: str = "all") -> int:
        where = self._USER_FILTERS.get(flt, "1=1")
        row = await self.fetchone(f"SELECT COUNT(*) FROM users u WHERE {where}")
        return row[0]

    # --- bonus ballar ----------------------------------------------------------
    async def add_bonus(self, uid: int, points: int, reason: str, request_id: int | None = None,
                        note: str | None = None) -> None:
        await self.execute(
            "INSERT INTO bonus_ledger(user_id, points, reason, request_id, note, created_at)"
            " VALUES(?,?,?,?,?,?)",
            uid, points, reason, request_id, note, now_iso(),
        )

    async def bonus_balance(self, uid: int) -> int:
        row = await self.fetchone("SELECT COALESCE(SUM(points),0) FROM bonus_ledger WHERE user_id=?", uid)
        return row[0]

    async def bonus_for_request(self, request_id: int) -> int:
        """Shu so'rov uchun hozir hisobda turgan ball (berilgan - qaytarib olingan)."""
        row = await self.fetchone(
            "SELECT COALESCE(SUM(points),0) FROM bonus_ledger WHERE request_id=? AND reason IN ('referral','revoke')",
            request_id,
        )
        return row[0]

    async def bonus_history(self, uid: int, limit: int = 10):
        return await self.fetchall(
            "SELECT * FROM bonus_ledger WHERE user_id=? ORDER BY id DESC LIMIT ?", uid, limit
        )

    async def bonus_top(self, limit: int = 20):
        return await self.fetchall(
            """SELECT b.user_id, SUM(b.points) AS balance,
                      SUM(CASE WHEN b.reason IN ('referral','invite') THEN 1 ELSE 0 END) AS referrals,
                      u.full_name, u.username, u.phone
               FROM bonus_ledger b LEFT JOIN users u ON u.id=b.user_id
               GROUP BY b.user_id HAVING balance != 0 OR referrals > 0
               ORDER BY balance DESC LIMIT ?""",
            limit,
        )

    async def referral_exists(self, ext_phone: str, trip_date: str) -> bool:
        """Shu raqamli yo'lovchi shu kunga allaqachon uzatilganmi (bir odamni ikki marta sanamaslik)."""
        row = await self.fetchone(
            "SELECT 1 FROM requests WHERE ext_phone=? AND trip_date=? AND status IN ('searching','matched')",
            ext_phone, trip_date,
        )
        return row is not None

    async def set_trip_full(self, trip_id: int) -> None:
        await self.execute("UPDATE trips SET seats_free=0 WHERE id=?", trip_id)

    # --- taklif (referal) ------------------------------------------------------
    async def set_referrer(self, uid: int, referrer_id: int) -> bool:
        if uid == referrer_id:
            return False
        n = await self._exec_count(
            "UPDATE users SET referrer_id=? WHERE id=? AND referrer_id IS NULL"
            " AND EXISTS (SELECT 1 FROM users r WHERE r.id=?)",
            referrer_id, uid, referrer_id,
        )
        return n == 1

    async def mark_ref_awarded(self, uid: int) -> bool:
        n = await self._exec_count(
            "UPDATE users SET ref_awarded=1 WHERE id=? AND ref_awarded=0 AND referrer_id IS NOT NULL", uid
        )
        return n == 1

    async def referral_stats(self, uid: int) -> tuple[int, int]:
        """(taklif qilinganlar, ball berilganlar)."""
        row = await self.fetchone(
            "SELECT COUNT(*), COALESCE(SUM(ref_awarded),0) FROM users WHERE referrer_id=?", uid
        )
        return row[0], row[1]

    async def set_group_ok(self, uid: int, ok: bool) -> None:
        await self.execute(
            "UPDATE users SET group_ok=?, group_checked_at=? WHERE id=?", int(ok), now_iso(), uid
        )

    async def get_ref_link(self, uid: int, chat_id: int) -> str | None:
        row = await self.fetchone(
            "SELECT invite_link FROM ref_links WHERE user_id=? AND chat_id=?", uid, chat_id
        )
        return row["invite_link"] if row else None

    async def save_ref_link(self, uid: int, chat_id: int, link: str) -> None:
        await self.execute(
            "INSERT OR REPLACE INTO ref_links(user_id, chat_id, invite_link) VALUES(?,?,?)",
            uid, chat_id, link,
        )

    async def referrer_by_link(self, link: str) -> int | None:
        row = await self.fetchone("SELECT user_id FROM ref_links WHERE invite_link=?", link)
        return row["user_id"] if row else None

    async def add_pending_ref(self, uid: int, referrer_id: int) -> None:
        await self.execute(
            "INSERT OR IGNORE INTO pending_refs(user_id, referrer_id, created_at) VALUES(?,?,?)",
            uid, referrer_id, now_iso(),
        )

    async def pop_pending_ref(self, uid: int) -> int | None:
        row = await self.fetchone("SELECT referrer_id FROM pending_refs WHERE user_id=?", uid)
        if row:
            await self.execute("DELETE FROM pending_refs WHERE user_id=?", uid)
            return row["referrer_id"]
        return None
