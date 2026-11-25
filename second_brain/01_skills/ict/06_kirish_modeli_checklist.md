# Skill: ICT kirish modeli va checklist

**Turi:** texnik (ICT), barcha ICT skillarini birlashtiradi
**Qachon ishlatiladi:** Forex juftligi bo'yicha savdo rejasini tuzishda.

## Model (ketma-ketlik)
1. **HTF bias** (Weekly/Daily): DOL qayerda? Narx premium zonadami yoki discount'dami?
   → `01_bozor_strukturasi.md`, `02_likvidlik.md`
2. **HTF PD array:** narx Daily yoki 4H'dagi FVG, OB yoki breaker'ga yetdimi?
   → `03_pd_arraylar.md`
3. **Vaqt:** hozir killzone yoki Silver Bullet oynasimi?
   → `04_vaqt_va_sessiyalar.md`
4. **Likvidlik sweep:** sessiya high/low, PDH/PDL yoki EQH/EQL olindimi?
5. **SMT:** korrelyatsion juftlik buni tasdiqlayaptimi?
   → `05_smt_divergensiya.md`
6. **MSS va displacement:** LTF'da (5m yoki 1m) struktura teskari tomonga buzildimi?
7. **Kirish:** displacement qoldirgan FVG yoki OB'da. Ideal holatda OTE va discount yoki premium bilan mos keladi.
8. **Stop-loss:** sweep qilingan swing'ning orqasiga.
9. **Take-profit:** keyingi qarama-qarshi likvidlik (DOL).
   Masalan TP1 ichki likvidlik, TP2 tashqi likvidlik.
10. **Risk:** `03_qoidalar/risk_menejment.md` bo'yicha. R:R kamida 1:2.

## Checklist (agent har bir punktni ✅ yoki ❌ bilan belgilaydi)
- [ ] HTF bias aniq
- [ ] Narx HTF PD array'da yoki to'g'ri zonada (discount yoki premium)
- [ ] Killzone yoki Silver Bullet vaqti
- [ ] Likvidlik sweep bo'ldi
- [ ] SMT tasdiqladi (ixtiyoriy, lekin ishonchni oshiradi)
- [ ] MSS displacement bilan bo'ldi
- [ ] Kirish uchun FVG yoki OB bor
- [ ] Yaqin 30 daqiqada yuqori ta'sirli yangilik (red folder) yo'q
- [ ] R:R ≥ 1:2

**Baholash:** 7 yoki undan ko'p ✅ bo'lsa, setup yuqori sifatli. 5–6 ta bo'lsa, o'rta sifatli.
5 tadan kam bo'lsa, savdo qilinmaydi.

## Cheklovlar (agent buni foydalanuvchiga ochiq aytadi)
- ICT konsepsiyalari subyektiv. Turli treyderlar bir xil grafikni turlicha belgilashi mumkin.
- Uning samaradorligi ilmiy jihatdan tasdiqlanmagan. Strategiyani avval demo hisobda
  va jurnal (`06_jurnal/`) orqali sinab ko'rish kerak.
- Agent narxlarni faqat `02_malumotlar/narxlar/` dagi ma'lumotlardan oladi. Grafikni "ko'rmasdan"
  darajalarni o'ylab topmaydi.

## Atamalar lug'ati
| Atama | Ma'nosi |
|---|---|
| BSL / SSL | Buy-side / Sell-side liquidity |
| BOS / MSS | Break of Structure / Market Structure Shift |
| FVG / IFVG | Fair Value Gap / Inversion FVG |
| OB | Order Block |
| CE | Consequent Encroachment (50%) |
| OTE | Optimal Trade Entry (0.62–0.79) |
| DOL | Draw on Liquidity |
| PD Array | Premium/Discount massivi (FVG, OB va boshqalar) |
| AMD / PO3 | Accumulation–Manipulation–Distribution / Power of 3 |
| SMT | Smart Money Technique divergensiyasi |
| PDH / PDL | Previous Day High / Low |
| HTF / LTF | Higher / Lower Timeframe |
