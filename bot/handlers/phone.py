import re


def normalize_phone(raw: str | None) -> str | None:
    """Telefon raqamni +998XXXXXXXXX ko'rinishiga keltiradi. Noto'g'ri bo'lsa None."""
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 9:
        digits = "998" + digits
    if len(digits) < 10 or len(digits) > 15:
        return None
    return "+" + digits
