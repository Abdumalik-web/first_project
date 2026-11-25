"""Grafik naqshlarini aniqlash: indikatorlar, swing, struktura, FVG, OB, likvidlik, CRT, SMT, vaqt.

Barcha funksiyalar ustunlari open/high/low/close/volume va indeksi NY vaqtidagi
DatetimeIndex bo'lgan DataFrame bilan ishlaydi.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, time

import numpy as np
import pandas as pd


# ---------------------------------------------------------------- indikatorlar
def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def rsi(s: pd.Series, n: int = 14) -> pd.Series:
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    pc = df["close"].shift()
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def macd(s: pd.Series):
    line = ema(s, 12) - ema(s, 26)
    sig = ema(line, 9)
    return line, sig, line - sig


def indicators(df: pd.DataFrame) -> dict:
    c = df["close"]
    m, s, h = macd(c)
    bb_mid = c.rolling(20).mean()
    bb_std = c.rolling(20).std()
    width = (4 * bb_std / bb_mid).dropna()
    out = {
        "close": float(c.iloc[-1]),
        "ema50": float(ema(c, 50).iloc[-1]),
        "ema200": float(ema(c, 200).iloc[-1]) if len(c) >= 200 else None,
        "rsi14": round(float(rsi(c).iloc[-1]), 1),
        "macd": float(m.iloc[-1]), "macd_signal": float(s.iloc[-1]),
        "macd_hist": float(h.iloc[-1]), "macd_hist_prev": float(h.iloc[-2]),
        "atr14": float(atr(df).iloc[-1]),
        "bb_upper": float((bb_mid + 2 * bb_std).iloc[-1]),
        "bb_lower": float((bb_mid - 2 * bb_std).iloc[-1]),
        "bb_squeeze": bool(len(width) > 120 and width.iloc[-1] <= width.iloc[-120:].quantile(0.15)),
    }
    out["rsi_divergence"] = rsi_divergence(df)
    return out


def rsi_divergence(df: pd.DataFrame, lookback: int = 60) -> str | None:
    r = rsi(df["close"])
    hs, ls = swings(df.iloc[-lookback:], 3)
    if len(hs) >= 2 and hs[-1].price > hs[-2].price and r.loc[hs[-1].ts] < r.loc[hs[-2].ts]:
        return "bearish"
    if len(ls) >= 2 and ls[-1].price < ls[-2].price and r.loc[ls[-1].ts] > r.loc[ls[-2].ts]:
        return "bullish"
    return None


# ---------------------------------------------------------------- swing va struktura
@dataclass
class Swing:
    ts: pd.Timestamp
    i: int
    price: float
    kind: str  # "high" | "low"


def swings(df: pd.DataFrame, n: int = 2) -> tuple[list[Swing], list[Swing]]:
    """Fractal swinglar: chap va o'ngdagi n ta shamdan baland (past) bo'lgan nuqta."""
    h, l = df["high"].to_numpy(), df["low"].to_numpy()
    highs, lows = [], []
    for i in range(n, len(df) - n):
        win_h, win_l = h[i - n:i + n + 1], l[i - n:i + n + 1]
        if h[i] == win_h.max() and (win_h == h[i]).sum() == 1:
            highs.append(Swing(df.index[i], i, float(h[i]), "high"))
        if l[i] == win_l.min() and (win_l == l[i]).sum() == 1:
            lows.append(Swing(df.index[i], i, float(l[i]), "low"))
    return highs, lows


@dataclass
class StructureEvent:
    ts: pd.Timestamp
    i: int
    kind: str          # "BOS" | "CHoCH"
    direction: str     # "bullish" | "bearish"
    level: float       # buzilgan swing darajasi
    displacement: bool  # kuchli sham bilan bo'ldimi


def _is_displacement(df: pd.DataFrame, i: int, look: int = 20) -> bool:
    body = (df["close"] - df["open"]).abs()
    avg = body.iloc[max(0, i - look):i].mean()
    rng = df["high"].iloc[i] - df["low"].iloc[i]
    return bool(avg > 0 and body.iloc[i] >= 1.5 * avg and rng > 0 and body.iloc[i] / rng >= 0.6)


def structure(df: pd.DataFrame, n: int = 2) -> dict:
    """Sham tanasi yopilishi bo'yicha BOS va CHoCH (MSS) hodisalari."""
    highs, lows = swings(df, n)
    closes = df["close"].to_numpy()
    events: list[StructureEvent] = []
    trend = None
    hi_ptr = lo_ptr = 0
    last_high = last_low = None
    broken_high = broken_low = None
    for i in range(len(df)):
        # swing faqat n sham o'tgandan keyin tasdiqlanadi
        while hi_ptr < len(highs) and highs[hi_ptr].i + n <= i:
            last_high = highs[hi_ptr]
            hi_ptr += 1
        while lo_ptr < len(lows) and lows[lo_ptr].i + n <= i:
            last_low = lows[lo_ptr]
            lo_ptr += 1
        if last_high and last_high is not broken_high and closes[i] > last_high.price:
            kind = "BOS" if trend == "bullish" else "CHoCH"
            events.append(StructureEvent(df.index[i], i, kind, "bullish", last_high.price, _is_displacement(df, i)))
            trend, broken_high = "bullish", last_high
        if last_low and last_low is not broken_low and closes[i] < last_low.price:
            kind = "BOS" if trend == "bearish" else "CHoCH"
            events.append(StructureEvent(df.index[i], i, kind, "bearish", last_low.price, _is_displacement(df, i)))
            trend, broken_low = "bearish", last_low
    return {
        "trend": trend, "events": events, "highs": highs, "lows": lows,
        "last_high": last_high, "last_low": last_low,
    }


