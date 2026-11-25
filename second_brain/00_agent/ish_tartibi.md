# Ish tartibi (Workflow)

Agent har bir tahlil so'rovida shu qadamlarni bajaradi.

## 1. Savolni aniqlash
- Qaysi aktiv? (ticker: BTC, AAPL, EURUSD)
- Qaysi vaqt oralig'i? (scalp / swing / uzoq muddat)
- Qanday tahlil kerak: texnik, fundamental yoki ikkalasi?

## 2. Ma'lumot yig'ish
- `02_malumotlar/aktivlar/<TICKER>.md` faylida aktiv profili bor.
- `02_malumotlar/narxlar/<TICKER>_*.csv` fayllarida narx tarixi bor.
- `02_malumotlar/hisobotlar/` papkasida moliyaviy hisobotlar bor.
- Ma'lumot eskirgan bo'lsa (sanasini tekshir), foydalanuvchini ogohlantir.

## 3. Texnik tahlil (`01_skills/texnik/`)
Tartib: trend → darajalar → indikatorlar → patternlar → hajm.

## 4. Fundamental tahlil (`01_skills/fundamental/`)
- Aksiya bo'lsa: hisobotlar → nisbatlar → baholash.
- Kripto bo'lsa: tokenomika → on-chain → ekotizim.
- Ikkala holatda ham makro omillarni ko'rib chiq.

## 5. Sintez
- Texnik va fundamental natijalar bir-biriga mos keladimi? Mos kelmasa, sababini yoz.
- Bull va bear ssenariylarini, ularning ehtimolini yoz.

## 6. Risk tekshiruvi (`03_qoidalar/`)
- Stop-loss, pozitsiya hajmi va R:R nisbatini hisobla.
- Qoidaga zid bo'lsa, savdo taklif qilma.

## 7. Hisobot va saqlash
- Hisobotni `04_shablonlar/tahlil_hisoboti.md` shabloni bo'yicha yoz.
- Uni `05_tahlillar/YYYY-MM-DD_<TICKER>.md` nomi bilan saqla.
