# Farg'ona ⇄ Toshkent taksi bot

Telegram bot: **haydovchi** va **yo'lovchini** bir-biriga moslab, yo'lovchiga
**eng yaqin** mos haydovchini topadi va so'rovni haydovchiga yuboradi.
Yo'nalish: Farg'ona viloyati tumanlari ➜ Toshkent va Toshkent ➜ Farg'ona viloyati.

## Qanday ishlaydi

1. **Haydovchi** «🚗 Haydovchiman» tugmasini bosib e'lon beradi:
   yo'nalish → qaysi tumanlardan yo'lovchi oladi (masalan Qo'qon, Dang'ara, Buvayda, Uchko'prik)
   → sana → vaqt oralig'i → bo'sh o'rinlar → mashina → narx → telefon → joylashuv (ixtiyoriy).
2. **Yo'lovchi** «🧍 Yo'lovchiman» tugmasini bosib so'rov qoldiradi:
   yo'nalish → Farg'ona tumani → Toshkent tumani → sana → vaqt → kishi soni
   → lokatsiya (ixtiyoriy) → izoh → telefon.
3. **Moslashtirish** (`bot/matching.py`). Haydovchi mos keladi, agar:
   - yo'nalish va sana bir xil bo'lsa;
   - yo'lovchining tumani haydovchi tanlagan tumanlar ichida bo'lsa;
   - bo'sh o'rin yetarli bo'lsa;
   - vaqt oralig'i bir xil yoki qo'shni bo'lsa.

   Mos haydovchilar **masofa** bo'yicha tartiblanadi: yo'lovchini olib ketish nuqtasi
   (lokatsiya yoki tuman markazi) bilan haydovchining joylashuvi (lokatsiya yoki u
   tanlagan birinchi tuman) orasidagi km. Vaqt oralig'i farq qilsa, jarima qo'shiladi.
4. So'rov **eng yaqin** haydovchiga «✅ Olaman / ❌ Rad etish» tugmalari bilan yuboriladi.
   - **Olaman** → ikkalasiga bir-birining ismi va telefon raqami yuboriladi, o'rin kamayadi.
   - **Rad etish** yoki 5 daqiqa javob yo'q → so'rov keyingi eng yaqin haydovchiga o'tadi.
   - Mos haydovchi yo'q bo'lsa, so'rov kutadi; yangi haydovchi e'lon berishi bilan unga yuboriladi.
5. «📋 Mening e'lonlarim» — e'lon/so'rovni ko'rish, bekor qilish, yo'lovchilar ro'yxati.
   «📍 Joylashuvni yangilash» — haydovchi hozirgi joyini yuboradi, eng yaqin yo'lovchilar aniqroq topiladi.

Sanasi o'tgan e'lon va so'rovlar avtomatik yopiladi (Toshkent vaqti bo'yicha).

## O'rnatish va ishga tushirish

1. [@BotFather](https://t.me/BotFather) da yangi bot yarating va tokenni oling.
2. Python 3.10+ o'rnatilgan bo'lsin, so'ng:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # .env ichiga BOT_TOKEN ni yozing
python -m bot.main
```

### Sozlamalar (`.env`)

| O'zgaruvchi | Ma'nosi | Standart |
|---|---|---|
| `BOT_TOKEN` | BotFather tokeni | — (majburiy) |
| `DB_PATH` | SQLite fayli | `taxi.db` |
| `OFFER_TIMEOUT_MIN` | Haydovchi javob berishi uchun daqiqa | `5` |

## Testlar

```bash
pip install -r requirements-dev.txt
pytest
```

## Loyiha tuzilmasi

```
bot/
  main.py        # ishga tushirish
  config.py      # .env sozlamalari
  regions.py     # Farg'ona va Toshkent tumanlari, koordinatalar, vaqt oraliqlari
  matching.py    # moslashtirish va "eng yaqin"ni hisoblash
  service.py     # so'rovni haydovchiga yuborish, qabul/rad, taymaut
  db.py          # SQLite (aiosqlite)
  keyboards.py, texts.py
  handlers/      # common, driver, passenger, offers
tests/           # matching, service va to'liq oqim testlari
```

Tuman koordinatalari taxminiy (tuman markazlari); aniqroq natija uchun foydalanuvchilar lokatsiya yuborishi tavsiya etiladi.
