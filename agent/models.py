"""Har bir savdo modelini (Klassik TA, ICT, SMC, CRT, Silver Bullet) grafikka qo'yib baholash.

Har bir model 2-chi miyadagi checklistga mos tekshiruvlar ro'yxatini qaytaradi:
ok=True (bajarildi), ok=False (bajarilmadi), ok=None (avtomatik tekshirib bo'lmaydi,
masalan yangiliklar; uni Claude fundamental qismda tekshiradi).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime

import pandas as pd

from . import detectors as D
from .config import SMT_PAIRS, pip_size


@dataclass
class Check:
    name: str
    ok: bool | None
    detail: str = ""


@dataclass
class ModelResult:
    model: str
    direction: str | None
    checks: list[Check] = field(default_factory=list)
    plan: dict | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for c in self.checks if c.ok is True)

    @property
    def evaluated(self) -> int:
        return sum(1 for c in self.checks if c.ok is not None)

    @property
    def score(self) -> float:
        return round(self.passed / self.evaluated, 3) if self.evaluated else 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d.update(passed=self.passed, evaluated=self.evaluated, score=self.score)
        return D.to_jsonable(d)


# ---------------------------------------------------------------- umumiy kontekst
def build_context(symbol: str, frames: dict[str, pd.DataFrame],
                  corr_frames: dict[str, pd.DataFrame] | None, now: datetime) -> dict:
    d1, h4, h1, m15 = frames["1d"], frames["4h"], frames["1h"], frames["15m"]
    m5 = frames.get("5m", m15)
    now_ts = pd.Timestamp(now)
    st = {tf: D.structure(df) for tf, df in (("1d", d1), ("4h", h4), ("1h", h1), ("15m", m15), ("5m", m5))}

    d1_trend, h4_trend = st["1d"]["trend"], st["4h"]["trend"]
    direction = h4_trend or d1_trend
    price = float(m5["close"].iloc[-1])
    atr15 = float(D.atr(m15).iloc[-1])

    levels = D.key_levels(d1, m15, now_ts)
    hs1, ls1 = st["1h"]["highs"], st["1h"]["lows"]
    eqh = D.equal_levels(hs1[-12:], 0.15 * atr15 * 4)
    eql = D.equal_levels(ls1[-12:], 0.15 * atr15 * 4)
    today = now_ts.normalize()
    sweeps = D.sweeps(m5, levels, today - pd.Timedelta(hours=4))

    # Draw on Liquidity: nomli darajalar ustuvor, 1H swinglar zaxira sifatida; juda yaqinlari tashlanadi
    min_dist = 1.5 * atr15
    named = [(v, k) for k, v in levels.items() if k != "MIDNIGHT_OPEN"]
    named += [(x, "EQH") for x in eqh] + [(x, "EQL") for x in eql]
    minor = [(s.price, "1H swing high") for s in hs1[-20:]] + [(s.price, "1H swing low") for s in ls1[-20:]]

    def pick(cands, up):
        far = [(p, n) for p, n in cands if (p - price if up else price - p) >= min_dist]
        return sorted(far, key=lambda x: abs(x[0] - price))

    above = pick(named, True) + pick(minor, True)
    below = pick(named, False) + pick(minor, False)

    fvg = {tf: D.fvgs(df) for tf, df in (("4h", h4), ("1h", h1), ("15m", m15), ("5m", m5))}
    obs = {tf: D.order_blocks(df, st[tf], fvg[tf]) for tf, df in (("4h", h4), ("1h", h1), ("15m", m15))}

    smt_res = None
    pair = SMT_PAIRS.get(symbol.upper())
    if pair and corr_frames and "15m" in corr_frames:
        smt_res = D.smt(m15, corr_frames["15m"], pair[1])
        smt_res["pair"] = pair[0]
        smt_res["inverse"] = pair[1]

    return {
        "symbol": symbol.upper(), "pip": pip_size(symbol), "now": now_ts, "price": price,
        "frames": {"1d": d1, "4h": h4, "1h": h1, "15m": m15, "5m": m5},
        "structure": st, "d1_trend": d1_trend, "h4_trend": h4_trend, "direction": direction,
        "levels": levels, "eqh": eqh, "eql": eql, "sweeps": sweeps,
        "dol_above": above[:5], "dol_below": below[:5],
        "dealing_range": D.dealing_range(h1),
        "fvg": fvg, "ob": obs, "smt": smt_res,
        "crt": {"1d": D.crt(d1), "4h": D.crt(h4)},
        "session": D.session_info(now),
        "ind": {"1d": D.indicators(d1), "4h": D.indicators(h4), "1h": D.indicators(h1)},
        "atr15": atr15,
    }


# ---------------------------------------------------------------- yordamchilar
def _dol(ctx, direction):
    lst = ctx["dol_above"] if direction == "bullish" else ctx["dol_below"]
    return lst[0][0] if lst else None


def _plan(ctx, direction, entry, sl, tp, why) -> dict | None:
    if None in (direction, entry, sl, tp):
        return None
    risk = (entry - sl) if direction == "bullish" else (sl - entry)
    reward = (tp - entry) if direction == "bullish" else (entry - tp)
    if risk <= 0 or reward <= 0:
        return None
    pip = ctx["pip"]
    return {"direction": direction, "entry": round(entry, 6), "stop_loss": round(sl, 6),
            "take_profit": round(tp, 6), "risk_pips": round(risk / pip, 1),
            "reward_pips": round(reward / pip, 1), "rr": round(reward / risk, 2), "logic": why}


def _rr_check(plan) -> Check:
    if not plan:
        return Check("R:R ≥ 1:2", False, "savdo rejasini tuzib bo'lmadi (kirish, stop yoki maqsad yo'q)")
    return Check("R:R ≥ 1:2", plan["rr"] >= 2, f"R:R = 1:{plan['rr']}")


def _recent_event(ctx, tf, direction, bars, need_disp=False, kinds=("BOS", "CHoCH")):
    df = ctx["frames"][tf]
    cutoff = len(df) - bars
    evs = [e for e in ctx["structure"][tf]["events"]
           if e.i >= cutoff and e.direction == direction and e.kind in kinds and (e.displacement or not need_disp)]
    return evs[-1] if evs else None


def _fresh_fvg(ctx, tf, direction, bars, after_i=None):
    df = ctx["frames"][tf]
    cutoff = len(df) - bars if after_i is None else after_i
    zs = [z for z in ctx["fvg"][tf] if z.direction == direction and z.i >= cutoff and not z.invalidated]
    return zs[-1] if zs else None


def _sweep_check(ctx, direction) -> tuple[Check, dict | None]:
    side = "SSL" if direction == "bullish" else "BSL"
    sw = [s for s in ctx["sweeps"] if s["side"] == side]
    if sw:
        return Check("Likvidlik sweep", True, f"{sw[-1]['level']} ({sw[-1]['price']:.5f}) sweep qilindi, {sw[-1]['ts']}"), sw[-1]
    return Check("Likvidlik sweep", False, f"bugun {side} sweep aniqlanmadi"), None


def _smt_check(ctx, direction) -> Check:
    s = ctx["smt"]
    if not s or s.get("signal") is None and s.get("note"):
        return Check("SMT tasdig'i", None, (s or {}).get("note", "korrelyatsion juftlik ma'lumoti yo'q"))
    ok = s["signal"] == direction
    return Check("SMT tasdig'i", ok, f"{s['pair']} bilan SMT: {s['signal'] or 'yo`q'}")


def _ltf_extreme(ctx, direction, bars=48):
    m5 = ctx["frames"]["5m"].iloc[-bars:]
    return float(m5["low"].min()) if direction == "bullish" else float(m5["high"].max())


def _bias_check(ctx, direction) -> Check:
    d1, h4 = ctx["d1_trend"], ctx["h4_trend"]
    return Check("HTF bias aniq (Daily va 4H bir xil)", bool(d1 and d1 == h4 == direction),
                 f"Daily: {d1}, 4H: {h4}")


def _zone_check(ctx, direction, price=None) -> Check:
    dr = ctx["dealing_range"]
    if not dr:
        return Check("To'g'ri zona (premium/discount)", None, "dealing range aniqlanmadi")
    p = price if price is not None else ctx["price"]
    zone = "premium" if p > dr["eq"] else "discount"
    want = "discount" if direction == "bullish" else "premium"
    return Check("To'g'ri zona (premium/discount)", zone == want,
                 f"narx {zone} zonada ({dr['position_pct']}%), kerak: {want}")


# ---------------------------------------------------------------- modellar
def classic_ta(ctx) -> ModelResult:
    i1, i4 = ctx["ind"]["1d"], ctx["ind"]["4h"]
    c = i1["close"]
    if i1["ema200"] and c > i1["ema50"] > i1["ema200"]:
        direction = "bullish"
    elif i1["ema200"] and c < i1["ema50"] < i1["ema200"]:
        direction = "bearish"
    else:
        direction = "bullish" if c > i1["ema50"] else "bearish"
    r = ModelResult("Klassik texnik tahlil", direction)
    bull = direction == "bullish"
    r.checks.append(Check("Daily trend aniq (narx, EMA50, EMA200 tartibi)",
                          bool(i1["ema200"]) and ((c > i1["ema50"] > i1["ema200"]) or (c < i1["ema50"] < i1["ema200"])),
                          f"close {c:.5f}, EMA50 {i1['ema50']:.5f}, EMA200 {i1['ema200'] or 0:.5f}"))
    r.checks.append(Check("4H trend Daily bilan mos", (i4["close"] > i4["ema50"]) == bull,
                          f"4H close {i4['close']:.5f}, EMA50 {i4['ema50']:.5f}"))
    rsi_ok = (i4["rsi14"] < 70 if bull else i4["rsi14"] > 30) or i4["rsi_divergence"] == direction
    r.checks.append(Check("RSI haddan oshmagan yoki divergensiya mos", rsi_ok,
                          f"4H RSI {i4['rsi14']}, divergensiya: {i4['rsi_divergence']}"))
    macd_ok = (i4["macd_hist"] > 0) == bull and abs(i4["macd_hist"]) >= abs(i4["macd_hist_prev"])
    r.checks.append(Check("MACD momentum mos va kuchaymoqda", macd_ok,
                          f"hist {i4['macd_hist']:.6f} (oldingi {i4['macd_hist_prev']:.6f})"))
    sw = ctx["structure"]["1d"]["lows" if bull else "highs"]
    sr = sw[-1].price if sw else None
    near = sr is not None and abs(c - sr) <= 1.0 * i1["atr14"]
    r.checks.append(Check("Narx support/resistance yaqinida", near,
                          f"eng yaqin daily {'support' if bull else 'resistance'}: {sr}"))
    r.checks.append(Check("Hajm tasdig'i", None, "forex uchun markazlashgan hajm yo'q"))
    atr4 = i4["atr14"]
    entry = ctx["price"]
    sl = entry - 1.5 * atr4 if bull else entry + 1.5 * atr4
    tgt = [s.price for s in ctx["structure"]["1d"]["highs" if bull else "lows"][-10:]
           if (s.price > entry if bull else s.price < entry)]
    tp = (min(tgt) if bull else max(tgt)) if tgt else None
    r.plan = _plan(ctx, direction, entry, sl, tp, "bozor narxida kirish, stop 1.5×ATR(4H), maqsad keyingi daily swing")
    r.checks.append(_rr_check(r.plan))
    return r


def ict(ctx) -> ModelResult:
    direction = ctx["direction"]
    r = ModelResult("ICT", direction)
    if not direction:
        r.notes.append("struktura yo'nalishi aniqlanmadi")
        return r
    s = ctx["session"]
    r.checks.append(_bias_check(ctx, direction))
    r.checks.append(_zone_check(ctx, direction))
    r.checks.append(Check("Killzone yoki Silver Bullet vaqti", bool(s["killzone"] or s["silver_bullet"]),
                          f"hozir {s['ny_time']}: {s['killzone'] or s['silver_bullet'] or 'killzone emas'}"))
    sc, sw = _sweep_check(ctx, direction)
    r.checks.append(sc)
    r.checks.append(_smt_check(ctx, direction))
    ev = _recent_event(ctx, "5m", direction, 48, need_disp=True)
    r.checks.append(Check("MSS displacement bilan (5m)", ev is not None,
                          f"{ev.kind} {ev.level:.5f} da, {ev.ts}" if ev else "so'nggi 4 soatda displacement'li MSS yo'q"))
    fvg = _fresh_fvg(ctx, "5m", direction, 48, after_i=(ev.i - 3) if ev else None)
    r.checks.append(Check("Kirish uchun FVG", fvg is not None,
                          f"FVG {fvg.bottom:.5f}–{fvg.top:.5f} ({fvg.ts})" if fvg else "yangi FVG yo'q"))
    r.checks.append(Check("Yaqin 30 daqiqada yuqori ta'sirli yangilik yo'q", None, "Claude iqtisodiy kalendarni tekshiradi"))
    if fvg:
        sl = sw["price"] if sw else _ltf_extreme(ctx, direction)
        sl = min(sl, _ltf_extreme(ctx, direction)) if direction == "bullish" else max(sl, _ltf_extreme(ctx, direction))
        r.plan = _plan(ctx, direction, fvg.mid, sl, _dol(ctx, direction),
                       "kirish FVG CE (50%) da, stop sweep ekstremumi ortida, maqsad keyingi likvidlik (DOL)")
    r.checks.append(_rr_check(r.plan))
    return r


def smc(ctx) -> ModelResult:
    direction = ctx["direction"]
    r = ModelResult("SMC", direction)
    if not direction:
        return r
    bull = direction == "bullish"
    r.checks.append(Check("HTF tashqi trend aniq", ctx["h4_trend"] == direction and ctx["d1_trend"] == direction,
                          f"Daily: {ctx['d1_trend']}, 4H: {ctx['h4_trend']}"))
    price = ctx["price"]
    cands = [z for tf in ("1h", "15m") for z in ctx["ob"][tf]
             if z.direction == direction and not z.invalidated and ((z.top < price) if bull else (z.bottom > price))]
    dr = ctx["dealing_range"]
    for z in cands:
        z.criteria["togri_zonada"] = bool(dr) and ((z.mid < dr["eq"]) if bull else (z.mid > dr["eq"]))
    best = max(cands, key=lambda z: (sum(z.criteria.values()), z.i), default=None)
    if best:
        n_ok = sum(best.criteria.values())
        r.checks.append(Check("POI to'g'ri zonada", best.criteria["togri_zonada"], f"OB {best.bottom:.5f}–{best.top:.5f}"))
        r.checks.append(Check("OB kamida 4/5 yaroqlilik mezoniga javob beradi", n_ok >= 4,
                              f"{n_ok}/5: " + ", ".join(k for k, v in best.criteria.items() if v)))
        m15 = ctx["frames"]["15m"]
        after = m15[m15.index > best.ts]
        hs, ls = D.swings(after, 2) if len(after) > 6 else ([], [])
        if bull:
            idm = [s for s in ls if s.price > best.top]
            taken = any((after["low"].iloc[s.i + 1:] < s.price).any() for s in idm)
        else:
            idm = [s for s in hs if s.price < best.bottom]
            taken = any((after["high"].iloc[s.i + 1:] > s.price).any() for s in idm)
        r.checks.append(Check("Inducement (IDM) olingan", bool(idm) and taken,
                              "OB'dan keyingi ichki swing likvidligi olingan" if taken else "IDM hali olinmagan"))
    else:
        r.checks.append(Check("POI to'g'ri zonada", False, "narx yo'nalishida yaroqli OB topilmadi"))
        r.checks.append(Check("OB kamida 4/5 yaroqlilik mezoniga javob beradi", False, "OB yo'q"))
        r.checks.append(Check("Inducement (IDM) olingan", False, "OB yo'q"))
    r.checks.append(_sweep_check(ctx, direction)[0])
    ev = _recent_event(ctx, "5m", direction, 48, kinds=("CHoCH",))
    r.checks.append(Check("LTF CHoCH (tana bilan yopilgan)", ev is not None,
                          f"CHoCH {ev.level:.5f} da, {ev.ts}" if ev else "so'nggi 4 soatda LTF CHoCH yo'q"))
    fvg = _fresh_fvg(ctx, "15m", direction, 32) or _fresh_fvg(ctx, "5m", direction, 48)
    r.checks.append(Check("Imbalance (FVG) mavjud", fvg is not None,
                          f"FVG {fvg.bottom:.5f}–{fvg.top:.5f}" if fvg else "yo'q"))
    r.checks.append(_smt_check(ctx, direction))
    if best:
        buf = 0.1 * ctx["atr15"]
        entry = best.top if bull else best.bottom
        sl = best.bottom - buf if bull else best.top + buf
        r.plan = _plan(ctx, direction, entry, sl, _dol(ctx, direction),
                       "limit kirish OB chetida (confirmation uchun ichida LTF CHoCH kuting), stop OB ortida")
    r.checks.append(_rr_check(r.plan))
    return r


def crt_model(ctx) -> ModelResult:
    pick, tf = None, None
    for t in ("4h", "1d"):
        c = ctx["crt"][t]
        if c and c.get("valid") and (pick is None or c["direction"] == ctx["direction"]):
            pick, tf = c, t
    if not pick:
        for t in ("4h", "1d"):
            c = ctx["crt"][t]
            if c and c.get("forming"):
                pick, tf = {**c["forming"], "valid": False, "forming_only": True,
                            "eq": (c["forming"]["range_high"] + c["forming"]["range_low"]) / 2}, t
                break
    direction = pick["direction"] if pick else ctx["direction"]
    r = ModelResult("CRT", direction)
    if not pick:
        r.checks.append(Check("CRT setup (sweep + diapazon ichida yopilish)", False,
                              f"4H: {(ctx['crt']['4h'] or {}).get('note')}; Daily: {(ctx['crt']['1d'] or {}).get('note')}"))
        r.checks.append(_rr_check(None))
        return r
    r.notes.append(f"CRT timeframe: {tf}" + (" (hozir shakllanmoqda, sham hali yopilmagan)" if pick.get("forming_only") else ""))
    r.checks.append(Check("HTF bias CRT yo'nalishiga mos", ctx["direction"] == direction,
                          f"CRT: {direction}, bias: {ctx['direction']}"))
    r.checks.append(Check("2-sham sweep qildi va tanasi diapazon ichida yopildi", bool(pick.get("valid")),
                          f"diapazon {pick['range_low']:.5f}–{pick['range_high']:.5f}"))
    ext = pick["sweep_extreme"]
    lv = ctx["levels"]
    kl_names = ("PDL", "PWL") if direction == "bullish" else ("PDH", "PWH")
    at_kl = any(n in lv and ((ext < lv[n]) if direction == "bullish" else (ext > lv[n])) for n in kl_names)
    htf_zones = [z for z in ctx["fvg"]["4h"] + ctx["ob"]["4h"] if z.direction == direction and not z.invalidated]
    at_kl = at_kl or any(z.bottom <= ext <= z.top for z in htf_zones)
    r.checks.append(Check("Sweep muhim darajada (KL / PD array)", at_kl, f"sweep ekstremumi {ext:.5f}"))
    s = ctx["session"]
    c2_hour = pd.Timestamp(pick.get("c2_ts", ctx["now"])).hour if tf == "4h" else None
    kz = bool(s["killzone"]) or (c2_hour in (2, 6))
    r.checks.append(Check("Sweep killzone vaqtida", kz, f"hozir: {s['killzone'] or '-'}; 4H 2-sham ochilishi: {c2_hour}"))
    ev = _recent_event(ctx, "5m", direction, 60)
    r.checks.append(Check("LTF MSS/CHoCH (Turtle Soup)", ev is not None, f"{ev.kind} {ev.ts}" if ev else "yo'q"))
    fvg = _fresh_fvg(ctx, "5m", direction, 60)
    r.checks.append(Check("Kirish uchun FVG yoki OB", fvg is not None,
                          f"FVG {fvg.bottom:.5f}–{fvg.top:.5f}" if fvg else "yo'q"))
    r.checks.append(_smt_check(ctx, direction))
    r.checks.append(Check("Yaqin 30 daqiqada yuqori ta'sirli yangilik yo'q", None, "Claude tekshiradi"))
    entry = fvg.mid if fvg else ctx["price"]
    tp = pick["range_high"] if direction == "bullish" else pick["range_low"]
    r.plan = _plan(ctx, direction, entry, ext, tp, f"TP1 CRT 50% ({pick['eq']:.5f}), TP2 qarama-qarshi CRT tomoni")
    r.checks.append(_rr_check(r.plan))
    return r


def silver_bullet(ctx) -> ModelResult:
    direction = ctx["direction"]
    r = ModelResult("Silver Bullet", direction)
    s = ctx["session"]
    now = ctx["now"]
    win = next(((n, a, b) for n, a, b in D.SILVER_BULLETS if a <= now.time() < b), None)
    r.checks.append(_bias_check(ctx, direction))
    r.checks.append(Check("Hozir Silver Bullet oynasi", win is not None,
                          s["silver_bullet"] or "oynadan tashqarida. Oynalar NY 03-04, 10-11, 14-15 (Toshkent qishda +10 soat)"))
    if not win or not direction:
        r.notes.append("Model faqat oyna ichida ishlaydi. Keyingi oynani kuting.")
        r.checks.append(_rr_check(None))
        return r
    start = now.normalize() + pd.Timedelta(hours=win[1].hour)
    m5 = ctx["frames"]["5m"]
    side = "SSL" if direction == "bullish" else "BSL"
    pre = [x for x in ctx["sweeps"] if x["side"] == side and pd.Timestamp(x["ts"]) >= start - pd.Timedelta(hours=1)]
    r.checks.append(Check("Oynadan oldin yoki boshida qarama-qarshi likvidlik sweep", bool(pre),
                          pre[-1]["level"] if pre else "yo'q"))
    in_win = m5.index >= start
    first_i = int(in_win.argmax()) if in_win.any() else len(m5)
    evs = [e for e in ctx["structure"]["5m"]["events"] if e.i >= first_i and e.direction == direction and e.displacement]
    r.checks.append(Check("Oyna ichida displacement va MSS", bool(evs), f"{evs[-1].kind} {evs[-1].ts}" if evs else "yo'q"))
    fv = [z for z in ctx["fvg"]["5m"] if z.i >= first_i and z.direction == direction and not z.invalidated]
    r.checks.append(Check("FVG oyna ichida hosil bo'ldi", bool(fv), f"{fv[-1].bottom:.5f}–{fv[-1].top:.5f}" if fv else "yo'q"))
    tp = _dol(ctx, direction)
    dist = abs(tp - ctx["price"]) / ctx["pip"] if tp else 0
    r.checks.append(Check("Maqsadgacha ≥ 10 pips joy bor", dist >= 10, f"{dist:.1f} pips"))
    r.checks.append(Check("Oyna ichida yuqori ta'sirli yangilik yo'q", None, "Claude tekshiradi"))
    if fv:
        sl = _ltf_extreme(ctx, direction, 24)
        r.plan = _plan(ctx, direction, fv[-1].mid, sl, tp, "oyna ichidagi FVG CE da kirish, maqsad DOL")
    r.checks.append(_rr_check(r.plan))
    return r


ALL_MODELS = [classic_ta, ict, smc, crt_model, silver_bullet]


def run_all(ctx) -> dict:
    results = [m(ctx) for m in ALL_MODELS]
    ranked = sorted(results, key=lambda r: (r.score, r.passed, (r.plan or {}).get("rr", 0)), reverse=True)
    best = ranked[0]
    verdict = best.model if best.score >= 0.6 and best.plan and best.plan["rr"] >= 2 else None
    return {
        "ranking": [r.to_dict() for r in ranked],
        "recommended_model": verdict,
        "recommendation_note": (f"{best.model} eng yuqori ball oldi ({best.passed}/{best.evaluated})"
                                if verdict else
                                "Hech bir model hozir to'liq setup bermayapti (ball < 60% yoki R:R < 2). Kutish tavsiya etiladi."),
    }


def context_summary(ctx) -> dict:
    """Claude uchun ixcham kontekst: xom DataFrame'larsiz."""
    def last_events(tf, k=4):
        return [D.to_jsonable(e) for e in ctx["structure"][tf]["events"][-k:]]

    def zones(lst, k=4):
        return [D.to_jsonable(z) for z in [z for z in lst if not z.invalidated][-k:]]

    return D.to_jsonable({
        "symbol": ctx["symbol"], "price": ctx["price"], "session": ctx["session"],
        "trend": {"1d": ctx["d1_trend"], "4h": ctx["h4_trend"], "1h": ctx["structure"]["1h"]["trend"],
                  "15m": ctx["structure"]["15m"]["trend"], "5m": ctx["structure"]["5m"]["trend"]},
        "structure_events": {tf: last_events(tf) for tf in ("1d", "4h", "1h", "15m", "5m")},
        "key_levels": ctx["levels"], "eqh": ctx["eqh"], "eql": ctx["eql"], "sweeps_today": ctx["sweeps"],
        "draw_on_liquidity": {"above": [{"price": p, "name": n} for p, n in ctx["dol_above"]],
                              "below": [{"price": p, "name": n} for p, n in ctx["dol_below"]]},
        "dealing_range_1h": ctx["dealing_range"],
        "fvg_open": {tf: zones(ctx["fvg"][tf]) for tf in ("4h", "1h", "15m", "5m")},
        "order_blocks": {tf: zones(ctx["ob"][tf], 3) for tf in ("4h", "1h", "15m")},
        "crt": ctx["crt"], "smt": ctx["smt"], "indicators": ctx["ind"],
    })
