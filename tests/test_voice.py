import json
from datetime import date
from types import SimpleNamespace

import pytest

from bot.config import Config
from bot.voice import SCHEMA, VoiceError, VoiceParser, to_parsed

TODAY = date(2026, 11, 20)


def test_to_parsed_maps_unknowns_and_dates():
    p = to_parsed(dict(role="unknown", direction="F2T", fergana_districts=["qoqon", "qoqon", "zzz"],
                       tashkent_district="unknown", date="day_after", slot="unknown", seats=0,
                       car=" Cobalt ", price="", comment=""), TODAY)
    assert p.role is None and p.direction == "F2T" and p.fergana == ["qoqon"]
    assert p.tashkent is None and p.trip_date == "2026-11-22" and p.slot is None
    assert p.seats is None and p.car == "Cobalt" and p.price is None


def test_schema_is_strict():
    assert SCHEMA["additionalProperties"] is False
    assert set(SCHEMA["required"]) == set(SCHEMA["properties"])


class _FakeMessages:
    def __init__(self, resp):
        self.resp, self.kwargs = resp, None

    async def create(self, **kw):
        self.kwargs = kw
        return self.resp


def _parser(resp):
    cfg = Config(bot_token="x", db_path="", offer_timeout_min=5, admin_ids=(),
                 anthropic_api_key="k", stt_api_key="s")
    vp = VoiceParser(cfg)
    fake = _FakeMessages(resp)
    vp.client = SimpleNamespace(beta=SimpleNamespace(messages=fake))
    return vp, fake


async def test_extract_sends_schema_and_parses():
    data = dict(role="passenger", direction="T2F", fergana_districts=["rishton"],
                tashkent_district="yunusobod", date="today", slot="day", seats=1,
                car="", price="", comment="yukim bor")
    resp = SimpleNamespace(stop_reason="end_turn",
                           content=[SimpleNamespace(type="text", text=json.dumps(data))])
    vp, fake = _parser(resp)
    p = await vp.extract("bugun Toshkentdan Rishtonga", TODAY)
    assert p.role == "passenger" and p.fergana == ["rishton"] and p.trip_date == "2026-11-20"
    assert fake.kwargs["output_config"]["format"]["schema"] is SCHEMA
    assert fake.kwargs["fallbacks"] == "default"


async def test_extract_refusal_raises():
    resp = SimpleNamespace(stop_reason="refusal", content=[])
    vp, _ = _parser(resp)
    with pytest.raises(VoiceError):
        await vp.extract("...", TODAY)
