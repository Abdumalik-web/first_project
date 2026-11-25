"""Obsidian vault bilan ishlash: frontmatter yozish/o'qish, hisobotlarni topish."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

SKILL_LINKS = {
    "Klassik texnik tahlil": ["trend_va_darajalar", "indikatorlar", "patternlar"],
    "ICT": ["01_bozor_strukturasi", "02_likvidlik", "03_pd_arraylar", "06_kirish_modeli_checklist"],
    "SMC": ["01_struktura_va_inducement", "02_poi_order_block"],
    "CRT": ["01_crt_asoslari", "02_timeframe_va_vaqt"],
    "Silver Bullet": ["07_silver_bullet", "04_vaqt_va_sessiyalar"],
}


def _yaml_value(v) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list):
        return "[" + ", ".join(_yaml_value(x) for x in v) + "]"
    s = str(v).replace('"', "'")
    return f'"{s}"'


def frontmatter(meta: dict) -> str:
    return "---\n" + "".join(f"{k}: {_yaml_value(v)}\n" for k, v in meta.items()) + "---\n\n"


def read_frontmatter(path: Path) -> dict:
    """Oddiy `kalit: qiymat` qatorlarini o'qiydi (PyYAML'siz)."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    meta = {}
    for line in text[3:end].splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"')
    return meta


def report_meta(res: dict) -> dict:
    """Skaner natijasidan Obsidian (Dataview) uchun metadata."""
    best = res["models"]["ranking"][0]
    rec = res["models"]["recommended_model"]
    plan = best.get("plan") or {}
    return {
        "turi": "tahlil",
        "symbol": res["symbol"],
        "sana": res["generated_tashkent"][:10],
        "vaqt_toshkent": res["generated_tashkent"][11:],
        "vaqt_ny": res["generated_ny"][11:],
        "sessiya": res["context"]["session"]["killzone"] or res["context"]["session"]["silver_bullet"] or "-",
        "tavsiya": rec or "kutish",
        "eng_yuqori_model": best["model"],
        "yonalish": best["direction"],
        "ball": f"{best['passed']}/{best['evaluated']}",
        "ball_foiz": round(best["score"] * 100),
        "rr": plan.get("rr"),
        "kirish": plan.get("entry"), "stop": plan.get("stop_loss"), "maqsad": plan.get("take_profit"),
        "natija": "",  # savdodan keyin o'zingiz to'ldirasiz: win / loss / be / olinmadi
        "tags": ["tahlil", res["symbol"].lower(), (rec or "kutish").lower().replace(" ", "-")],
    }


def skills_footer(res: dict) -> str:
    lines = ["\n\n---\n## Bog'liq qaydlar", "[[00_Bosh_sahifa]]"]
    for m in res["models"]["ranking"]:
        links = " · ".join(f"[[{s}]]" for s in SKILL_LINKS.get(m["model"], []))
        lines.append(f"- **{m['model']}** ({m['passed']}/{m['evaluated']}): {links}")
    return "\n".join(lines) + "\n"


def _fmt(x) -> str:
    if x is None:
        return "-"
    if isinstance(x, float):
        return f"{x:.5f}".rstrip("0").rstrip(".") if abs(x) < 1000 else f"{x:.2f}"
    return str(x)