# ---------------------------------------------------------------- FVG va Order Block
@dataclass
class Zone:
    kind: str          # "FVG" | "OB"
    direction: str     # "bullish" | "bearish"
    top: float
    bottom: float
    ts: pd.Timestamp
    i: int
    mitigated: bool = False   # narx zonaga qaytganmi
    invalidated: bool = False  # tanasi bilan teshib o'tilganmi
    criteria: dict = field(default_factory=dict)

    @property
    def mid(self) -> float:
        return (self.top + self.bottom) / 2


def fvgs(df: pd.DataFrame, min_size: float = 0.0) -> list[Zone]:
    h, l, c = df["high"].to_numpy(), df["low"].to_numpy(), df["close"].to_numpy()
    out = []
    for i in range(2, len(df)):
        if l[i] > h[i - 2] and l[i] - h[i - 2] > min_size:
            z = Zone("FVG", "bullish", float(l[i]), float(h[i - 2]), df.index[i - 1], i - 1)
        elif h[i] < l[i - 2] and l[i - 2] - h[i] > min_size:
            z = Zone("FVG", "bearish", float(l[i - 2]), float(h[i]), df.index[i - 1], i - 1)
        else:
            continue
        after = slice(i + 1, len(df))
        if z.direction == "bullish":
            z.mitigated = bool((l[after] <= z.top).any())
            z.invalidated = bool((c[after] < z.bottom).any())
        else:
            z.mitigated = bool((h[after] >= z.bottom).any())
            z.invalidated = bool((c[after] > z.top).any())
        out.append(z)
    return out


def order_blocks(df: pd.DataFrame, st: dict, fvg_list: list[Zone]) -> list[Zone]:
    """Har bir struktura buzilishi uchun impulsdan oldingi oxirgi qarama-qarshi sham.

    SMC yaroqlilik mezonlari: likvidlik olgan, FVG qoldirgan, BOS/CHoCH'ga sabab bo'lgan,
    mitigatsiya qilinmagan. Zona mezoni models.py da narxga nisbatan baholanadi.
    """
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    out = []
    for ev in st["events"]:
        start = max(0, ev.i - 30)
        seg = slice(start, ev.i + 1)
        if ev.direction == "bullish":
            ext = start + int(np.argmin(l[seg]))
            cand = [k for k in range(max(start, ext - 5), ext + 1) if c[k] < o[k]]
        else:
            ext = start + int(np.argmax(h[seg]))
            cand = [k for k in range(max(start, ext - 5), ext + 1) if c[k] > o[k]]
        if not cand:
            continue
        k = cand[-1]
        z = Zone("OB", ev.direction, float(h[k]), float(l[k]), df.index[k], k)
        prior = slice(max(0, k - 20), k)
        after = slice(ev.i + 1, len(df))
        if ev.direction == "bullish":
            swept = bool(l[ext] < l[prior].min()) if k > 0 else False
            z.mitigated = bool((l[after] <= z.top).any())
            z.invalidated = bool((c[after] < z.bottom).any())
        else:
            swept = bool(h[ext] > h[prior].max()) if k > 0 else False
            z.mitigated = bool((h[after] >= z.bottom).any())
            z.invalidated = bool((c[after] > z.top).any())
        left_fvg = any(f.direction == ev.direction and k <= f.i <= ev.i for f in fvg_list)
        z.criteria = {
            "likvidlik_olgan": swept,
            "fvg_qoldirgan": left_fvg,
            "struktura_buzgan": True,
            "mitigatsiya_qilinmagan": not z.mitigated,
        }
        out.append(z)
    return out


