# Reklama o'chiruvchi Telegram bot

Guruhdagi reklama havolalarini (t.me, @kanal, Instagram, YouTube, TikTok...),
kanallardan forward qilingan xabarlarni va (ixtiyoriy) videolarni avtomatik o'chiradi.
"Guruhga qo'shildi" / "guruhdan chiqdi" tizim xabarlarini ham o'chiradi.
Adminlar xabarlariga tegmaydi.

## Ishga tushirish
1. Telegramda @BotFather ga `/newbot` yozib token oling.
2. @BotFather da `/setprivacy` -> botingiz -> **Disable** (bot guruhdagi barcha xabarlarni ko'rishi uchun).
3. O'rnatish va ishga tushirish:
   ```
   pip install -r requirements.txt
   python bot.py
   ```
   Bot tokenni o'zi so'raydi (yozilgani ekranda ko'rinmaydi).
   Yoki oldindan bering: Linux `export BOT_TOKEN=...`, PowerShell `$env:BOT_TOKEN="..."`.
4. Botni guruhga qo'shing va **admin** qiling ("Xabarlarni o'chirish" huquqi bilan).

## Guruhdagi buyruqlar (faqat adminlar uchun)
| Buyruq | Vazifasi |
|---|---|
| `/rasm` | Oddiy a'zolar rasmlarini o'chirishni yoqadi / o'chiradi |
| `/video` | Oddiy a'zolar videolarini o'chirishni yoqadi / o'chiradi |
| `/majburiy` | Guruhga yozishdan oldin botga start bosishni majburiy qiladi / bekor qiladi |
| `/sozlamalar` | Joriy sozlamalarni ko'rsatadi |

Har bir guruh sozlamasi alohida `settings.json` faylida saqlanadi.

## Boshqa botga start bosish majburiyati
`REQUIRED_BOT_TOKEN` ga boshqa botingiz tokeni berilsa, a'zolar o'sha botga start
bosmaguncha guruhga yoza olmaydi: xabari o'chiriladi va start tugmasi ko'rsatiladi.
Bot buni o'sha bot nomidan foydalanuvchiga "yozmoqda..." holatini yuborib tekshiradi
(faqat start bosganlarga yuborish mumkin). Tasdiq 24 soat eslab qolinadi.

## Sozlamalar (muhit o'zgaruvchilari)
| O'zgaruvchi | Ma'nosi |
|---|---|
| `BLOCK_ALL_LINKS=1` | Har qanday havolani o'chiradi (`0` - faqat ro'yxatdagi saytlar) |
| `DELETE_VIDEOS=1` | Videolarni o'chirish (standart qiymat) |
| `DELETE_PHOTOS=1` | Rasmlarni o'chirish (standart qiymat) |
| `REQUIRED_BOT_TOKEN=...` | Start bosilishi shart bo'lgan boshqa botning tokeni |
| `WARN_TTL=10` | Ogohlantirish xabari necha soniyada o'chadi |

Test: `python test_bot.py`
