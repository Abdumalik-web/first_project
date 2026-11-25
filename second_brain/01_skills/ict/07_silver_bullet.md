# Skill: ICT Silver Bullet

**Turi:** texnik (ICT). Vaqtga asoslangan, kun ichidagi savdo modeli.
**Qachon ishlatiladi:** Kun ichida aniq 1 soatlik oynalarda bitta yuqori sifatli kirishni izlash uchun.

## Mohiyati
Silver Bullet aniq **1 soatlik vaqt oynasi** ichida ishlatiladigan oddiy model.
G'oyasi quyidagicha:
1. Narx eng yaqin likvidlik tomon (DOL) displacement bilan harakat qiladi.
2. Bu harakat **FVG** qoldiradi.
3. Narx shu FVG'ga qaytganda kirish qilinadi.
4. Maqsad keyingi likvidlik pulidir.

## Vaqt oynalari
Vaqtlar New York (ET) vaqtida berilgan. Toshkent vaqtiga o'tkazish uchun qishda +10, yozda +9 soat qo'shiladi.

| Oyna | NY (ET) | Toshkent (qish) | Toshkent (yoz) |
|---|---|---|---|
| **London SB** | 03:00 – 04:00 | 13:00 – 14:00 | 12:00 – 13:00 |
| **NY AM SB** | 10:00 – 11:00 | 20:00 – 21:00 | 19:00 – 20:00 |
| **NY PM SB** | 14:00 – 15:00 | 00:00 – 01:00 | 23:00 – 00:00 |

- **NY AM SB (10:00–11:00)** eng ko'p ishlatiladigan va eng mashhur oyna.
- **Qoida:** FVG aynan shu 1 soat ichida **hosil bo'lishi** kerak. Oynadan oldin hosil bo'lgan FVG hisobga olinmaydi.
  Kirish ham oyna ichida bo'lishi lozim.

## Timeframe
- Bias va DOL Daily, 4H yoki 1H grafikda aniqlanadi.
- Setup va kirish **1m–5m** grafikda izlanadi (asosan 1m yoki 3m).

## Model (qadamma-qadam)
1. **Oynadan oldin bias:** HTF'da DOL qayerda?
   Bu ICT ish tartibidagi qadam (`02_likvidlik.md`, `04_vaqt_va_sessiyalar.md`).
   Yaqin likvidliklarni belgila: sessiya high/low, PDH/PDL, EQH/EQL, oynadan oldingi soat high/low'i.
2. **Likvidlik sweep (tavsiya etiladi):** oyna boshida yoki undan biroz oldin narx
   qarama-qarshi tomondagi yaqin likvidlikni oladi.
   Masalan, bullish holatda 09:30–10:00 oralig'idagi low sweep qilinadi.
3. **Displacement va MSS:** narx DOL yo'nalishida kuchli harakat qiladi, strukturani buzadi va **FVG** qoldiradi.
4. **Kirish:** narx shu FVG'ga qaytganda limit order bilan kiriladi.
   Kirish nuqtasi FVG chetida yoki CE (50%) darajasida bo'ladi.
5. **Stop-loss:**
   - FVG'ni yaratgan 1-shamning ortiga;
   - konservativ variant: sweep qilingan swing ortiga.
6. **Take-profit:** DOL yo'nalishidagi keyingi likvidlik pulining oldiga.
   Qisman foyda olish mumkin: avval ichki likvidlikda, keyin tashqi likvidlikda.
7. **Minimal masofa:** kirishdan maqsadgacha yetarli joy bo'lishi kerak.
   Forex uchun odatda kamida taxminan 10–15 pips talab qilinadi. Joy kam bo'lsa, savdo olinmaydi.

## Bullish misol (EURUSD, NY AM SB)
- HTF bias bullish. DOL: PDH 1.0890.
- 09:50 da narx 09:00 dan keyingi low'ni (1.0832) sweep qildi.
- 10:07 da 1m grafikda kuchli ko'tariluvchi displacement bo'ldi, MSS sodir bo'ldi va bullish FVG (1.0841–1.0845) qoldi.
- 10:15 da narx FVG'ga qaytdi. Kirish 1.0845 da.
- Stop 1.0829 da, maqsad 1.0888 da.
- Risk 16 pips, potensial foyda 43 pips. R:R ≈ 1:2.7.

*(Raqamlar faqat namuna uchun berilgan. Haqiqiy tahlilda agent ularni `02_malumotlar/narxlar/` dan oladi.)*

## Checklist
- [ ] HTF bias va DOL aniq
- [ ] Hozir Silver Bullet oynasi ichidamiz
- [ ] Oynadan oldin yoki oyna boshida qarama-qarshi likvidlik sweep qilindi
- [ ] DOL yo'nalishida displacement va MSS bo'ldi
- [ ] FVG **oyna ichida** hosil bo'ldi
- [ ] Maqsadgacha yetarli masofa bor (forex uchun taxminan 10–15 pips yoki undan ko'p)
- [ ] R:R ≥ 1:2
- [ ] Oyna ichida yuqori ta'sirli yangilik yo'q.
      Masalan, 10:00 da chiqadigan yangilik NY AM SB oynasini bekor qilishi mumkin.

**Baholash:** 7 yoki undan ko'p ✅ bo'lsa, savdo olinadi. 6 yoki kamroq bo'lsa, savdo olinmaydi.

## Qoidalar va xatolar
- **Bitta oynada bitta savdo.** Agar u stop bo'lsa, keyingi oyna kutiladi. Revenge trade qilinmaydi.
- HTF bias'ga qarshi FVG'lar e'tiborsiz qoldiriladi.
- Oyna tugagach, kirish uchun hosil bo'lgan setup'lar bekor qilinadi.
- Agar narx FVG'ni sham tanasi bilan teskari yo'nalishda yorib o'tsa, setup bekor bo'ladi (FVG IFVG'ga aylanadi).

## Boshqa skillar bilan bog'liqligi
- **SMT** (`05_smt_divergensiya.md`): oyna ichidagi sweep'ni korrelyatsion juftlik tasdiqlasa, ishonch oshadi.
- **CRT** (`../crt/`): agar 1H yoki 4H CRT'ning manipulation fazasi Silver Bullet oynasiga to'g'ri kelsa, bu kuchli birikma.
- **SMC** (`../smc/`): oyna ichidagi sweep ko'pincha inducement'ning olinishi bo'ladi.

## Cheklov
Silver Bullet ham boshqa ICT modellari kabi subyektiv va samaradorligi ilmiy tasdiqlanmagan.
Avval demo hisobda sinab ko'rish va natijalarni `06_jurnal/` ga yozib borish kerak.