# ---------------------------------------------------------------- likvidlik
def key_levels(d1: pd.DataFrame, intraday: pd.DataFrame, now: pd.Timestamp) -> dict:
    """PDH/PDL, PWH/PWL, Osiyo diapazoni, Midnight Open."""
    today = now.normalize()
    prev_days = d1[d1.index.normalize() < today]
    lv: dict = {}
    if len(prev_days):
        lv["PDH"], lv["PDL"] = float(prev_days["high"].iloc[-1]), float(prev_days["low"].iloc[-1])
    week_start = today - pd.Timedelta(days=today.weekday())
    prev_week = d1[(d1.index.normalize() < week_start) & (d1.index.normalize() >= week_start - pd.Timedelta(days=7))]
    if len(prev_week):
        lv["PWH"], lv["PWL"] = float(prev_week["high"].max()), float(prev_week["low"].min())
    asia = intraday[(intraday.index >= today - pd.Timedelta(hours=4)) & (intraday.index < today)]
    if len(asia):
        lv["ASIA_H"], lv["ASIA_L"] = float(asia["high"].max()), float(asia["low"].min())
    mo = intraday[intraday.index >= today]
    if len(mo):
        lv["MIDNIGHT_OPEN"] = float(mo["open"].iloc[0])
    return lv


def equal_levels(sw: list[Swing], tol: float) -> list[float]:
    """Bir-biriga tol masofada bo'lgan swinglar: EQH / EQL."""
    out = []
    for a in range(len(sw)):
        for b in range(a + 1, len(sw)):
            if abs(sw[a].price - sw[b].price) <= tol:
                out.append(round((sw[a].price + sw[b].price) / 2, 6))
    return sorted(set(out))


def sweeps(df: pd.DataFrame, levels: dict[str, float], since: pd.Timestamp) -> list[dict]:
    """since dan keyin soya bilan o'tilgan, lekin tanasi qaytib yopilgan darajalar."""
    seg = df[df.index >= since]
    out = []
    for name, lvl in levels.items():
        if lvl is None or name == "MIDNIGHT_OPEN":
            continue
        above = seg[seg["high"] > lvl]
        below = seg[seg["low"] < lvl]
        if len(above) and (above["close"] <= lvl).any() and seg["close"].iloc[-1] < lvl:
            out.append({"level": name, "price": lvl, "side": "BSL", "ts": str(above.index[0])})
        if len(below) and (below["close"] >= lvl).any() and seg["close"].iloc[-1] > lvl:
            out.append({"level": name, "price": lvl, "side": "SSL", "ts": str(below.index[0])})
    return out


def dealing_range(df: pd.DataFrame, n: int = 3) -> dict | None:
    """Oxirgi muhim swing high va low orasidagi diapazon: premium / discount."""
    hs, ls = swings(df, n)
    if not hs or not ls:
        return None
    hi, lo = hs[-1].price, ls[-1].price
    if hi <= lo:
        return None
    price = float(df["close"].iloc[-1])
    pos = (price - lo) / (hi - lo)
    return {
        "high": hi, "low": lo, "eq": (hi + lo) / 2, "position_pct": round(pos * 100, 1),
        "zone": "premium" if pos > 0.5 else "discount",
        "ote_bull": (hi - 0.79 * (hi - lo), hi - 0.62 * (hi - lo)),
        "ote_bear": (lo + 0.62 * (hi - lo), lo + 0.79 * (hi - lo)),
    }


