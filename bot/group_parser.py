"""Guruhdagi oddiy matnli e'lonlardan yo'lovchini ajratish (kalit so'zlar bo'yicha, bepul).

Lotin, kirill (o'zbek) va rus tilidagi odatiy xabarlarni tushunadi, masalan:
  "Ertaga Qo'qondan Toshkentga 2 kishi kerak 90 123 45 67"
  "Тошкентдан Риштонга 1 киши керак"
  "Нужно такси из Ташкента в Коканд завтра утром"
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

TO_TASHKENT, FROM_TASHKENT = "F2T", "T2F"

# --- Kirill -> lotin --------------------------------------------------------
_CYR = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "j", "з": "z",
    "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "x", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sh",
    "ъ": "", "ы": "i", "ь": "", "э": "e", "ю": "yu", "я": "ya", "ў": "o", "қ": "q", "ғ": "g",
    "ҳ": "h",
}


def normalize(text: str) -> str:
    """Kichik harf, kirill -> lotin, apostroflarni olib tashlash, ortiqcha belgilarsiz."""
    t = text.lower()
    t = "".join(_CYR.get(ch, ch) for ch in t)
    t = re.sub(r"[ʻʼ'`‘’ʹ]", "", t)  # qo'qon -> qoqon
    t = re.sub(r"[^\w\s+@]", " ", t)  # tinish belgilari -> bo'sh joy
    return re.sub(r"\s+", " ", t).strip()


# --- Joy nomlari -------------------------------------------------------------
# Har bir kod uchun normallashtirilgan nomlar (apostrofsiz, lotin)
FERGANA_ALIASES: dict[str, list[str]] = {
    "fargona_sh": ["fargona", "fergana", "fargana", "fergane"],
    "margilon": ["margilon", "margilan", "margelan"],
    "qoqon": ["qoqon", "kokand", "koqon", "quqon", "qoqan", "kokan"],
    "quvasoy": ["quvasoy", "kuvasay", "kuvasoy"],
    "oltiariq": ["oltiariq", "oltiyariq", "altyaryk", "altiarik", "oltiarik"],
    "bagdod": ["bagdod", "bogdod", "bagdad"],
    "beshariq": ["beshariq", "besharik", "besharyk"],
    "buvayda": ["buvayda", "buvaida"],
    "dangara": ["dangara", "dangar"],
    "fargona_t": ["vodil"],
    "furqat": ["furqat", "furkat"],
    "qoshtepa": ["qoshtepa", "kushtepa", "qushtepa", "langar"],
    "quva": ["quva", "kuva"],
    "rishton": ["rishton", "rishtan"],
    "sox": ["sox", "sokh"],
    "toshloq": ["toshloq", "tashlak", "toshlok"],
    "uchkoprik": ["uchkoprik", "uchkuprik"],
    "ozbekiston": ["yaypan", "yaypon"],
    "yozyovon": ["yozyovon", "yazyavan", "yozyavon"],
}
TASHKENT_ALIASES: dict[str, list[str]] = {
    "bektemir": ["bektemir"],
    "chilonzor": ["chilonzor", "chilanzar", "chilonzar"],
    "mirobod": ["mirobod", "mirabad"],
    "mirzo_ulugbek": ["ulugbek"],
    "olmazor": ["olmazor", "almazar", "olmazar"],
    "sergeli": ["sergeli", "sergili"],
    "shayxontohur": ["shayxontohur", "shayxantaxur", "shayxontoxur"],
    "uchtepa": ["uchtepa"],
    "yakkasaroy": ["yakkasaroy", "yakkasaray"],
    "yashnobod": ["yashnobod", "yashnabad"],
    "yunusobod": ["yunusobod", "yunusabad"],
    "yangihayot": ["yangihayot", "yangixayot"],
}
TASHKENT_WORDS = ["toshkent", "tashkent", "toshkand", "tashkand", "tosh"]

# O'zbek / rus qo'shimchalari (so'z oxiri)
SUFFIXES = {
    "", "dan", "tan", "ga", "ka", "qa", "da", "ning", "ni", "dagi", "gacha", "dagilar",
    "lik", "liklar", "a", "e", "u", "om", "y", "dek",
}
FROM_SUFFIXES = {"dan", "tan"}
TO_SUFFIXES = {"ga", "ka", "qa", "gacha"}


def _match(word: str, alias: str) -> str | None:
    """So'z alias + qo'shimchadan iborat bo'lsa, qo'shimchani qaytaradi."""
    if word.startswith(alias) and word[len(alias):] in SUFFIXES:
        return word[len(alias):]
    return None


@dataclass
class Place:
    kind: str      # "fergana" / "tashkent"
    code: str | None
    index: int     # so'z tartibi
    suffix: str
    prev: str      # oldingi so'z (rus: "iz", "v", "do")


def find_places(words: list[str]) -> list[Place]:
    out: list[Place] = []
    for i, w in enumerate(words):
        prev = words[i - 1] if i else ""
        for alias in TASHKENT_WORDS:
            suf = _match(w, alias)
            if suf is not None and not (alias == "tosh" and suf not in FROM_SUFFIXES | TO_SUFFIXES):
                out.append(Place("tashkent", None, i, suf, prev))
                break
        else:
            hit = None
            for code, aliases in FERGANA_ALIASES.items():
                for alias in aliases:
                    suf = _match(w, alias)
                    if suf is not None:
                        hit = Place("fergana", code, i, suf, prev)
                        break
                if hit:
                    break
            if hit:
                out.append(hit)
    return out


def find_tashkent_district(words: list[str]) -> str | None:
    for w in words:
        for code, aliases in TASHKENT_ALIASES.items():
            if any(_match(w, a) is not None for a in aliases):
                return code
    return None


# --- Kim yozgan: yo'lovchi yoki haydovchi ------------------------------------
PASSENGER_PATTERNS = [
    r"\bkerak\b", r"\bkere\b", r"\bkishi\b", r"\bkishimiz\b", r"\bodam\b", r"\bodammiz\b",
    r"\bmashina kerak", r"\btaksi kerak", r"\btaxi kerak", r"\bjoy kerak", r"\bketaman\b",
    r"\bboraman\b", r"\bketamiz\b", r"\bboramiz\b", r"\bnujn", r"\bnujen\b", r"\bishu\b",
    r"\bchelovek", r"\bpassajir\b",
]
DRIVER_PATTERNS = [
    r"\bjoy bor\b", r"\bjoylar bor\b", r"\bbosh joy\b", r"\bboshjoy\b", r"\bolib ketaman\b",
    r"\bolib ketamiz\b", r"\bolamiz\b", r"\bolaman\b", r"\bketyapmiz\b", r"\bketyapman\b",
    r"\bketyapti\b", r"\bkam joy\b", r"\bjoy qoldi\b", r"\bjoyi bor\b", r"\bmashina bor\b",
    r"\bavto bor\b", r"\bpochta olamiz\b",
    r"\byest mesto\b", r"\bsvobodn", r"\bvozmu\b", r"\bvozmem\b", r"\bedem\b", r"\bedu\b",
    r"\bcobalt\b", r"\bkobalt\b", r"\bgentra\b", r"\bnexia\b", r"\bneksiya\b", r"\blacetti\b",
    r"\blasetti\b", r"\bmalibu\b", r"\bspark\b", r"\bdamas\b", r"\bkaptiva\b", r"\bcaptiva\b",
    r"\bonix\b", r"\btracker\b", r"\bjentra\b", r"\bkoblat\b",
]

NUM_WORDS = {"bir": 1, "ikki": 2, "ikkita": 2, "uch": 3, "uchta": 3, "tort": 4, "torta": 4,
             "birta": 1, "odin": 1, "dva": 2, "dvoe": 2, "tri": 3, "troe": 3, "chetire": 4}
SEATS_RE = re.compile(r"\b(\d|" + "|".join(NUM_WORDS) + r")\s*(?:ta\s*)?(kishi|odam|joy|chel|chelovek|passajir|nafar)")
PHONE_RE = re.compile(r"(?:\+?998[\s\-\(]*)?\(?(\d{2})\)?[\s\-]*(\d{3})[\s\-]*(\d{2})[\s\-]*(\d{2})(?!\d)")
USERNAME_RE = re.compile(r"@([A-Za-z][A-Za-z0-9_]{4,31})")

DATE_WORDS = {
    0: ["bugun", "hozir", "segodnya", "seychas", "srochno", "shoshilinch"],
    1: ["ertaga", "zavtra"],
    2: ["indinga", "poslezavtra", "ertadan keyin", "ertaga emas indinga"],
}
SLOT_WORDS = {
    "morning": ["ertalab", "tongda", "erta bilan", "utrom", "utro", "sahar"],
    "day": ["kunduzi", "tushlik", "tushdan oldin", "obed", "dnem", "peshin", "abetda"],
    "evening": ["kechqurun", "oqshom", "tushdan keyin", "vecherom", "vecher", "asr"],
    "night": ["kechasi", "tunda", "tungi", "nochyu", "noch", "yarim tun"],
}


@dataclass
class Lead:
    direction: str
    fergana_code: str
    tashkent_code: str | None = None
    day_offset: int | None = None  # 0 bugun, 1 ertaga, 2 indinga; None — aytilmagan
    slot: str | None = None
    seats: int | None = None
    phones: list[str] = field(default_factory=list)
    usernames: list[str] = field(default_factory=list)

    def trip_date(self, today: date) -> str | None:
        return None if self.day_offset is None else (today + timedelta(days=self.day_offset)).isoformat()


def _score(text: str, patterns: list[str]) -> int:
    return sum(1 for p in patterns if re.search(p, text))


def extract_phones(raw: str) -> list[str]:
    out = []
    for m in PHONE_RE.finditer(raw):
        code = m.group(1)
        if code[0] not in "2356789":  # O'zbekiston kodlari: 20, 33, 50, 55, 71, 77, 88, 90-99 ...
            continue
        num = "+998" + "".join(m.groups())
        if num not in out:
            out.append(num)
    return out


def _direction(places: list[Place]) -> str | None:
    tk = [p for p in places if p.kind == "tashkent"]
    fg = [p for p in places if p.kind == "fergana"]
    if not tk or not fg:
        return None
    t, f = tk[0], fg[0]
    # Qo'shimchalar bo'yicha: "Toshkentdan", "Qo'qonga" -> T2F
    if t.suffix in FROM_SUFFIXES or f.suffix in TO_SUFFIXES:
        return FROM_TASHKENT
    if f.suffix in FROM_SUFFIXES or t.suffix in TO_SUFFIXES:
        return TO_TASHKENT
    # Rus predloglari: "iz Tashkenta", "v Kokand"
    if t.prev in ("iz", "s") or f.prev in ("v", "do", "vo"):
        return FROM_TASHKENT
    if f.prev in ("iz", "s") or t.prev in ("v", "do", "vo"):
        return TO_TASHKENT
    # Aks holda: birinchi aytilgan joy — jo'nash joyi
    return TO_TASHKENT if f.index < t.index else FROM_TASHKENT


def parse(raw: str) -> Lead | None:
    """Yo'lovchi e'loni bo'lsa Lead qaytaradi, aks holda None."""
    if not raw or len(raw) > 1000:
        return None
    text = normalize(raw)
    words = text.split()
    places = find_places(words)
    direction = _direction(places)
    if not direction:
        return None
    fergana_code = next(p.code for p in places if p.kind == "fergana")

    p_score = _score(text, PASSENGER_PATTERNS)
    d_score = _score(text, DRIVER_PATTERNS)
    if p_score <= d_score:
        return None  # haydovchining e'loni yoki noaniq

    seats = None
    m = SEATS_RE.search(text)
    if m:
        n = m.group(1)
        seats = int(n) if n.isdigit() else NUM_WORDS.get(n)
        if seats is not None and not 1 <= seats <= 7:
            seats = None

    day = None
    for offset in (2, 1, 0):  # "ertadan keyin" "ertaga"dan oldin tekshiriladi
        if any(re.search(rf"\b{w}\b", text) for w in DATE_WORDS[offset]):
            day = offset
            break
    slot = next((s for s, ws in SLOT_WORDS.items() if any(re.search(rf"\b{w}", text) for w in ws)), None)

    return Lead(
        direction=direction,
        fergana_code=fergana_code,
        tashkent_code=find_tashkent_district(words),
        day_offset=day,
        slot=slot,
        seats=seats,
        phones=extract_phones(raw),
        usernames=list(dict.fromkeys(USERNAME_RE.findall(raw))),
    )
