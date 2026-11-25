# Skill: SMC kirish modeli va checklist

**Turi:** texnik (SMC). Forex uchun ICT checklisti bilan birga ishlatiladi.

## Kirish turlari
| Tur | Qanday | Afzalligi | Kamchiligi |
|---|---|---|---|
| **Risk entry** | POI'ga limit order qo'yiladi, LTF tasdig'i kutilmaydi | Yuqori R:R | Stop urilishi ehtimoli yuqori |
| **Confirmation entry** | POI ichida LTF CHoCH kutiladi, kirish yangi hosil bo'lgan LTF OB yoki FVG'dan | Ishonchliroq | R:R pastroq, ba'zi harakatlar o'tkazib yuboriladi |
| **Sweep entry** | LTF'da IDM yoki likvidlik sweep'i + CHoCH | Aniq invalidatsiya darajasi | Tajriba talab qiladi |

Agent sukut bo'yicha (default) **confirmation entry**ni taklif qiladi.

## Model
1. **HTF:** tashqi struktura va trend yo'nalishini aniqla, keyin premium yoki discount zonani belgila.
2. **HTF POI:** yaroqli OB yoki zona tanla (`02_poi_order_block.md` mezonlari bo'yicha).
3. **IDM:** POI oldidagi inducement olindimi?
4. **Narx POI'da:** imkon bo'lsa, killzone vaqtida (`../ict/04_vaqt_va_sessiyalar.md`).
5. **LTF CHoCH:** sham tanasi bilan yopilgan bo'lishi kerak. Displacement bo'lsa, yanada yaxshi.
6. **Kirish:** LTF CHoCH'ni yaratgan OB yoki FVG'dan.
7. **Stop-loss:** LTF swing ortiga yoki HTF POI ortiga.
8. **Take-profit:** TP1 ichki likvidlik yoki weak high/low. TP2 HTF tashqi likvidlik.
9. **Boshqarish:** TP1 olinganda stop breakeven'ga suriladi.

## Checklist
- [ ] HTF tashqi trend aniq
- [ ] POI to'g'ri zonada (premium yoki discount)
- [ ] OB kamida 4 ta yaroqlilik mezoniga javob beradi
- [ ] IDM olingan
- [ ] Likvidlik sweep bo'ldi
- [ ] LTF CHoCH sham tanasi bilan tasdiqlangan
- [ ] Imbalance (FVG) mavjud
- [ ] SMT tasdig'i bor (ixtiyoriy)
- [ ] R:R ≥ 1:2

**Baholash:** 7 yoki undan ko'p ✅ bo'lsa, yuqori sifatli setup. 5–6 ta bo'lsa, o'rta sifatli.
5 tadan kam bo'lsa, savdo qilinmaydi.

## Ko'p uchraydigan xatolar
- Har bir oxirgi shamni OB deb hisoblash.
- IDM olinmasdan POI'ga kirish.
- Sham soyasining o'tishini BOS deb hisoblash.
- Ichki CHoCH'ni trend o'zgarishi deb qabul qilish.
- HTF trendga qarshi, faqat LTF signalga qarab savdo qilish.

## Cheklov
SMC ham ICT kabi subyektiv yondashuv va samaradorligi ilmiy tasdiqlanmagan.
Agent buni foydalanuvchiga ochiq aytadi va strategiyani avval demo hisobda sinab ko'rishni tavsiya qiladi.
