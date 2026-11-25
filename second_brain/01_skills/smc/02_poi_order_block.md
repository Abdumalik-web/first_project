# Skill: POI tanlash va Order Block yaroqliligi

**Turi:** texnik (SMC)

## Yaroqli Order Block mezonlari
Grafikdagi har bir "oxirgi qarama-qarshi sham" OB hisoblanmaydi. Yaroqli OB'da quyidagilar bo'lishi kerak:
1. **Likvidlikni olgan:** OB shakllanayotganda yoki undan oldin sweep bo'lgan.
2. **Imbalance (FVG) qoldirgan:** OB'dan keyingi harakat bo'shliq qoldirgan.
3. **BOS yoki CHoCH'ga sabab bo'lgan:** strukturani buzgan.
4. **Mitigatsiya qilinmagan:** narx hali unga qaytmagan (birinchi tegish eng kuchli bo'ladi).
5. **To'g'ri zonada:** bullish OB discount zonada, bearish OB premium zonada.

4–5 mezon bajarilsa, bu kuchli POI. 2 yoki undan kam bo'lsa, zona e'tiborga olinmaydi.

## Supply va Demand zonalari
- **Demand (talab):** narx keskin ko'tarilgan baza (konsolidatsiya) zonasi.
- **Supply (taklif):** narx keskin tushgan baza zonasi.
- Zona tuzilmalari:
  - **RBR** (Rally-Base-Rally) va **DBD** (Drop-Base-Drop): davom etish zonalari.
  - **DBR** (Drop-Base-Rally) va **RBD** (Rally-Base-Drop): reversal zonalari.
- Zona qanchalik tez tark etilgan bo'lsa (kuchli displacement), u shunchalik kuchli.

## Extreme POI va Decisional POI
- **Extreme POI:** harakat boshidagi eng uzoqdagi OB. U strong high yoki low yonida bo'ladi.
  Stop-loss uchun eng xavfsiz joy, lekin narx unga har doim ham yetib bormaydi.
- **Decisional POI:** harakat o'rtasidagi, IDM'dan keyin kelgan OB.
- **Qoida:** IDM olingandan keyingi birinchi yaroqli POI eng yaxshi tanlov.
  Agar u teshib o'tilsa, extreme POI'ga qaraladi.

## Mitigation
Narxning OB'ga qaytib, u yerda qolgan buyurtmalarni "to'ldirishi". Mitigatsiya qilingan OB kuchsizlanadi.
Narx OB'ni sham tanasi bilan teshib o'tsa, u **flip** bo'ladi: endi teskari rolda (breaker sifatida) ishlaydi.

## Likvidlik va POI birikmasi (eng kuchli setup)
**Sweep + POI + Imbalance** bir joyda bo'lishi kerak. Ya'ni narx likvidlikni oladi,
yaroqli OB'ga kiradi va bu OB FVG bilan birga keladi.
