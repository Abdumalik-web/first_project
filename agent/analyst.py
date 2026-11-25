"""Claude bilan ishlash: 2-chi miya (Obsidian vault) + skaner natijalari + chart rasmi.

Ikki rejim:
- analyze(): bitta juftlikni tahlil qilish (fundamental uchun web_search bilan);
- summarize(): vault'dagi tahlillar va jurnal asosida davriy hisobot.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

import anthropic

from .config import BRAIN, EFFORT, MODEL, NOTES_DIR, REPORTS_DIR, WEB_SEARCH_MAX_USES
from .vault import notes_in, recent_reports

KNOWLEDGE_ORDER = [
    "00_agent/system_prompt.md",
    "00_agent/ish_tartibi.md",
    "03_qoidalar",
    "01_skills/texnik",
    "01_skills/ict",
    "01_skills/smc",
    "01_skills/crt",
    "01_skills/fundamental/makro_tahlil.md",
    "04_shablonlar/tahlil_hisoboti.md",
    "06_jurnal",
]

TASK_INSTRUCTIONS = """
## Avtomatik tahlil rejimi

Senga Python skaneri hisoblagan ma'lumotlar JSON ko'rinishida beriladi:
- `context`: struktura, likvidlik, FVG/OB, CRT, SMT, indikatorlar va sessiya (vaqtlar New York vaqtida);
- `models`: har bir savdo modeli (Klassik TA, ICT, SMC, CRT, Silver Bullet) checklist bo'yicha baholangan.
  `ok=null` degani avtomatik tekshirib bo'lmagan, uni o'zing tekshirasan.

Vazifang:
1. **Fundamental tahlil.** web_search orqali quyidagilarni qidir:
   - har ikki valyuta markaziy bankining joriy stavkasi va siyosati;
   - so'nggi inflyatsiya va bandlik ma'lumotlari;
   - bugun va shu hafta chiqadigan yuqori ta'sirli yangiliklar (iqtisodiy kalendar);
   - so'nggi muhim yangiliklar va DXY holati.
   Har bir raqamga manba va sana yoz. Topa olmagan narsangni "topilmadi" deb yoz, raqamlarni o'ylab topma.
2. **Yangilik tekshiruvi.** `ok=null` bo'lgan yangilik punktlarini kalendar asosida to'ldir.
3. **Chart rasmi.** Agar rasm berilgan bo'lsa, uni skaner natijalari bilan solishtir.
   Rasmda boshqa narsa ko'rinsa, buni ayt.
4. **Modellarni solishtir.** Jadval tuz: model | yo'nalish | ball | R:R | asosiy kuchli/zaif punkt.
5. **Tavsiya.** Hozirgi grafikka qaysi model eng to'g'ri kelishini asosla.
   Fundamental fon texnik yo'nalishga zid bo'lsa yoki yaqinda muhim yangilik bo'lsa, ishonch darajasini pasaytir.
   Hech bir model yaroqli bo'lmasa, "savdo qilmaslik / kutish" deb tavsiya qil va nimani kutish kerakligini yoz.
6. **Savdo rejasi.** Tavsiya etilgan model rejasini risk qoidalari bo'yicha tekshir.
   Pozitsiya hajmini 1% risk uchun formula bilan ko'rsat.
7. **O'tgan tahlillar.** Agar shu juftlik bo'yicha o'tgan tahlillar berilgan bo'lsa, ular bilan solishtir.
   Nima o'zgardi? Oldingi tavsiya to'g'ri chiqdimi?
8. **Hisobot.** Hisobotni `tahlil_hisoboti.md` shabloni bo'yicha, o'zbek tilida yoz.
   Barcha vaqtlarni NY va Toshkent vaqtida ko'rsat.
   Hisobot Obsidian'da ochiladi, shuning uchun ishlatgan skillaringni `[[fayl_nomi]]` ko'rinishida havola qil.
   Masalan: [[02_likvidlik]], [[05_smt_divergensiya]], [[01_crt_asoslari]].
   Oxiriga "Bu moliyaviy maslahat emas." deb yoz.
"""

SUMMARY_INSTRUCTIONS = """
## Davriy hisobot rejimi

Senga Obsidian vault'dagi tahlil hisobotlari (metadata bilan), savdo jurnali va foydalanuvchi qaydlari beriladi.
Shu ma'lumotlar asosida o'zbek tilida, Obsidian uchun Markdown hisobot yoz:
1. **Umumiy ko'rinish.** Davr ichida qaysi juftliklar tahlil qilingan, qaysi model necha marta tavsiya etilgan (jadval).
2. **Natijalar.** Jurnaldagi haqiqiy savdolarni tahlillar bilan solishtir.
   Qaysi model yaxshi ishladi, qaysi biri yomon ishladi? R natijalarini hisobla.
   Jurnal bo'sh bo'lsa, buni ochiq ayt va natija haqida taxmin qilma.
