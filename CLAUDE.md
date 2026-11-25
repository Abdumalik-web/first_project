# Forex tahlil yordamchisi: Claude uchun yo'riqnoma

Bu loyiha foydalanuvchining forex tahlil tizimi:
- `second_brain/` Obsidian vault (2-chi miya): skillar, qoidalar, shablonlar, tahlillar va jurnal.
- `agent/` texnik skaner. U narxlarni yuklaydi, ICT, SMC, CRT, Silver Bullet va klassik TA modellarini grafikka qo'yib, checklist bo'yicha baholaydi.

Foydalanuvchi bilan **o'zbek tilida** gaplash. U dasturchi emas: buyruqlarni o'zing ishga tushir, natijani Obsidian'da ko'rsat.
Platforma: Windows. Python'ni `py` bilan chaqir (`python` buyrug'i Microsoft Store yorlig'iga tushib qolishi mumkin).

## "XXX tahlil qil" (masalan "EURUSD tahlil qil")

1. **Skaner.** `py -m agent EURUSD --offline --ochma` ni ishga tushir.
   - Natija `second_brain/05_tahlillar/<sana_vaqt>_EURUSD.md` (frontmatter bilan) va `second_brain/05_tahlillar/_json/<xuddi shu nom>.json` ga yoziladi.
   - Buyruq chiqargan `✅ Saqlandi:` qatoridan fayl nomini ol.
2. **Bilim.** Quyidagilarni o'qi:
   - `second_brain/00_agent/system_prompt.md` va `ish_tartibi.md`;
   - `03_qoidalar/risk_menejment.md`;
   - `04_shablonlar/tahlil_hisoboti.md`;
   - `07_qaydlar/` dagi foydalanuvchi qaydlari;
   - kerakli skill fayllari (`01_skills/ict`, `smc`, `crt`, `texnik`).
   Shu juftlik bo'yicha `05_tahlillar/` dagi oxirgi 2–3 ta tahlilni ham ko'rib chiq.
3. **Skaner natijasi.** JSON faylni o'qi:
   - `models.ranking` da har bir model checklist bo'yicha baholangan (`ok: null` degani avtomatik tekshirilmagan);
   - `context` da struktura, likvidlik, FVG/OB, CRT, SMT va sessiya ma'lumotlari bor (vaqtlar New York vaqtida).
4. **Fundamental.** Internetdan qidir:
   - ikkala valyuta markaziy bankining stavkasi va siyosati;
   - so'nggi inflyatsiya va bandlik ma'lumotlari;
   - bugun va shu hafta chiqadigan yuqori ta'sirli yangiliklar (iqtisodiy kalendar);
   - so'nggi muhim yangiliklar va DXY holati.
   Har bir raqamga manba va sana yoz. Topilmagan narsani o'ylab topma.
   Yangilik bo'yicha `ok: null` punktlarini kalendar asosida to'ldir.
5. **Chart rasmi.** Agar foydalanuvchi rasm bergan bo'lsa, uni skaner natijasi bilan solishtir.
6. **Hisobot.** Skaner yaratgan `.md` faylni yangila:
   - frontmatter'ni saqla, faqat `manba:` ni `"claude"` ga o'zgartir;
   - frontmatter'dan keyin shablon bo'yicha hisobot yoz: qisqa xulosa, texnik, fundamental, modellar jadvali (model | yo'nalish | ball | R:R | kuchli/zaif punkt), qaysi model eng mos va nega, savdo rejasi (1% risk uchun pozitsiya hajmi formulasi bilan), ssenariylar;
   - vaqtlarni NY va Toshkent vaqtida ko'rsat;
   - ishlatgan skillaringni `[[02_likvidlik]]` kabi havola qil;
   - skaner yozgan matnni o'chirma: uni hisobotdan keyin "## Ilova: skaner natijasi" sarlavhasi ostida qoldir;
   - oxirida "Bu moliyaviy maslahat emas." deb yoz.
7. **Obsidian'da ochish.** Quyidagi buyruq bilan och (NOMI kengaytmasiz fayl nomi):
   `start "" "obsidian://open?vault=second_brain&file=05_tahlillar/NOMI"`
   PowerShell'da: `Start-Process "obsidian://open?vault=second_brain&file=05_tahlillar/NOMI"`
8. Chatda faqat qisqa xulosa ber: tavsiya, yo'nalish, asosiy daraja va hisobot ochilgani.

Tavsiya qoidasi: biror model faqat ball ≥ 60% va R:R ≥ 1:2 bo'lsa tavsiya qilinadi. Aks holda "kutish" deb yoz va nimani kutish kerakligini ayt.
Risk qoidalari (`03_qoidalar/`) har qanday signaldan ustun turadi.

## "Haftalik hisobot" yoki vault bo'yicha savol

1. `second_brain/05_tahlillar/` dagi so'nggi 7 kunlik tahlillarni o'qi (frontmatter: `tavsiya`, `ball`, `rr`, `natija`).
2. `second_brain/06_jurnal/` ni o'qi.
3. Quyidagilarni yoz:
   - qaysi model necha marta tavsiya qilingan;
   - natijalar (`natija:` maydoni va jurnal bo'yicha);
   - takrorlanayotgan xatolar;
   - keyingi hafta rejasi.
4. Hisobotni `second_brain/08_hisobotlar/<YYYY-MM-DD>_hisobot_7kun.md` ga frontmatter bilan saqla:
   `turi: "hisobot"`, `sana`, `davr_kun: 7`, `tags: ["hisobot"]`.
   Manba tahlillarga `[[fayl_nomi]]` havolalarini qo'y.
5. Hisobotni Obsidian'da och (7-qadamdagi kabi, `08_hisobotlar/NOMI`).

## Boshqa qoidalar
- Narx va raqamlarni faqat skaner natijasidan yoki internet manbasidan ol, o'zing o'ylab topma.
- `second_brain/.obsidian/` papkasiga tegma (foydalanuvchining Obsidian sozlamalari).
- Skill yoki qoidani o'zgartirishdan oldin foydalanuvchidan so'ra.
- Foydalanuvchi savdo natijasini aytsa (masalan "EURUSD win bo'ldi"), tegishli tahlil faylidagi `natija:` maydonini yangila va `06_jurnal/savdo_jurnali.md` ga qator qo'sh.
