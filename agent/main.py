"""Forex tahlil agenti: buyruq qatori (CLI).

Misollar:
    python -m agent EURUSD
    python -m agent GBPUSD --rasm chart.png --savol "London sessiyasi uchun setup bormi?"
    python -m agent EURUSD --offline          # Claude'siz, faqat modellar balli
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from . import models
from .config import NY_TZ, REPORTS_DIR, SMT_PAIRS
from .data import load_all

TASHKENT = ZoneInfo("Asia/Tashkent")


def scan(symbol: str, source: str = "auto", now: datetime | None = None) -> dict:
    frames = load_all(symbol, source)
    missing = [tf for tf in ("1d", "4h", "1h", "15m") if tf not in frames]
    if missing:
        raise SystemExit(f"{symbol}: ma'lumot yetarli emas (yo'q: {', '.join(missing)}). "
                         "Internet ulanishini yoki second_brain/02_malumotlar/narxlar/ CSV fayllarini tekshiring.")
    corr = None
    pair = SMT_PAIRS.get(symbol.upper())
    if pair:
        corr = load_all(pair[0], source)
    now = now or datetime.now(ZoneInfo(NY_TZ))
    ctx = models.build_context(symbol, frames, corr, now)
    last_bar = frames["5m"].index[-1] if "5m" in frames else frames["15m"].index[-1]
    lag_min = (pd.Timestamp(now) - last_bar).total_seconds() / 60
    result = {
        "symbol": symbol.upper(),
        "generated_ny": now.strftime("%Y-%m-%d %H:%M"),
        "generated_tashkent": now.astimezone(TASHKENT).strftime("%Y-%m-%d %H:%M"),
        "last_bar_ny": str(last_bar),
        "data_lag_minutes": round(lag_min, 1),
        "context": models.context_summary(ctx),
        "models": models.run_all(ctx),
    }
    if lag_min > 60:
        result["warning"] = "Oxirgi sham 1 soatdan eski: bozor yopiq yoki ma'lumot kechikmoqda."
    return result


def print_scorecard(res: dict) -> None:
    print(f"\n=== {res['symbol']} | NY {res['generated_ny']} | Toshkent {res['generated_tashkent']} ===")
    if res.get("warning"):
        print("⚠️ ", res["warning"])
    s = res["context"]["session"]
    print(f"Narx: {res['context']['price']} | Sessiya: {s['killzone'] or s['silver_bullet'] or '-'}")
    for m in res["models"]["ranking"]:
        plan = m["plan"] or {}
        print(f"\n▶ {m['model']:<22} {m['direction'] or '-':<8} ball {m['passed']}/{m['evaluated']}"
              f" ({m['score'] * 100:.0f}%)  R:R {plan.get('rr', '-')}")
        for c in m["checks"]:
            mark = {True: "✅", False: "❌", None: "➖"}[c["ok"]]
            print(f"   {mark} {c['name']}: {c['detail']}")
        if plan:
            print(f"   Reja: kirish {plan['entry']} | SL {plan['stop_loss']} | TP {plan['take_profit']}")
    print(f"\n★ Tavsiya: {res['models']['recommended_model'] or 'kutish'}. {res['models']['recommendation_note']}\n")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Forex texnik va fundamental tahlil agenti")
    ap.add_argument("symbol", help="masalan EURUSD, GBPUSD, XAUUSD")
    ap.add_argument("--rasm", type=Path, help="chart skrinshoti (png/jpg)")
    ap.add_argument("--savol", help="qo'shimcha savol")
    ap.add_argument("--manba", choices=["auto", "yahoo", "csv"], default="auto")
    ap.add_argument("--offline", action="store_true", help="Claude'ni chaqirmasdan faqat skaner natijasi")
    args = ap.parse_args(argv)

    res = scan(args.symbol, args.manba)
    print_scorecard(res)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(TASHKENT).strftime("%Y-%m-%d_%H%M")
    base = REPORTS_DIR / f"{stamp}_{res['symbol']}"
    base.with_suffix(".json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    if args.offline:
        print(f"Skaner natijasi saqlandi: {base.with_suffix('.json')}")
        return

    from .analyst import analyze

    if args.rasm and not args.rasm.exists():
        sys.exit(f"Rasm topilmadi: {args.rasm}")
    report = analyze(res["symbol"], res, args.rasm, args.savol)
    base.with_suffix(".md").write_text(report, encoding="utf-8")
    print(f"\nHisobot saqlandi: {base.with_suffix('.md')}")


if __name__ == "__main__":
    main()
