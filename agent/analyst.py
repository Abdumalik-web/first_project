"""Claude bilan tahlil: 2-chi miya + avtomatik skanerlash natijalari + (ixtiyoriy) chart rasmi.

Fundamental tahlil uchun Claude web_search orqali real vaqtdagi yangiliklarni,
markaziy bank stavkalarini va iqtisodiy kalendarni qidiradi.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

import anthropic

from .config import BRAIN, EFFORT, MODEL, WEB_SEARCH_MAX_USES

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
7. **Hisobot.** Hisobotni `tahlil_hisoboti.md` shabloni bo'yicha, o'zbek tilida yoz.
   Barcha vaqtlarni NY va Toshkent vaqtida ko'rsat.
   Oxiriga "Bu moliyaviy maslahat emas." deb yoz.
"""


def load_knowledge() -> str:
    parts = []
    for rel in KNOWLEDGE_ORDER:
        p = BRAIN / rel
        files = [p] if p.is_file() else sorted(p.glob("*.md")) if p.is_dir() else []
        for f in files:
            if f.name.startswith("_"):
                continue
            parts.append(f"<fayl yo'l=\"{f.relative_to(BRAIN)}\">\n{f.read_text(encoding='utf-8')}\n</fayl>")
    return "# 2-chi miya (bilim bazasi)\n\n" + "\n\n".join(parts) + "\n\n" + TASK_INSTRUCTIONS


def _image_block(path: Path) -> dict:
    media = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
             ".webp": "image/webp", ".gif": "image/gif"}[path.suffix.lower()]
    data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
    return {"type": "image", "source": {"type": "base64", "media_type": media, "data": data}}


def analyze(symbol: str, scan: dict, image: Path | None = None, question: str | None = None,
            max_continuations: int = 5) -> str:
    client = anthropic.Anthropic()
    system = [{"type": "text", "text": load_knowledge(), "cache_control": {"type": "ephemeral"}}]
    content: list[dict] = []
    if image:
        content.append(_image_block(image))
    content.append({"type": "text", "text": (
        f"Aktiv: {symbol}\n"
        + (f"Foydalanuvchi savoli: {question}\n" if question else "")
        + "Skaner natijalari:\n```json\n" + json.dumps(scan, ensure_ascii=False, indent=1) + "\n```"
    )})
    messages: list[dict] = [{"role": "user", "content": content}]
    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": WEB_SEARCH_MAX_USES}]

    texts: list[str] = []
    assistant_blocks: list = []
    for _ in range(max_continuations + 1):
        with client.beta.messages.stream(
            model=MODEL,
            max_tokens=64000,
            system=system,
            messages=messages,
            tools=tools,
            thinking={"type": "adaptive"},
            output_config={"effort": EFFORT},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
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
            messages = [messages[0], {"role": "assistant", "content": assistant_blocks}]
            continue
        break
    print()
    return "".join(texts)
