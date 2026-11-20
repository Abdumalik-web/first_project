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
    # Ovozli xabarlar (ixtiyoriy). Ikkala kalit ham bo'lsa yoqiladi.
    anthropic_api_key: str = ""
    claude_model: str = "claude-opus-5-5"
    stt_api_key: str = ""
    stt_url: str = "https://api.openai.com/v1/audio/transcriptions"
    stt_model: str = "whisper-1"
    stt_language: str = "uz"

    @property
    def voice_enabled(self) -> bool:
        return bool(self.anthropic_api_key and self.stt_api_key)


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
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
        claude_model=os.getenv("CLAUDE_MODEL", "claude-opus-5-5").strip(),
        stt_api_key=os.getenv("STT_API_KEY", "").strip(),
        stt_url=os.getenv("STT_URL", "https://api.openai.com/v1/audio/transcriptions").strip(),
        stt_model=os.getenv("STT_MODEL", "whisper-1").strip(),
        stt_language=os.getenv("STT_LANGUAGE", "uz").strip(),
    )
