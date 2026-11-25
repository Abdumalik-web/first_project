# 🧠 2-chi miya (Second Brain)

Bu papka AI agentning **bilim bazasi**. Agent tahlil qilishdan oldin shu yerdagi
fayllarni o'qiydi. U skillar (qanday tahlil qilish), ma'lumotlar (nimani tahlil
qilish) va qoidalardan (qanday qaror qilish) foydalanadi.

## Tuzilma

| Papka | Vazifasi |
|---|---|
| `00_agent/` | Agentning "shaxsiyati": rolli, ish tartibi, system prompt |
| `01_skills/texnik/` | Texnik tahlil skillari: trend, indikatorlar, patternlar, darajalar |
| `01_skills/ict/` | Forex uchun ICT va SMT skillari: struktura, likvidlik, FVG/OB, killzone'lar, SMT, kirish modeli, Silver Bullet |
| `01_skills/smc/` | Smart Money Concepts: ichki va tashqi struktura, CHoCH, inducement, POI/OB yaroqliligi, kirish turlari |
| `01_skills/crt/` | Candle Range Theory: 3 shamli model, CRT High/Low/50%, HTF va LTF juftliklari, kirish modeli |
| `01_skills/fundamental/` | Fundamental tahlil skillari: moliyaviy hisobotlar, baholash, kripto tokenomika |
| `02_malumotlar/` | Xom ma'lumotlar: aktiv profillari, narxlar (CSV), moliyaviy hisobotlar |
| `03_qoidalar/` | Risk menejment va savdo qoidalari. Agent ulardan chetga chiqmaydi |
| `04_shablonlar/` | Tahlil hisobotlari uchun shablonlar |
| `05_tahlillar/` | Agent yozgan tayyor tahlillar (tarix) |
| `06_jurnal/` | Savdo jurnali va xulosalar. Agent o'z xatolaridan o'rganadi |

## Qanday ishlaydi

```
Savol ("BTC ni tahlil qil")
   │
   ▼
1. 00_agent/ish_tartibi.md   → agent qadamlarni biladi
2. 02_malumotlar/            → aktiv haqidagi ma'lumotni topadi
3. 01_skills/texnik/         → texnik tahlil qiladi
4. 01_skills/fundamental/    → fundamental tahlil qiladi
5. 03_qoidalar/              → riskni tekshiradi
6. 04_shablonlar/            → hisobotni shablon bo'yicha yozadi
7. 05_tahlillar/             → natijani saqlaydi
```

## Bilim qo'shish

- **Yangi skill:** `01_skills/` ichiga `.md` fayl qo'shing. Uni `_skill_shabloni.md` asosida yozing.
- **Yangi aktiv:** `02_malumotlar/aktivlar/` ichiga `_aktiv_shabloni.md` nusxasini qo'shing.
- **Narx ma'lumoti:** `02_malumotlar/narxlar/TICKER_1d.csv` (`date,open,high,low,close,volume`).
- **Hisobot:** `02_malumotlar/hisobotlar/` ichiga PDF yoki MD qo'ying.

> ⚠️ Agent tahlillari moliyaviy maslahat emas. Yakuniy qarorni har doim o'zingiz qabul qilasiz.
