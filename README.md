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
   - bo'sh o'rin yetarli bo'lsa;
   - vaqt oralig'i bir xil yoki qo'shni bo'lsa.

   Tuman **qat'iy shart emas**: Toshkentdan chiqqan yo'lovchi Toshkentdagi, Farg'onadan
   chiqqan yo'lovchi Farg'onadagi **eng yaqin** haydovchiga yuboriladi. Mos haydovchilar
   **masofa** bo'yicha tartiblanadi: yo'lovchini olib ketish nuqtasi (lokatsiya yoki tuman
   markazi) bilan haydovchining joylashuvi (lokatsiya yoki u tanlagan birinchi tuman) orasidagi km.
   Yo'lovchining tumani haydovchi e'lonida bo'lmasa +20 km, vaqt oralig'i farq qilsa +40 km
   jarima qo'shiladi — shunda tumani mos haydovchi ustun turadi, lekin u bo'lmasa eng yaqin
   boshqa haydovchiga darhol yuboriladi (haydovchiga «tumani e'loningizda yo'q» deb yoziladi).
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
| `ADMIN_IDS` | Adminlar Telegram ID raqamlari, vergul bilan (`111,222`) | bo'sh |

## Admin panel

1. Botga `/id` yozing — sizning Telegram ID raqamingiz chiqadi.
2. `.env` faylga `ADMIN_IDS=123456789` deb yozing (bir nechta bo'lsa vergul bilan) va botni qayta ishga tushiring.
3. Botga `/admin` yozing:
   - 📊 **Statistika** — foydalanuvchilar, haydovchilar, yo'lovchilar, faol e'lonlar, moslashuvlar;
   - 🚗 **Faol e'lonlar** va 🧍 **Kutayotgan so'rovlar** ro'yxati (telefon va ID bilan);
   - 📢 **Hammaga xabar yuborish** — matn, rasm yoki video.
4. **👤 Foydalanuvchilar** (yoki `/users`): botdan foydalanuvchilar ro'yxati — ism, username,
   telefon, nechta e'lon/so'rov bergani, qachon qo'shilgani; filtr (haydovchilar, yo'lovchilar,
   bloklanganlar), sahifalash va **Excel'da ochiladigan fayl** (CSV) qilib yuklab olish.
5. Buyruqlar: `/user <id | @username | ism | telefon>`, `/ban <id>`, `/unban <id>`,
   `/del_trip <raqam>`, `/del_req <raqam>`.

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
  middlewares.py # bloklangan foydalanuvchilarni to'xtatish
  voice.py       # ovoz -> matn -> e'lon ma'lumotlari
  group_parser.py # guruh xabarlaridan yo'lovchini ajratish
  ads.py         # admin bo'lgan guruhlarga reklama va haydovchi e'lonlari
  bonus.py       # yo'lovchi uzatish uchun bonus ballar
  referral.py    # taklif havolalari va majburiy guruh
  handlers/      # common, admin, driver, passenger, handover, offers, voice, group
