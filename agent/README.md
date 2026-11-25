# 🤖 Forex tahlil agenti

Agent `second_brain/` (Obsidian vault) dagi skillar asosida forex juftligini **real vaqtga yaqin** ma'lumot bilan tahlil qiladi.
U har bir savdo modelini grafikka qo'yib ko'radi va eng mosini tavsiya qiladi.

## Qanday ishlaydi

```
1. Ma'lumot   → Yahoo Finance'dan 1D, 1H, 15m, 5m narxlar (bir necha daqiqa kechikish bilan)
                 + SMT uchun korrelyatsion juftlik (EURUSD ↔ GBPUSD va h.k.)
2. Skaner     → Python aniqlaydi: struktura (BOS/CHoCH), likvidlik, sweep, FVG, OB,
                 premium/discount, CRT (4H/Daily), SMT, killzone, indikatorlar
3. Modellar   → Har bir model checklist bo'yicha ball oladi:
                 Klassik TA · ICT · SMC · CRT · Silver Bullet
4. Claude     → 2-chi miyani o'qiydi, internetdan fundamental ma'lumot qidiradi
                 (stavkalar, inflyatsiya, iqtisodiy kalendar, yangiliklar), chart rasmini ko'radi
5. Hisobot    → modellar jadvali, tavsiya, savdo rejasi → second_brain/05_tahlillar/
```

## O'rnatish (bir marta)

1. Python 3.10 yoki undan yangi versiyani o'rnating.
2. Kutubxonalarni o'rnating:
   ```bash
   pip install -r agent/requirements.txt
   ```
3. Anthropic API kalitini oling: https://console.anthropic.com → API Keys.
4. Kalitni muhit o'zgaruvchisiga yozing (kalitni kodga yoki Git'ga yozmang).
   - Windows (PowerShell):
     ```powershell
     setx ANTHROPIC_API_KEY "sk-ant-..."
     ```
   - Mac/Linux:
     ```bash
     export ANTHROPIC_API_KEY="sk-ant-..."
     ```

## Ishlatish

Loyiha papkasida (`first_project/`) ishga tushiring:

To'liq tahlil (texnik + fundamental + model tavsiyasi):
```bash
python -m agent EURUSD
```

Chart skrinshoti bilan (masalan, TradingView'dan):
```bash
python -m agent GBPUSD --rasm chart.png --savol "NY sessiyasi uchun setup bormi?"
```

Claude'siz, faqat modellar balli (bepul va tez):
```bash
python -m agent XAUUSD --offline
```

O'z CSV faylingiz bilan. Fayllarni `second_brain/02_malumotlar/narxlar/EURUSD_5m.csv` kabi nomlab qo'ying:
```bash
python -m agent EURUSD --manba csv
```

Qo'llab-quvvatlanadigan juftliklar: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDJPY, USDCHF, USDCAD,
EURJPY, GBPJPY, EURGBP, XAUUSD, XAGUSD. Yangi juftlik qo'shish uchun uni `agent/config.py` ga yozing.

## Obsidian bilan ishlash

`second_brain/` papkasi Obsidian vault sifatida ishlaydi.

1. Obsidian'ni o'rnating: https://obsidian.md
2. **Open folder as vault** tugmasini bosing va `first_project/second_brain` papkasini tanlang.
3. Community plugins bo'limida **Dataview** plaginini o'rnatib, yoqing.
4. **[[00_Bosh_sahifa]]** ni oching. U yerda so'nggi tahlillar, modellar statistikasi va hisobotlar jadvali bor.

Agent va Obsidian quyidagicha birga ishlaydi:

| Siz Obsidian'da | Agent |
|---|---|
| `07_qaydlar/` ga o'z qoidalaringiz va kuzatuvlaringizni yozasiz | har bir tahlilda ularni o'qiydi |
| `01_skills/` dagi skillarni tahrirlaysiz yoki yangisini qo'shasiz | keyingi tahlilda yangilangan bilim bilan ishlaydi |
| — | `05_tahlillar/` ga metadata va `[[havola]]`lar bilan hisobot yozadi |
| tahlil faylidagi `natija:` maydoniga `win`, `loss`, `be` yoki `olinmadi` deb yozasiz | statistika va hisobotda hisobga oladi |
| `06_jurnal/savdo_jurnali.md` ni to'ldirasiz | xatolardan o'rganadi, hisobotda natijalarni tahlil qiladi |
| — | shu juftlik bo'yicha o'tgan 3 ta tahlilni o'qib, ular bilan solishtiradi |

### Vault'dan hisobot olish

Haftalik hisobot:
```bash
python -m agent hisobot
```

30 kunlik, faqat bitta juftlik bo'yicha:
```bash
python -m agent hisobot --kun 30 --juftlik EURUSD
```

Vault bo'yicha erkin savol:
```bash
python -m agent hisobot --kun 30 --savol "Qaysi model eng ko'p ishladi va qaysi sessiyada?"
```

Hisobot `08_hisobotlar/` papkasiga saqlanadi va manba tahlillarga `[[havola]]` qiladi.
Ularni Obsidian grafigida (Graph view) ko'rish mumkin.

## Natija misoli (`--offline`)

```
▶ SMC         bullish  ball 5/9 (56%)  R:R 2.03
   ✅ POI to'g'ri zonada: OB 0.98833–0.98927
   ✅ OB kamida 4/5 yaroqlilik mezoniga javob beradi: 5/5
   ❌ Inducement (IDM) olingan: IDM hali olinmagan
   ...
★ Tavsiya: kutish. Hech bir model hozir to'liq setup bermayapti.
```

- **Tavsiya qachon beriladi:** eng yuqori ball ≥ 60% va R:R ≥ 1:2 bo'lsa. Aks holda agent "kutish" deydi.
- **➖ belgisi:** bu punktni avtomatik tekshirib bo'lmaydi (masalan, yangiliklar). Uni Claude fundamental qismda tekshiradi.

## Xarajat

Har bir to'liq tahlil bitta Claude so'rovi. Unga 2-chi miya (~15K token, keshlanadi),
skaner natijasi va 8 tagacha web qidiruv kiradi. Narxlar: https://www.anthropic.com/pricing

## Cheklovlar

- Yahoo Finance forex narxlari bir necha daqiqa kechikadi. Bu tick-darajadagi real vaqt emas.
  Scalping uchun o'z brokeringizdan CSV eksport qiling.
- ICT, SMC va CRT naqshlarini kod aniq qoidalar bilan aniqlaydi. Siz grafikda ko'radigan belgilardan
  farq qilishi mumkin, shuning uchun rasm bilan solishtiring.
- Bu moliyaviy maslahat emas. Strategiyani avval demo hisobda sinab ko'ring.
