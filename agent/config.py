"""Agent sozlamalari."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRAIN = ROOT / "second_brain"
REPORTS_DIR = BRAIN / "05_tahlillar"
SCAN_JSON_DIR = REPORTS_DIR / "_json"
JOURNAL_DIR = BRAIN / "06_jurnal"
NOTES_DIR = BRAIN / "07_qaydlar"
SUMMARY_DIR = BRAIN / "08_hisobotlar"
PRICES_DIR = BRAIN / "02_malumotlar" / "narxlar"

MODEL = "claude-opus-5-5"
EFFORT = "high"
WEB_SEARCH_MAX_USES = 8

NY_TZ = "America/New_York"

# Foydalanuvchi yozadigan nom -> Yahoo Finance tikeri
YAHOO_TICKERS = {
    "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "AUDUSD": "AUDUSD=X",
    "NZDUSD": "NZDUSD=X", "USDJPY": "JPY=X", "USDCHF": "CHF=X",
    "USDCAD": "CAD=X", "EURJPY": "EURJPY=X", "GBPJPY": "GBPJPY=X",
    "EURGBP": "EURGBP=X", "XAUUSD": "GC=F", "XAGUSD": "SI=F",
    "DXY": "DX-Y.NYB",
}

# SMT uchun korrelyatsion juftlik: (juftlik, teskari korrelyatsiyami)
SMT_PAIRS = {
    "EURUSD": ("GBPUSD", False), "GBPUSD": ("EURUSD", False),
    "AUDUSD": ("NZDUSD", False), "NZDUSD": ("AUDUSD", False),
    "USDCHF": ("EURUSD", True), "USDJPY": ("DXY", False),
    "USDCAD": ("DXY", False), "XAUUSD": ("XAGUSD", False),
    "XAGUSD": ("XAUUSD", False), "EURJPY": ("GBPJPY", False),
    "GBPJPY": ("EURJPY", False), "EURGBP": ("DXY", True),
}

# Har bir timeframe uchun Yahoo yuklash parametrlari
TIMEFRAMES = {
    "1d": {"interval": "1d", "period": "2y"},
    "1h": {"interval": "1h", "period": "60d"},
    "15m": {"interval": "15m", "period": "20d"},
    "5m": {"interval": "5m", "period": "5d"},
}


def pip_size(symbol: str) -> float:
    s = symbol.upper()
    if "JPY" in s:
        return 0.01
    if s.startswith("XAU"):
        return 0.1
    if s.startswith("XAG"):
        return 0.01
    if s == "DXY":
        return 0.01
    return 0.0001
