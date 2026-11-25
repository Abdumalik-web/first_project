---
tags: [moc]
---
# 🧠 Bosh sahifa

> Bu Obsidian vault'ning markaziy sahifasi. Jadvallar ishlashi uchun **Dataview** plaginini yoqing:
> Settings → Community plugins → Browse → "Dataview" → Install → Enable.

## 📈 So'nggi tahlillar
```dataview
TABLE symbol AS "Juftlik", sessiya AS "Sessiya", tavsiya AS "Tavsiya", eng_yuqori_model AS "Eng yuqori model",
      yonalish AS "Yo'nalish", ball AS "Ball", rr AS "R:R", manba AS "Manba", natija AS "Natija"
FROM "05_tahlillar"
WHERE turi = "tahlil"
SORT file.name DESC
LIMIT 20
```

## 🏆 Qaysi model necha marta tavsiya qilingan
```dataview
TABLE length(rows) AS "Soni", round(sum(rows.ball_foiz) / length(rows)) AS "O'rtacha ball %"
FROM "05_tahlillar"
WHERE turi = "tahlil"
GROUP BY tavsiya
SORT length(rows) DESC
```

## ✅ Natijasi yozilgan savdolar
Tahlil faylining metadata qismidagi `natija:` maydonini to'ldiring: `win`, `loss`, `be` yoki `olinmadi`.
```dataview
TABLE symbol AS "Juftlik", tavsiya AS "Model", rr AS "R:R", natija AS "Natija"
FROM "05_tahlillar"
WHERE natija AND natija != ""
SORT file.name DESC
```

## 📊 Davriy hisobotlar
```dataview
LIST FROM "08_hisobotlar" SORT file.name DESC LIMIT 10
```

## 🗂 Bilim bazasi
- **Agent:** [[system_prompt]] · [[ish_tartibi]]
- **Klassik TA:** [[trend_va_darajalar]] · [[indikatorlar]] · [[patternlar]]
- **ICT:**
  - [[01_bozor_strukturasi]] · [[02_likvidlik]] · [[03_pd_arraylar]] · [[04_vaqt_va_sessiyalar]]
  - [[05_smt_divergensiya]] · [[06_kirish_modeli_checklist]] · [[07_silver_bullet]]
- **SMC:** [[00_smc_va_ict]] · [[01_struktura_va_inducement]] · [[02_poi_order_block]] · [[smc/03_kirish_modeli_checklist|SMC checklist]]
- **CRT:** [[01_crt_asoslari]] · [[02_timeframe_va_vaqt]] · [[crt/03_kirish_modeli_checklist|CRT checklist]]
- **Fundamental:** [[aksiya_tahlili]] · [[kripto_tahlili]] · [[makro_tahlil]]
- **Qoidalar:** [[risk_menejment]] · **Jurnal:** [[savdo_jurnali]] · **Shablon:** [[tahlil_hisoboti]]
- **Mening qaydlarim:** `07_qaydlar/` papkasi