def scan_markdown(res: dict) -> str:
    """Skaner natijasini Obsidian uchun o'qishga qulay qaydga aylantiradi (Claude'siz)."""
    ctx, mdl = res["context"], res["models"]
    s = ctx["session"]
    rec = mdl["recommended_model"]
    out = [f"# {res['symbol']}: avtomatik skaner",
           f"**Vaqt:** Toshkent {res['generated_tashkent']} · NY {res['generated_ny']} · "
           f"**Narx:** {_fmt(ctx['price'])} · **Sessiya:** {s['killzone'] or s['silver_bullet'] or 'killzone emas'}"]
    if res.get("warning"):
        out.append(f"\n> [!warning] {res['warning']}")
    kind = "success" if rec else "info"
    out.append(f"\n> [!{kind}] Tavsiya: {rec or 'kutish'}\n> {mdl['recommendation_note']}")

    out.append("\n## Modellar taqqoslanishi\n| # | Model | Yo'nalish | Ball | R:R | Kirish | Stop | Maqsad |\n|---|---|---|---|---|---|---|---|")
    for i, m in enumerate(mdl["ranking"], 1):
        p = m["plan"] or {}
        out.append(f"| {i} | **{m['model']}** | {m['direction'] or '-'} | {m['passed']}/{m['evaluated']} "
                   f"({round(m['score'] * 100)}%) | {_fmt(p.get('rr'))} | {_fmt(p.get('entry'))} | "
                   f"{_fmt(p.get('stop_loss'))} | {_fmt(p.get('take_profit'))} |")

    out.append("\n## Checklistlar")
    for m in mdl["ranking"]:
        fold = "+" if m["model"] == (rec or mdl["ranking"][0]["model"]) else "-"
        out.append(f"\n> [!example]{fold} {m['model']}: {m['passed']}/{m['evaluated']}")
        for c in m["checks"]:
            mark = {True: "✅", False: "❌", None: "➖"}[c["ok"]]
            out.append(f"> - {mark} **{c['name']}**: {c['detail']}")
        if m.get("plan"):
            out.append(f"> \n> *Reja:* {m['plan']['logic']} (risk {m['plan']['risk_pips']} pips, "
                       f"foyda {m['plan']['reward_pips']} pips)")
        for n in m.get("notes", []):
            out.append(f"> \n> *Izoh:* {n}")

    t = ctx["trend"]
    out.append("\n## Bozor holati")
    out.append(f"- **Trend:** 1D {t['1d']} · 4H {t['4h']} · 1H {t['1h']} · 15m {t['15m']} · 5m {t['5m']}")
    lv = ctx["key_levels"]
    out.append("- **Darajalar:** " + " · ".join(f"{k} {_fmt(v)}" for k, v in lv.items()))
    dol = ctx["draw_on_liquidity"]
    out.append("- **Yuqoridagi likvidlik:** " + (", ".join(f"{d['name']} {_fmt(d['price'])}" for d in dol["above"][:3]) or "-"))
    out.append("- **Pastdagi likvidlik:** " + (", ".join(f"{d['name']} {_fmt(d['price'])}" for d in dol["below"][:3]) or "-"))
    sw = ctx["sweeps_today"]
    out.append("- **Bugungi sweep'lar:** " + (", ".join(f"{x['level']} ({x['side']})" for x in sw) or "yo'q"))
    dr = ctx.get("dealing_range_1h")
    if dr:
        out.append(f"- **1H diapazon:** {_fmt(dr['low'])}–{_fmt(dr['high'])}, narx {dr['zone']} zonada ({dr['position_pct']}%)")
    if ctx.get("smt"):
        out.append(f"- **SMT ({ctx['smt'].get('pair', '-')}):** {ctx['smt'].get('signal') or 'yo`q'}")
    i4 = ctx["indicators"]["4h"]
    out.append(f"- **4H indikatorlar:** RSI {i4['rsi14']} · MACD hist {i4['macd_hist']:.6f} · ATR {_fmt(i4['atr14'])}")
    out.append("\n> [!note] Bu faqat avtomatik texnik skaner. Fundamental tahlil va yangiliklar tekshiruvi uchun "
               "to'liq rejimni ishlating. Bu moliyaviy maslahat emas.")
    return "\n".join(out) + "\n"


def open_in_obsidian(path: Path, vault_dir: Path) -> None:
    """Faylni Obsidian'da ochadi (obsidian:// havolasi orqali)."""
    import sys
    import urllib.parse
    import webbrowser

    rel = path.relative_to(vault_dir).with_suffix("").as_posix()
    uri = (f"obsidian://open?vault={urllib.parse.quote(vault_dir.name)}"
           f"&file={urllib.parse.quote(rel)}")
    try:
        if sys.platform == "win32":
            import os
            os.startfile(uri)  # type: ignore[attr-defined]
        else:
            webbrowser.open(uri)
    except Exception as e:
        print(f"[ogohlantirish] Obsidian ochilmadi: {e}")


def notes_in(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return [f for f in sorted(folder.rglob("*.md")) if not f.name.startswith("_") and f.name != "README.md"]


def recent_reports(folder: Path, symbol: str | None = None, limit: int | None = None,
                   days: int | None = None) -> list[Path]:
    if not folder.exists():
        return []
    files = sorted(folder.glob("*.md"), reverse=True)
    if symbol:
        files = [f for f in files if f.stem.upper().endswith(symbol.upper())]
    if days is not None:
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        files = [f for f in files if f.name[:10] >= since]
    return files[:limit] if limit else files
