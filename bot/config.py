import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    bot_token: str
    db_path: str
    # Haydovchi taklifga shuncha daqiqa ichida javob bermasa, keyingi haydovchiga o'tadi
    offer_timeout_min: int
    admin_ids: tuple[int, ...]


def load_config() -> Config:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN topilmadi. .env faylga BOT_TOKEN=... yozing.")
    admins = tuple(
        int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x
    )
    return Config(
        bot_token=token,
        db_path=os.getenv("DB_PATH", "taxi.db"),
        offer_timeout_min=int(os.getenv("OFFER_TIMEOUT_MIN", "5")),
        admin_ids=admins,
    )
