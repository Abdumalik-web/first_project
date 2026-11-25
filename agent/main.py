"""Forex tahlil agenti: buyruq qatori (CLI).

Misollar:
    python -m agent EURUSD
    python -m agent GBPUSD --rasm chart.png --savol "London sessiyasi uchun setup bormi?"
    python -m agent EURUSD --offline          # Claude'siz, faqat modellar balli
    python -m agent hisobot --kun 7           # vault asosida haftalik hisobot
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from . import models, vault
from .config import JOURNAL_DIR, NOTES_DIR, NY_TZ, REPORTS_DIR, SCAN_JSON_DIR, SMT_PAIRS, SUMMARY_DIR
from .data import load_all

TASHKENT = ZoneInfo("Asia/Tashkent")


def scan(symbol: str, source: str = "auto", now: datetime | None = None) -> dict:
    print(f"⏳ {symbol.upper()} narxlari yuklanmoqda (10–30 soniya)...", flush=True)
    frames = load_all(symbol, source)
    missing = [tf for tf in ("1d", "4h", "1h", "15m") if tf not in frames]
    if missing:
        raise SystemExit(f"{symbol}: ma'lumot yetarli emas (yo'q: {', '.join(missing)}). "
                         "Internet ulanishini yoki second_brain/02_malumotlar/narxlar/ CSV fayllarini tekshiring.")
    corr = None
    pair = SMT_PAIRS.get(symbol.upper())
    if pair:
        print(f"⏳ SMT uchun {pair[0]} yuklanmoqda...", flush=True)
        corr = load_all(pair[0], source)
    print("🔎 Modellar grafikka qo'yib ko'rilmoqda...", flush=True)
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


def summary_main(argv: list[str]) -> None:
    ap = argparse.ArgumentParser(prog="python -m agent hisobot",
                                 description="Obsidian vault'dagi tahlillar va jurnal asosida hisobot")
    ap.add_argument("--kun", type=int, default=7, help="necha kunlik tahlillar (standart: 7)")
    ap.add_argument("--juftlik", help="faqat shu juftlik, masalan EURUSD")
    ap.add_argument("--savol", help="vault bo'yicha erkin savol, masalan 'qaysi model eng ko'p ishladi?'")
    args = ap.parse_args(argv)

    reports = vault.recent_reports(REPORTS_DIR, args.juftlik, days=args.kun)
    if not reports:
        sys.exit(f"So'nggi {args.kun} kunda tahlil topilmadi ({REPORTS_DIR}).")
    parts = []
    for f in reports:
        meta = vault.read_frontmatter(f)
        body = f.read_text(encoding="utf-8")
        parts.append(f"<tahlil fayl=\"{f.stem}\" meta='{json.dumps(meta, ensure_ascii=False)}'>\n{body[:5000]}\n</tahlil>")
    for f in vault.notes_in(JOURNAL_DIR):
        parts.append(f"<jurnal fayl=\"{f.stem}\">\n{f.read_text(encoding='utf-8')}\n</jurnal>")
    material = "\n\n".join(parts)

    from .analyst import summarize

    today = datetime.now(TASHKENT).strftime("%Y-%m-%d")
    period = f"so'nggi {args.kun} kun (≤ {today})" + (f", {args.juftlik.upper()}" if args.juftlik else "")
    text = summarize(material, period, args.savol)
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{today}_hisobot_{args.kun}kun" + (f"_{args.juftlik.upper()}" if args.juftlik else "")
    meta = {"turi": "hisobot", "sana": today, "davr_kun": args.kun, "juftlik": (args.juftlik or "hammasi").upper(),
            "tahlillar_soni": len(reports), "tags": ["hisobot"]}
    links = "\n\n---\n## Manba tahlillar\n" + "\n".join(f"- [[{f.stem}]]" for f in reports) + "\n\n[[00_Bosh_sahifa]]\n"
    out = SUMMARY_DIR / f"{name}.md"
    out.write_text(vault.frontmatter(meta) + text + links, encoding="utf-8")
    print(f"\n✅ Hisobot saqlandi: {out}")
    vault.open_in_obsidian(out, SUMMARY_DIR.parent)


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0].lower() == "hisobot":
        return summary_main(argv[1:])
    ap = argparse.ArgumentParser(description="Forex texnik va fundamental tahlil agenti")
    ap.add_argument("symbol", help="masalan EURUSD, GBPUSD, XAUUSD")
    ap.add_argument("--rasm", type=Path, help="chart skrinshoti (png/jpg)")
    ap.add_argument("--savol", help="qo'shimcha savol")
    ap.add_argument("--manba", choices=["auto", "yahoo", "csv"], default="auto")
    ap.add_argument("--offline", action="store_true", help="Claude'ni chaqirmasdan faqat skaner natijasi")
    ap.add_argument("--ochma", action="store_true", help="natijani Obsidian'da avtomatik ochmaslik")
    args = ap.parse_args(argv)

    if args.rasm:
        args.rasm = Path(str(args.rasm).strip().strip('"'))
        if not args.rasm.exists():
            sys.exit(f"Rasm topilmadi: {args.rasm}")

    res = scan(args.symbol, args.manba)
    print_scorecard(res)

    SCAN_JSON_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(TASHKENT).strftime("%Y-%m-%d_%H%M")
    name = f"{stamp}_{res['symbol']}"
    (SCAN_JSON_DIR / f"{name}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")

    meta = vault.report_meta(res)
    scan_md = vault.scan_markdown(res)
    if args.offline:
        meta["manba"] = "skaner"
        body = scan_md
    else:
        from .analyst import analyze

        print("\n🤖 Claude fundamental tahlil va hisobot yozmoqda (1–3 daqiqa)...\n", flush=True)
        report = analyze(res["symbol"], res, args.rasm, args.savol)
        meta["manba"] = "claude"
        body = report + "\n\n---\n## Ilova: skaner natijasi\n" + scan_md.split("\n", 1)[1]
    md_path = REPORTS_DIR / f"{name}.md"
    md_path.write_text(vault.frontmatter(meta) + body + vault.skills_footer(res), encoding="utf-8")
    print(f"\n✅ Saqlandi: {md_path}")
    if not args.ochma:
        vault.open_in_obsidian(md_path, REPORTS_DIR.parent)


if __name__ == "__main__":
    main()
