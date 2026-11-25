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
