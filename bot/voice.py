"""Ovozli xabardan e'lon ma'lumotlarini olish.

1) Ovoz -> matn: OpenAI-mos transkripsiya API (standart: OpenAI Whisper).
2) Matn -> tuzilgan ma'lumot: Claude (structured outputs, JSON sxema bo'yicha).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date, timedelta

import aiohttp
import anthropic

from .config import Config
from .regions import FERGANA, TASHKENT, TIME_SLOTS

log = logging.getLogger(__name__)

UNKNOWN = "unknown"
DATE_KEYS = {"today": 0, "tomorrow": 1, "day_after": 2}


class VoiceError(Exception):
    """Foydalanuvchiga ko'rsatiladigan xato."""


@dataclass
class Parsed:
    role: str | None = None            # "driver" / "passenger" / None
    direction: str | None = None       # "F2T" / "T2F"
    fergana: list[str] = field(default_factory=list)
    tashkent: str | None = None
    trip_date: str | None = None       # YYYY-MM-DD
    slot: str | None = None
    seats: int | None = None
    car: str | None = None
    price: str | None = None
    comment: str | None = None


def _district_list(table: dict[str, tuple[str, float, float]]) -> str:
    return "\n".join(f"- {code}: {name}" for code, (name, _, _) in table.items())


SYSTEM_PROMPT = f"""Sen Farg'ona viloyati ⇄ Toshkent yo'nalishidagi taksi botining yordamchisisan.
Foydalanuvchi ovozli xabar yuborgan, u matnga aylantirilgan (xatolar, rus so'zlari yoki
kirill yozuvi bo'lishi mumkin). Matndan e'lon ma'lumotlarini ajratib ol.

Qoidalar:
- role: odam o'zi mashina haydab, yo'lovchi olib ketmoqchi bo'lsa ("joy bor", "olib ketaman",
  "haydovchiman", "mashinam bor") — "driver"; taksi/mashina qidirayotgan bo'lsa — "passenger";
  aniq bo'lmasa — "unknown".
- direction: Farg'ona viloyatidan Toshkentga — "F2T"; Toshkentdan Farg'ona viloyatiga — "T2F".
- fergana_districts: Farg'ona viloyatidagi tumanlar kodlari. Yo'lovchi uchun bitta,
  haydovchi bir nechta aytishi mumkin. Shahar/qishloq nomi aytilsa, u joylashgan tuman kodini tanla.
- tashkent_district: Toshkent shahridagi tuman kodi (mavze/mahalla nomidan ham aniqla).
- date: "bugun" — today, "ertaga" — tomorrow, "indinga"/"ertadan keyin" — day_after.
- slot: morning 05–09, day 09–14, evening 14–20, night 20–05.
- seats: yo'lovchi uchun necha kishi, haydovchi uchun nechta bo'sh joy; aytilmasa 0.
- car, price, comment: aytilgan bo'lsa qisqa qilib yoz, aks holda bo'sh qator.
- Matnda aytilmagan narsani o'ylab topma — "unknown", bo'sh ro'yxat, 0 yoki bo'sh qator qo'y.

Farg'ona viloyati tumanlari:
{_district_list(FERGANA)}

Toshkent tumanlari:
{_district_list(TASHKENT)}
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "role": {"type": "string", "enum": ["driver", "passenger", UNKNOWN]},
        "direction": {"type": "string", "enum": ["F2T", "T2F", UNKNOWN]},
        "fergana_districts": {"type": "array", "items": {"type": "string", "enum": list(FERGANA)}},
        "tashkent_district": {"type": "string", "enum": [*TASHKENT, UNKNOWN]},
        "date": {"type": "string", "enum": [*DATE_KEYS, UNKNOWN]},
        "slot": {"type": "string", "enum": [*TIME_SLOTS, UNKNOWN]},
        "seats": {"type": "integer"},
        "car": {"type": "string"},
        "price": {"type": "string"},
        "comment": {"type": "string"},
    },
    "required": ["role", "direction", "fergana_districts", "tashkent_district", "date",
                 "slot", "seats", "car", "price", "comment"],
    "additionalProperties": False,
}


def to_parsed(data: dict, today: date) -> Parsed:
    """Claude javobini (JSON) Parsed ga aylantiradi, noma'lumlarni None qiladi."""
    def known(v):
        return None if v in (None, "", UNKNOWN) else v

    def text(key: str, limit: int) -> str | None:
        v = (data.get(key) or "").strip()
        return v[:limit] if v else None

    districts = [c for c in data.get("fergana_districts", []) if c in FERGANA]
    districts = list(dict.fromkeys(districts))  # takrorlarni olib tashlash
    d = known(data.get("date"))
    seats = data.get("seats") or 0
    return Parsed(
        role=known(data.get("role")),
        direction=known(data.get("direction")),
        fergana=districts,
        tashkent=known(data.get("tashkent_district")),
        trip_date=(today + timedelta(days=DATE_KEYS[d])).isoformat() if d in DATE_KEYS else None,
        slot=known(data.get("slot")),
        seats=seats if seats > 0 else None,
        car=text("car", 100),
        price=text("price", 50),
        comment=text("comment", 200),
    )


