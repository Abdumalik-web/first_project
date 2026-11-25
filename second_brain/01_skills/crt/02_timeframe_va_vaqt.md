# Skill: CRT timeframe'lari va vaqt

**Turi:** texnik (CRT)

## HTF va LTF juftliklari
CRT katta timeframe'da (HTF) aniqlanadi, kirish esa kichik timeframe'da (LTF) izlanadi.

| CRT timeframe (HTF) | Kirish timeframe (LTF) | Savdo turi |
|---|---|---|
| Monthly | Daily / 4H | Pozitsion |
| Weekly | 4H / 1H | Swing |
| **Daily** | 1H / 15m | Kun ichi va swing |
| **4H** | 15m / 5m | Kun ichi (eng ko'p ishlatiladi) |
| 1H | 5m / 1m | Scalp |

**Qoida:** LTF kirish signali faqat HTF CRT yo'nalishida qabul qilinadi.

## 4H shamlarning vaqti
4H shamlar broker serverining vaqtiga qarab boshqa soatlarda ochiladi.
CRT tahlilida odatda **New York vaqti** bo'yicha bo'lingan shamlar ishlatiladi.
Bunda shamlar 18:00, 22:00, 02:00, 06:00, 10:00 va 14:00 da ochiladi.
Ba'zi CRT treyderlari 01:00, 05:00 va 09:00 NY vaqtini kalit soat sifatida ishlatadi.
Agent qaysi bo'linish ishlatilganini **hisobotda ochiq ko'rsatadi**.

Toshkent vaqtiga o'tkazish: qishda +10 soat, yozda +9 soat (`../ict/04_vaqt_va_sessiyalar.md`).

Kun ichida eng muhim 4H shamlar killzone'larga to'g'ri keladi:
- London killzone (02:00–05:00 NY) davridagi sham ko'pincha manipulation fazasi bo'ladi.
- New York AM killzone (07:00–10:00 NY) davridagi sham ko'pincha manipulation yoki distribution fazasi bo'ladi.

## Kunlik CRT (Daily)
- **Kechagi kun** diapazon, ya'ni 1-sham sifatida olinadi: PDH va PDL.
- **Bugungi kun** PDH yoki PDL'ni sweep qilib, ichkariga qaytsa, bu CRT setup.
- Haftalik variant: o'tgan hafta diapazoni (PWH va PWL), bu haftaning dushanba–seshanba sweep'i.

## Key Level (KL) bilan birlashtirish
CRT eng kuchli bo'lgan holat: 2-shamning sweep'i **HTF muhim darajada** sodir bo'lsa.
Masalan, HTF FVG, OB, eski high yoki low, yoki NWOG.
Bunday sweep'ga oddiy CRT emas, **"KL'dagi CRT"** deyiladi.
Buning uchun quyidagi fayllarga qarang:
- `../ict/03_pd_arraylar.md`
- `../smc/02_poi_order_block.md`