tests/           # matching, service va to'liq oqim testlari
```

Tuman koordinatalari taxminiy (tuman markazlari); aniqroq natija uchun foydalanuvchilar lokatsiya yuborishi tavsiya etiladi.

## Guruhlardan yo'lovchi topish (bepul)

Botni taksi guruhlariga qo'shsangiz, u guruhda **hech narsa yozmaydi**, faqat o'qiydi.
Yo'lovchi xabarini topsa (masalan *«Ertaga Qo'qondan Toshkentga 2 kishi kerak 90 123 45 67»*),
undan yo'nalish, tuman, sana, vaqt, kishi soni, telefon va username'ni ajratadi va
**faol e'loni bor, mos keladigan eng yaqin haydovchilarga** (ko'pi bilan 5 ta) yuboradi.

- Lotin, kirill va rus tilidagi odatiy xabarlarni tushunadi (kalit so'zlar bo'yicha).
- Haydovchilarning o'z e'lonlari («joy bor», «ketyapmiz», «Cobalt»...) e'tiborsiz qoldiriladi.
- Bir xil e'lon bir nechta guruhga tashlansa, haydovchiga bir marta boradi (6 soat ichida).
- Sana aytilmasa, bugungi va ertangi e'lonlar bilan solishtiriladi.

**Sozlash (guruhda admin bo'lish shart emas):**

1. BotFather → `/setprivacy` → botingiz → **Disable**. Busiz bot guruhdagi oddiy xabarlarni ko'rmaydi.
2. Botni guruhga qo'shing. Agar bot privacy o'chirilishidan **oldin** qo'shilgan bo'lsa,
   uni guruhdan chiqarib, qayta qo'shing.
3. Admin panel → **👥 Guruhlar**: qaysi guruhdan nechta yo'lovchi topilgani.

## Guruhlarga avtomatik reklama

Bot **admin** bo'lgan guruhlarga ikki xil reklamani **navbatma-navbat** joylaydi
(har 10 daqiqada bittadan, sozlanadi):

1. *«Farg'onadan Toshkentga yuramiz!»* — tugma: **«Farg'ona ➜ Toshkent: joy band qilish»**
2. *«Toshkentdan Farg'onaga yuramiz!»* — tugma: **«Toshkent ➜ Farg'ona: joy band qilish»**

Tugma botning shaxsiy chatiga olib boradi va yo'lovchi so'rovi **yo'nalish tanlangan holda**
boshlanadi. Yo'lovchi tumani va joylashuvini kiritadi, bot uni eng yaqin haydovchiga yuboradi.

- Har yo'nalishning yangi reklamasidan oldin o'sha yo'nalishning eskisi o'chiriladi —
  guruhda har yo'nalishdan bittadan reklama turadi.
- Oxirgi reklamadan beri guruhda yangi xabar bo'lmasa, qayta joylanmaydi
  (o'chirish: `/reklama_faollik_off` — shunda har safar joylanadi).
- Bot oddiy a'zo bo'lgan guruhlarga reklama joylamaydi (faqat o'qiydi).

Boshqaruv (admin): `/reklama` (holati va har bir guruh nima uchun kutayotgani), `/reklama_on`, `/reklama_off`, `/reklama_vaqt 30`,
`/reklama_matn1 <matn>` (Farg'ona ➜ Toshkent), `/reklama_matn2 <matn>` (Toshkent ➜ Farg'ona),
`/reklama_tugma1`, `/reklama_tugma2`, `/reklama_hozir`.
Botni guruhda admin qilganda **«Delete messages»** huquqi bo'lsin.

## Haydovchi e'lonlarini guruhlarga joylash

Har bir haydovchi e'loni bot admin bo'lgan guruhlarga **har soatda** (sozlanadi) avtomatik joylanadi
(haydovchidan so'ralmaydi; birinchi joylanganda haydovchiga bu haqda xabar boradi):
yo'nalish (tumanlar ➜ Toshkent yoki aksincha), sana va vaqt, bo'sh joylar, mashina, narx,
**telefon raqami va Telegram akkaunti**, hamda «Bot orqali joy band qilish» tugmasi.

- Har soatda e'lonning eski posti o'chirilib, yangisi joylanadi — guruhda har haydovchidan bittadan.
- E'lon yakunlansa, bekor qilinsa yoki joylar to'lsa — post guruhdan avtomatik o'chiriladi.
- Haydovchi «📋 Mening e'lonlarim» ➜ «📢 Guruhlarga joylash» bilan istalgan payt yoqib-o'chiradi.
- Admin: `/elon` (holati), `/elon_on`, `/elon_off`, `/elon_vaqt 60`, `/elon_hozir`.

**Guruh havolasi.** Har bir haydovchiga (e'loni guruhga birinchi joylanganda: *«Yuborgan
e'loningiz guruhlarimizga joylandi»*) va har bir yo'lovchiga (birinchi so'rovidan keyin)
guruh havolasi **faqat bir marta** yuboriladi. Havolani almashtirish: `/guruh_link https://t.me/...`,
o'chirish: `/guruh_link off`.

## Yo'lovchi uzatish va bonus ballar

