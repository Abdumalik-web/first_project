# Reklama o'chiruvchi Telegram bot

Guruhdagi reklama havolalarini (t.me, @kanal, Instagram, YouTube, TikTok...),
kanallardan forward qilingan xabarlarni va (ixtiyoriy) videolarni avtomatik o'chiradi.
Adminlar xabarlariga tegmaydi.

## Ishga tushirish
1. Telegramda @BotFather ga `/newbot` yozib token oling.
2. @BotFather da `/setprivacy` -> botingiz -> **Disable** (bot guruhdagi barcha xabarlarni ko'rishi uchun).
3. O'rnatish va ishga tushirish:
   ```
   pip install -r requirements.txt
   export BOT_TOKEN=tokeningiz
   python bot.py
   ```
4. Botni guruhga qo'shing va **admin** qiling ("Xabarlarni o'chirish" huquqi bilan).

## Sozlamalar (muhit o'zgaruvchilari)
| O'zgaruvchi | Ma'nosi |
|---|---|
| `BLOCK_ALL_LINKS=1` | Har qanday havolani o'chiradi (`0` - faqat ro'yxatdagi saytlar) |
| `DELETE_VIDEOS=1` | Oddiy a'zolarning videolarini ham o'chiradi |
| `WARN_TTL=10` | Ogohlantirish xabari necha soniyada o'chadi |

Test: `python test_bot.py`