class VoiceParser:
    def __init__(self, config: Config):
        self.config = config
        self.client = anthropic.AsyncAnthropic(api_key=config.anthropic_api_key)

    async def transcribe(self, audio: bytes, filename: str = "voice.ogg") -> str:
        form = aiohttp.FormData()
        form.add_field("file", audio, filename=filename, content_type="audio/ogg")
        form.add_field("model", self.config.stt_model)
        if self.config.stt_language:
            form.add_field("language", self.config.stt_language)
        headers = {"Authorization": f"Bearer {self.config.stt_api_key}"}
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as s:
                async with s.post(self.config.stt_url, data=form, headers=headers) as r:
                    if r.status != 200:
                        log.warning("STT %s: %s", r.status, (await r.text())[:300])
                        raise VoiceError("Ovozni matnga aylantirib bo'lmadi.")
                    body = await r.json()
        except aiohttp.ClientError as e:
            log.warning("STT network error: %s", e)
            raise VoiceError("Ovoz xizmatiga ulanib bo'lmadi.") from e
        text = (body.get("text") or "").strip()
        if not text:
            raise VoiceError("Ovozli xabarda gap eshitilmadi.")
        return text

    async def extract(self, text: str, today: date) -> Parsed:
        try:
            response = await self.client.beta.messages.create(
                model=self.config.claude_model,
                max_tokens=4000,
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                output_config={
                    "effort": "low",
                    "format": {"type": "json_schema", "schema": SCHEMA},
                },
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": f"Ovozli xabar matni:\n«{text}»"}],
            )
        except anthropic.AuthenticationError as e:
            log.error("Anthropic API kaliti noto'g'ri: %s", e)
            raise VoiceError("Ovozli xizmat sozlanmagan.") from e
        except anthropic.RateLimitError as e:
            log.warning("Anthropic rate limit: %s", e)
            raise VoiceError("Hozir so'rovlar ko'p, birozdan keyin urinib ko'ring.") from e
        except anthropic.APIStatusError as e:
            log.warning("Anthropic API error %s: %s", e.status_code, e.message)
            raise VoiceError("Ovozli xabarni tushunib bo'lmadi.") from e
        except anthropic.APIConnectionError as e:
            log.warning("Anthropic connection error: %s", e)
            raise VoiceError("Xizmatga ulanib bo'lmadi.") from e

        if response.stop_reason in ("refusal", "max_tokens"):
            log.warning("extract stopped: %s", response.stop_reason)
            raise VoiceError("Ovozli xabarni tushunib bo'lmadi.")
        raw = next((b.text for b in response.content if b.type == "text"), "")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            log.warning("extract bad JSON: %r", raw[:200])
            raise VoiceError("Ovozli xabarni tushunib bo'lmadi.") from e
        return to_parsed(data, today)