Haydovchi o'zi olib keta olmaydigan yo'lovchini (mashina to'lgan, boshqa yo'nalish, botda
bo'lmagan begona odam qo'ng'iroq qilgan va h.k.) **«📤 Yo'lovchi uzatish»** orqali botga kiritadi:
yo'nalish, tumanlar, sana, vaqt, necha kishi, telefon raqami. Bot uni eng yaqin boshqa haydovchiga
yuboradi.

- Uzatilgan yo'lovchini boshqa haydovchi **qabul qilsa** — uzatgan haydovchiga
  **har bir uzatish uchun N ball** (standart 10, necha kishi bo'lishidan qat'i nazar) yoziladi. Faqat qabul qilinganda — soxta raqam bilan
  ball yig'ib bo'lmaydi.
- Keyin bekor qilinsa (yo'lovchi yoki olgan haydovchi bekor qilsa) — ball qaytarib olinadi.
- Bir raqamni bir kunga ikki marta kiritib bo'lmaydi.
- Yo'lovchi raqami faqat uni olgan haydovchiga ko'rsatiladi.
- **«✅ To'ldim»** («📋 Mening e'lonlarim»da) yoki mashina bot orqali to'lsa — bot haydovchiga
  «Oq yo'l!» tilaydi va yo'lovchi uzatib bonus yig'ishni taklif qiladi.
- **«💰 Bonusim»** — balans, tarix va pulga aylantirish sharti.

Admin: `/bonuslar` (eng ko'p yig'ganlar), `/bonus_tolash <id> <ball> [izoh]` (pul to'landi —
ball yechiladi, foydalanuvchiga xabar boradi), `/bonus_qosh <id> <ball>`, `/bonus_ball 10`,
`/bonus_info <shart matni>`.

## Taklif havolalari va majburiy guruh

- **«👥 Do'stlarni taklif qilish»** — har bir foydalanuvchiga shaxsiy havolalar: botga
  (`t.me/<bot>?start=r<id>`) va guruhga (bot yaratgan shaxsiy taklif havolasi) hamda «Ulashish» tugmasi.
- Shu havolalar orqali kelgan **yangi** odam botga ham, guruhga ham qo'shilgach, taklif qilganga
  **5 ball** (`/taklif_ball` bilan o'zgaradi). Bir odam uchun bir marta; botda oldin bo'lgan odam
  hisoblanmaydi.
- **Majburiy guruh** (`/majburiy_guruh <id>`): guruhga qo'shilmagan odam botdan foydalana olmaydi —
  bot «👥 Guruhga qo'shilish» va «✅ Qo'shildim» tugmalarini ko'rsatadi. Guruhdan chiqsa — yana
  to'xtatiladi. Adminlar tekshirilmaydi. `/majburiy_guruh off` — o'chirish.
- Bot o'sha guruhda **admin** bo'lishi kerak («Invite users via link» huquqi bilan) — shaxsiy
  guruh havolalari va kim qo'shilganini ko'rish uchun.

## Ovozli xabar orqali e'lon

Foydalanuvchi botga ovozli xabar yuborishi mumkin, masalan: *«Ertaga ertalab Qo'qondan
Toshkentga, Chilonzorga, ikki kishimiz»*. Bot:

1. ovozni matnga aylantiradi (standart: OpenAI Whisper);
2. Claude yordamida matndan yo'nalish, tuman, sana, vaqt, kishi soni va boshqalarni ajratadi;
3. faqat **yetishmayotgan** ma'lumotni tugmalar bilan so'raydi va tasdiqlashni ko'rsatadi.

Rol aniq bo'lmasa (haydovchi yoki yo'lovchi), bot so'raydi. E'lon to'ldirilayotgan paytda
ovozli xabar yuborilsa, u o'sha e'londagi bo'sh maydonlarni to'ldiradi.

Yoqish uchun `.env` ga ikkita kalit yozing va botni qayta ishga tushiring:

```
ANTHROPIC_API_KEY=...   # console.anthropic.com
STT_API_KEY=...         # platform.openai.com (yoki boshqa OpenAI-mos xizmat, STT_URL bilan)
```

Kalitlar bo'lmasa, bot ovozli xabarga «tugmalar orqali tanlang» deb javob beradi.

## Serverga (VPS) joylash — bot 24/7 ishlaydi

Ubuntu 22.04/24.04 VPS kerak. Windows PowerShell'dan:

```powershell
# 1. Kompyuterdagi botni to'xtating (Ctrl+C) — bitta token bilan ikki joyda ishlab bo'lmaydi
# 2. Loyihani arxivlang (.env va taxi.db ham ketadi)
cd $HOME
tar -czf bot.tgz --exclude=.venv --exclude=.git --exclude=__pycache__ first_project
# 3. Serverga yuboring va kiring
scp bot.tgz root@SERVER_IP:/root/
ssh root@SERVER_IP
```

Serverda:

```bash
mkdir -p /opt/taxi-bot && tar -xzf /root/bot.tgz -C /opt/taxi-bot --strip-components=1
bash /opt/taxi-bot/deploy/setup.sh
```

Foydali buyruqlar: `journalctl -u taxi-bot -f` (loglar), `systemctl restart taxi-bot`, `systemctl stop taxi-bot`.

**Yangilash (eng oson):** serverga kirib (`ssh root@SERVER_IP`) bitta buyruq yozing —
server GitHub'dan eng yangi versiyani o'zi yuklab oladi, `.env` va baza o'zgarmaydi:

```bash
bash /opt/taxi-bot/deploy/update.sh
```

**Yangilash (kompyuterdan):** arxivni `.env` va bazasiz yarating, yuboring va yana `setup.sh` ni ishga tushiring:

```powershell
tar -czf bot.tgz --exclude=.venv --exclude=.git --exclude=__pycache__ --exclude=.env --exclude=*.db first_project
scp bot.tgz root@SERVER_IP:/root/
ssh root@SERVER_IP "tar -xzf /root/bot.tgz -C /opt/taxi-bot --strip-components=1 && bash /opt/taxi-bot/deploy/setup.sh"
```