# ---------------------------------------------------------------- CRT
def crt(df: pd.DataFrame) -> dict | None:
    """Oxirgi ikki yopilgan sham (1-sham diapazon, 2-sham manipulation) va hozirgi sham."""
    if len(df) < 3:
        return None
    c1, c2, cur = df.iloc[-3], df.iloc[-2], df.iloc[-1]
    hi, lo = float(c1["high"]), float(c1["low"])
    body_hi, body_lo = max(c2["open"], c2["close"]), min(c2["open"], c2["close"])
    inside_close = lo <= c2["close"] <= hi
    swept_hi, swept_lo = c2["high"] > hi, c2["low"] < lo
    res = {"range_high": hi, "range_low": lo, "eq": (hi + lo) / 2,
           "range_ts": str(df.index[-3]), "c2_ts": str(df.index[-2]), "valid": False, "direction": None}
    if swept_hi and swept_lo:
        res["note"] = "outside bar: ikkala tomon sweep qilindi, signal noaniq"
    elif (swept_lo or swept_hi) and inside_close and lo <= body_lo and body_hi <= hi:
        res.update(valid=True, direction="bullish" if swept_lo else "bearish",
                   sweep_extreme=float(c2["low"] if swept_lo else c2["high"]))
        res["target"] = hi if swept_lo else lo
        res["progress"] = "hozirgi sham EQ dan o'tdi" if (
            (swept_lo and cur["high"] >= res["eq"]) or (swept_hi and cur["low"] <= res["eq"])) else "hali EQ ga yetmadi"
    elif not swept_hi and not swept_lo:
        res["note"] = "inside bar: CRT hali shakllanmagan"
    else:
        res["note"] = "2-sham tanasi diapazondan tashqarida yopildi: breakout, CRT emas"
    # hozir shakllanayotgan CRT (cur 2-sham sifatida)
    h2, l2 = float(c2["high"]), float(c2["low"])
    if cur["low"] < l2 and l2 <= cur["close"] <= h2:
        res["forming"] = {"direction": "bullish", "range_high": h2, "range_low": l2, "sweep_extreme": float(cur["low"])}
    elif cur["high"] > h2 and l2 <= cur["close"] <= h2:
        res["forming"] = {"direction": "bearish", "range_high": h2, "range_low": l2, "sweep_extreme": float(cur["high"])}
    return res


# ---------------------------------------------------------------- SMT
def smt(a: pd.DataFrame, b: pd.DataFrame, inverse: bool, recent: int = 16, ref: int = 64) -> dict:
    """Oxirgi `recent` shamda A va B oldingi `ref` sham ekstremumini yangiladimi?"""
    j = a.index.intersection(b.index)
    a, b = a.loc[j], b.loc[j]
    if len(j) < recent + ref:
        return {"signal": None, "note": "ma'lumot yetarli emas"}
    ra, rb = a.iloc[-(recent + ref):-recent], b.iloc[-(recent + ref):-recent]
    na, nb = a.iloc[-recent:], b.iloc[-recent:]
    a_ll, a_hh = na["low"].min() < ra["low"].min(), na["high"].max() > ra["high"].max()
    if inverse:  # A ning low'i B ning high'iga mos keladi
        b_ll, b_hh = nb["high"].max() > rb["high"].max(), nb["low"].min() < rb["low"].min()
    else:
        b_ll, b_hh = nb["low"].min() < rb["low"].min(), nb["high"].max() > rb["high"].max()
    sig = None
    if a_ll != b_ll:
        sig = "bullish"
    elif a_hh != b_hh:
        sig = "bearish"
    return {"signal": sig, "a_new_low": bool(a_ll), "b_new_low_equiv": bool(b_ll),
            "a_new_high": bool(a_hh), "b_new_high_equiv": bool(b_hh)}


# ---------------------------------------------------------------- vaqt
KILLZONES = [("London Killzone", time(2), time(5)), ("NY AM Killzone", time(7), time(10)),
             ("London Close", time(10), time(12))]
SILVER_BULLETS = [("London SB", time(3), time(4)), ("NY AM SB", time(10), time(11)),
                  ("NY PM SB", time(14), time(15))]


def session_info(now: datetime) -> dict:
    t = now.time()
    kz = next((n for n, a, b in KILLZONES if a <= t < b), None)
    sb = next((n for n, a, b in SILVER_BULLETS if a <= t < b), None)
    closed = now.weekday() == 5 or (now.weekday() == 4 and t >= time(17)) or (now.weekday() == 6 and t < time(17))
    return {"ny_time": now.strftime("%Y-%m-%d %H:%M %Z"), "killzone": kz, "silver_bullet": sb,
            "market_closed": closed, "weekday": now.strftime("%A")}


def to_jsonable(o):
    if isinstance(o, (Swing, StructureEvent, Zone)):
        return to_jsonable(asdict(o))
    if isinstance(o, dict):
        return {k: to_jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [to_jsonable(v) for v in o]
    if isinstance(o, (pd.Timestamp, datetime)):
        return str(o)
    if isinstance(o, (np.floating, float)):
        return round(float(o), 6)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o
