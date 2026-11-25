"""Narx ma'lumotlarini yuklash: Yahoo Finance (real vaqtga yaqin) yoki lokal CSV."""
from __future__ import annotations

import pandas as pd

from .config import NY_TZ, PRICES_DIR, TIMEFRAMES, YAHOO_TICKERS

COLS = ["open", "high", "low", "close", "volume"]


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=str.lower)
    for c in COLS:
        if c not in df.columns:
            df[c] = 0.0
    df = df[COLS].dropna(subset=["open", "high", "low", "close"])
    idx = pd.DatetimeIndex(df.index)
    idx = idx.tz_localize("UTC") if idx.tz is None else idx
    df.index = idx.tz_convert(NY_TZ)
    return df.sort_index()


def load_csv(symbol: str, tf: str) -> pd.DataFrame | None:
    path = PRICES_DIR / f"{symbol.upper()}_{tf}.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path, parse_dates=["date"], index_col="date")
    return _normalize(df)


def load_yahoo(symbol: str, tf: str) -> pd.DataFrame | None:
    import yfinance as yf

    ticker = YAHOO_TICKERS.get(symbol.upper(), symbol)
    p = TIMEFRAMES[tf]
    df = yf.download(ticker, period=p["period"], interval=p["interval"],
                     progress=False, auto_adjust=False)
    if df is None or df.empty:
        return None
    return _normalize(df)


def resample(df: pd.DataFrame, rule: str, offset: str | None = None) -> pd.DataFrame:
    """4H shamlar NY vaqti bo'yicha 18:00, 22:00, 02:00, ... da ochiladi (offset='2h')."""
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    # NY "devor soati" bo'yicha bo'lamiz, aks holda yozgi/qishki vaqt almashganda shamlar 1 soat siljiydi
    local = df.copy()
    local.index = local.index.tz_localize(None)
    out = local.resample(rule, origin="epoch", offset=offset).agg(agg).dropna(subset=["open"])
    out.index = out.index.tz_localize(NY_TZ, ambiguous="NaT", nonexistent="shift_forward")
    return out[out.index.notna()]


def load_all(symbol: str, source: str = "auto") -> dict[str, pd.DataFrame]:
    """1d, 4h, 1h, 15m, 5m ma'lumotlarini qaytaradi."""
    frames: dict[str, pd.DataFrame] = {}
    for tf in TIMEFRAMES:
        df = None
        if source in ("auto", "csv"):
            df = load_csv(symbol, tf)
        if df is None and source in ("auto", "yahoo"):
            try:
                df = load_yahoo(symbol, tf)
            except Exception as e:  # tarmoq xatosi va h.k.
                print(f"[ogohlantirish] {symbol} {tf} yuklanmadi: {e}")
        if df is not None and not df.empty:
            frames[tf] = df
    if "1h" in frames:
        frames["4h"] = resample(frames["1h"], "4h", offset="2h")
    return frames