3. **Takrorlanayotgan naqshlar.** Qaysi checklist punktlari ko'p hollarda bajarilmagan? Qaysi sessiyalar faol bo'lgan?
4. **Xatolar va darslar.** `06_jurnal` uchun "Takrorlanayotgan xatolar" ro'yxatiga qo'shish taklif qilinadigan punktlar.
5. **Keyingi davr rejasi.** Qaysi juftlik va model'ga e'tibor berish kerak?

Havolalar uchun `[[...]]` ishlat: tahlil fayllariga fayl nomi bilan (kengaytmasiz), skillarga ham.
Faqat berilgan ma'lumotlarga tayan, raqamlarni o'ylab topma.
"""


def _read_files(rel: str) -> list[Path]:
    p = BRAIN / rel
    if p.is_file():
        return [p]
    return [f for f in sorted(p.rglob("*.md")) if not f.name.startswith("_")] if p.is_dir() else []


def load_knowledge(extra_instructions: str = TASK_INSTRUCTIONS) -> str:
    parts = []
    for rel in KNOWLEDGE_ORDER:
        for f in _read_files(rel):
            parts.append(f"<fayl yo'l=\"{f.relative_to(BRAIN)}\">\n{f.read_text(encoding='utf-8')}\n</fayl>")
    # Foydalanuvchining shaxsiy Obsidian qaydlari (07_qaydlar)
    for f in notes_in(NOTES_DIR):
        parts.append(f"<qayd yo'l=\"07_qaydlar/{f.relative_to(NOTES_DIR).as_posix()}\">\n"
                     f"{f.read_text(encoding='utf-8')}\n</qayd>")
    return "# 2-chi miya (Obsidian vault)\n\n" + "\n\n".join(parts) + "\n\n" + extra_instructions


def _image_block(path: Path) -> dict:
    media = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
             ".webp": "image/webp", ".gif": "image/gif"}[path.suffix.lower()]
    data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
    return {"type": "image", "source": {"type": "base64", "media_type": media, "data": data}}


def _call(system_text: str, content: list[dict], tools: list[dict] | None = None,
          max_continuations: int = 5) -> str:
    """Streaming so'rov: pause_turn ni davom ettiradi, refusal'ni qayta ishlaydi."""
    client = anthropic.Anthropic()
    system = [{"type": "text", "text": system_text, "cache_control": {"type": "ephemeral"}}]
    first = {"role": "user", "content": content}
    messages: list[dict] = [first]
    extra = {"tools": tools} if tools else {}
    texts: list[str] = []
    assistant_blocks: list = []
    for _ in range(max_continuations + 1):
        with client.beta.messages.stream(
            model=MODEL,
            max_tokens=64000,
            system=system,
            messages=messages,
            thinking={"type": "adaptive"},
            output_config={"effort": EFFORT},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            **extra,
        ) as stream:
            for text in stream.text_stream:
                print(text, end="", flush=True)
            response = stream.get_final_message()

        texts += [b.text for b in response.content if b.type == "text"]
        if response.stop_reason == "refusal":
            cat = getattr(response.stop_details, "category", None) if response.stop_details else None
            texts.append(f"\n\n[Model so'rovni rad etdi: {cat}]")
            break
        if response.stop_reason == "pause_turn":
            # Server web_search tsiklini davom ettiradi; "davom et" deb yozish shart emas
            assistant_blocks += list(response.content)
            messages = [first, {"role": "assistant", "content": assistant_blocks}]
            continue
        break
    print()
    return "".join(texts)


def analyze(symbol: str, scan: dict, image: Path | None = None, question: str | None = None) -> str:
    content: list[dict] = []
    if image:
        content.append(_image_block(image))
    past = recent_reports(REPORTS_DIR, symbol, limit=3)
    past_txt = "".join(f"\n<otgan_tahlil fayl=\"{p.stem}\">\n{p.read_text(encoding='utf-8')[:6000]}\n</otgan_tahlil>"
                       for p in past)
    content.append({"type": "text", "text": (
        f"Aktiv: {symbol}\n"
        + (f"Foydalanuvchi savoli: {question}\n" if question else "")
        + (f"\nShu juftlik bo'yicha o'tgan tahlillar:{past_txt}\n" if past else "")
        + "\nSkaner natijalari:\n```json\n" + json.dumps(scan, ensure_ascii=False, indent=1) + "\n```"
    )})
    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": WEB_SEARCH_MAX_USES}]
    return _call(load_knowledge(), content, tools)


def summarize(material: str, period: str, question: str | None = None) -> str:
    text = (f"Davr: {period}\n" + (f"Foydalanuvchi savoli: {question}\n" if question else "")
            + "\nVault ma'lumotlari:\n" + material)
    return _call(load_knowledge(SUMMARY_INSTRUCTIONS), [{"type": "text", "text": text}])
