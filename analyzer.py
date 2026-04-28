"""
analyzer.py — Full Wyckoff Long Trade Checklist
צ'קליסט עסקת לונג:
  המניה: LPS חודשי (2-5 חודשים) + פאזה D-E + מיני-איסוף יומי (2+ חודשים) + LPS יומי נוכחי
  השוק:  SPY יומי — חולשת מוכרים (LPS) → חצי סיכון / היפוך בתמיכה (פאזה B) → סיכון שלם
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

import config


# ─────────────────────────────────────────────
#  Dataclasses
# ─────────────────────────────────────────────

@dataclass
class ChecklistResult:
    ticker: str
    detected: bool

    # ✅ סעיף 1: LPS חודשי (2-5 חודשים)
    monthly_lps_ok: bool = False
    monthly_lps_months: int = 0

    # ✅ סעיף 2: פאזה D-E (מחיר בחלק עליון של טווח שנתי)
    monthly_phase_de: bool = False

    # ✅ סעיף 3: מיני-איסוף יומי (2+ חודשים)
    daily_mini_accum_ok: bool = False
    daily_accum_days: int = 0

    # ✅ סעיף 4: LPS יומי נוכחי (חולשת מוכרים)
    daily_lps_ok: bool = False
    lps_start_date: Optional[str] = None
    lps_end_date: Optional[str] = None
    lps_days: Optional[int] = None
    total_decline_pct: Optional[float] = None
    volume_trend: Optional[str] = None

    # ✅ סעיף 5: תזמון כניסה
    entry_mode: Optional[str] = None   # "breakout" | "spring" | None

    # ציון כולל (0-4)
    checklist_score: int = 0

    # נתוני תצוגה
    current_price: Optional[float] = None
    ohlcv: Optional[pd.DataFrame] = field(default=None, repr=False)
    error: Optional[str] = None


# שמירת תאימות אחורה
WyckoffResult = ChecklistResult


@dataclass
class SpyAnalysis:
    """ניתוח SPY לצורך קביעת רמת סיכון."""
    lps_sellers_weakness: bool = False   # חצי סיכון
    phase_b_reversal: bool = False       # סיכון שלם
    rsi_daily: float = 50.0
    monthly_lps_ok: bool = False
    error: Optional[str] = None


# ─────────────────────────────────────────────
#  עזרים
# ─────────────────────────────────────────────

def _volume_trend_label(volumes: list[float], avg_volume: float) -> str:
    if len(volumes) < 2:
        return "Below Avg"
    arr = np.array(volumes, dtype=float)
    slope = float(np.polyfit(np.arange(len(arr)), arr, 1)[0])
    if slope < 0:
        return "Declining"
    if all(v < avg_volume for v in volumes):
        return "Below Avg"
    return "Mixed"


def _calc_rsi(closes: pd.Series, period: int = 14) -> float:
    delta = closes.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - 100 / (1 + rs)
    v = rsi.iloc[-1]
    return float(v) if pd.notna(v) else 50.0


def _download(ticker: str, period: str, interval: str) -> Optional[pd.DataFrame]:
    """הורדת נתונים + נרמול עמודות."""
    try:
        raw = yf.download(ticker, period=period, interval=interval,
                          progress=False, auto_adjust=True)
    except Exception:
        return None
    if raw is None or raw.empty:
        return None
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    raw = raw.loc[:, ~raw.columns.duplicated()]
    df = raw[["Open", "High", "Low", "Close", "Volume"]].copy().dropna()
    return df if not df.empty else None


# ─────────────────────────────────────────────
#  בדיקות המניה
# ─────────────────────────────────────────────

def _detect_monthly_lps(ticker: str) -> tuple[bool, int, bool]:
    """
    בודק LPS חודשי (2-5 חודשים) + פאזה D-E.
    מחזיר: (lps_found, lps_months, phase_de)
    """
    df = _download(ticker, period="18mo", interval="1mo")
    if df is None or len(df) < 5:
        return False, 0, False

    df["body"] = (df["Close"] - df["Open"]).abs()
    df["avg_body"] = df["body"].rolling(min(6, len(df))).mean()
    df.dropna(inplace=True)

    if len(df) < 3:
        return False, 0, False

    current_close = float(df["Close"].iloc[-1])
    high_12 = float(df["High"].max())
    low_12 = float(df["Low"].min())
    range_12 = high_12 - low_12

    # פאזה D-E: מחיר בחלק העליון 40% של הטווח השנתי
    if range_12 > 0:
        phase_de = current_close > (low_12 + config.PHASE_DE_THRESHOLD * range_12)
    else:
        phase_de = False

    total = len(df)
    for end_offset in range(3):  # LPS יכול להסתיים עד 3 חודשים אחורה
        end_pos = total - 1 - end_offset
        if end_pos < 1:
            break

        # ספור חודשים רצופים עם גוף קטן
        count = 0
        for i in range(end_pos, max(-1, end_pos - config.MONTHLY_LPS_MAX_MONTHS - 1), -1):
            row = df.iloc[i]
            if row["body"] < row["avg_body"] * 1.0:
                count += 1
            else:
                break

        if not (config.MONTHLY_LPS_MIN_MONTHS <= count <= config.MONTHLY_LPS_MAX_MONTHS):
            continue

        lps_start = end_pos - count + 1
        open_first = float(df.iloc[lps_start]["Open"])
        close_last = float(df.iloc[end_pos]["Close"])

        # הסדרה לא עולה יותר מ-5% (זו התנחלות, לא פריצה)
        if close_last > open_first * 1.05:
            continue

        return True, count, phase_de

    return False, 0, phase_de


def _detect_daily_mini_accum(df: pd.DataFrame) -> tuple[bool, int]:
    """
    בודק מיני-איסוף יומי: טווח מחיר כולל < 20% על פני 40+ ימים.
    מחזיר: (ok, ימים_בטווח_מרכזי)
    """
    lookback = min(65, len(df))
    sub = df.tail(lookback)

    max_high = float(sub["High"].max())
    min_low = float(sub["Low"].min())
    mean_close = float(sub["Close"].mean())

    if mean_close <= 0:
        return False, 0

    total_range_pct = (max_high - min_low) / mean_close
    accum_ok = total_range_pct < config.MINI_ACCUM_RANGE_MAX

    # ימים שנמצאו בליבת הטווח (80% האמצעיים)
    core_low = min_low + 0.1 * (max_high - min_low)
    core_high = max_high - 0.1 * (max_high - min_low)
    days_in_core = int(((sub["Low"] >= core_low) & (sub["High"] <= core_high)).sum())

    return accum_ok, days_in_core


def _detect_daily_lps(df: pd.DataFrame, mode: str = "long") -> tuple[bool, Optional[str], Optional[str], int, float]:
    """
    זיהוי LPS יומי נוכחי (חולשת מוכרים).
    מחזיר: (detected, start_date, end_date, days, decline_pct)
    """
    df = df.copy()
    df["body"] = (df["Close"] - df["Open"]).abs()
    df["avg_body"] = df["body"].rolling(config.ROLLING_BASELINE).mean()
    df.dropna(inplace=True)

    if df.empty:
        return False, None, None, 0, 0.0

    total = len(df)

    for end_offset in range(config.PULLBACK_RECENCY):
        end_pos = total - 1 - end_offset
        if end_pos < config.PULLBACK_MIN_DAYS - 1:
            break

        # ספור נרות קטנים רצופים לאחור מ-end_pos
        max_count = 0
        for i in range(end_pos, -1, -1):
            row = df.iloc[i]
            if row["body"] < config.PULLBACK_BODY_THRESHOLD * row["avg_body"]:
                max_count += 1
            else:
                break

        if max_count < config.PULLBACK_MIN_DAYS:
            continue

        # נסה כל אורך מ-MIN עד min(max_count, MAX) — מהקצר לארוך
        for count in range(config.PULLBACK_MIN_DAYS, min(max_count, config.PULLBACK_MAX_DAYS) + 1):
            lps_start_pos = end_pos - count + 1

            # בדיקת spike + כיוון כל נר (חייב יורד או שטוח)
            has_spike = False
            candle_ok = True
            for i in range(lps_start_pos, end_pos + 1):
                row = df.iloc[i]
                move = abs(float(row["Close"]) - float(row["Open"])) / float(row["Open"])
                if move > config.MAX_SINGLE_SPIKE:
                    has_spike = True
                    break
                if mode == "long" and float(row["Close"]) > float(row["Open"]):
                    candle_ok = False
                    break
                if mode == "short" and float(row["Close"]) < float(row["Open"]):
                    candle_ok = False
                    break
            if has_spike or not candle_ok:
                continue

            open_first = float(df.iloc[lps_start_pos]["Open"])
            close_last = float(df.iloc[end_pos]["Close"])

            if mode == "long":
                if close_last > open_first * (1 + config.LPS_DIRECTION_TOLERANCE):
                    continue
            else:
                if close_last < open_first * (1 - config.LPS_DIRECTION_TOLERANCE):
                    continue

            decline_pct = round((open_first - close_last) / open_first * 100, 2)
            start_date = str(df.index[lps_start_pos].date())
            end_date = str(df.index[end_pos].date())
            return True, start_date, end_date, count, decline_pct

    return False, None, None, 0, 0.0


def _detect_entry_timing(df: pd.DataFrame) -> Optional[str]:
    """
    תזמון כניסה מדויק (2 הנרות האחרונים):
    - "breakout": close של הנר האחרון > high של הנר הקודם
    - "spring":   low של הנר האחרון < low של הנר הקודם, אך close חזר מעל low הקודם
    """
    if len(df) < 2:
        return None

    prev = df.iloc[-2]
    curr = df.iloc[-1]

    prev_high = float(prev["High"])
    prev_low = float(prev["Low"])
    curr_close = float(curr["Close"])
    curr_low = float(curr["Low"])

    if curr_close > prev_high:
        return "breakout"
    if curr_low < prev_low and curr_close > prev_low:
        return "spring"
    return None


# ─────────────────────────────────────────────
#  ניתוח SPY
# ─────────────────────────────────────────────

def analyze_spy() -> SpyAnalysis:
    """
    מנתח את SPY לצורך קביעת רמת סיכון:
    - phase_b_reversal     → סיכון שלם  (SPY בפאזה B, היפוך בתמיכה)
    - lps_sellers_weakness → חצי סיכון  (SPY יומי LPS, חולשת מוכרים)
    - ללא שניהם            → רבע סיכון
    """
    df = _download("SPY", period="70d", interval="1d")
    if df is None or len(df) < config.ROLLING_BASELINE + 5:
        return SpyAnalysis(error="No SPY data")

    df["avg_volume"] = df["Volume"].rolling(config.ROLLING_BASELINE).mean()

    rsi = _calc_rsi(df["Close"])

    # ── LPS חודשי של SPY ──
    spy_monthly_lps, _, _ = _detect_monthly_lps("SPY")

    # ── LPS יומי: חולשת מוכרים ──
    spy_lps_ok, _, _, _, _ = _detect_daily_lps(df, mode="long")

    # ── פאזה B + היפוך בתמיכה ──
    # רוצים לראות: RSI < SPY_PHASE_B_RSI_MAX + מחיר קרוב לתמוך (min 10 ימים) + נרות אחרונים עולים
    recent_low = float(df["Low"].tail(10).min())
    current_close = float(df["Close"].iloc[-1])
    near_support = current_close < recent_low * 1.05

    last_3_closes = df["Close"].tail(3).values
    recovering = len(last_3_closes) >= 2 and float(last_3_closes[-1]) > float(last_3_closes[-2])

    phase_b_reversal = (
        rsi < config.SPY_PHASE_B_RSI_MAX
        and near_support
        and recovering
    )

    # LPS + חולשת מוכרים: RSI נמוך + LPS זוהה
    lps_sellers_weakness = (
        rsi < config.SPY_LPS_RSI_MAX
        and spy_lps_ok
    )

    return SpyAnalysis(
        lps_sellers_weakness=lps_sellers_weakness,
        phase_b_reversal=phase_b_reversal,
        rsi_daily=round(rsi, 1),
        monthly_lps_ok=spy_monthly_lps,
    )


# ─────────────────────────────────────────────
#  פונקציה ראשית
# ─────────────────────────────────────────────

def analyze(ticker: str, mode: str = "long") -> ChecklistResult:
    """
    ניתוח צ'קליסט מלא לעסקת לונג.
    mode="short" → LPS הפוך (חולשת קונים), לסריקת שורטים.
    """
    # ── הורדת נתונים יומיים ──
    df = _download(ticker, period="70d", interval="1d")
    if df is None:
        return ChecklistResult(ticker=ticker, detected=False, error="No data returned by yfinance")

    df["avg_volume"] = df["Volume"].rolling(config.ROLLING_BASELINE).mean()

    if len(df) < config.ROLLING_BASELINE:
        return ChecklistResult(
            ticker=ticker, detected=False,
            error=f"Insufficient data ({len(df)} days < {config.ROLLING_BASELINE} required)",
        )

    df.dropna(inplace=True)
    current_price = float(df["Close"].iloc[-1])

    # בדיקת תנודתיות מינימלית
    avg_body_val = float((df["Close"] - df["Open"]).abs().rolling(config.ROLLING_BASELINE).mean().iloc[-1])
    if current_price > 0 and (avg_body_val / current_price) < config.MIN_AVG_BODY_PCT:
        return ChecklistResult(ticker=ticker, detected=False, current_price=current_price,
                               error="Insufficient volatility (frozen stock)")

    # ── LPS יומי בלבד ──
    daily_lps_ok, lps_start, lps_end, lps_days, decline_pct = _detect_daily_lps(df, mode=mode)

    # ── Volume trend ──
    volume_trend = None
    if daily_lps_ok and lps_start and lps_end:
        date_strs = [str(d.date()) for d in df.index]
        if lps_start in date_strs and lps_end in date_strs:
            s = date_strs.index(lps_start)
            e = date_strs.index(lps_end)
            vols = [float(df.iloc[i]["Volume"]) for i in range(s, e + 1)]
            avg_vol_v = df["avg_volume"].dropna()
            avg_vol = float(avg_vol_v.iloc[-1]) if not avg_vol_v.empty else 0.0
            volume_trend = _volume_trend_label(vols, avg_vol)

    detected = bool(daily_lps_ok)

    return ChecklistResult(
        ticker=ticker,
        detected=detected,
        daily_lps_ok=daily_lps_ok,
        lps_start_date=lps_start,
        lps_end_date=lps_end,
        lps_days=lps_days,
        total_decline_pct=decline_pct,
        volume_trend=volume_trend,
        current_price=round(current_price, 2),
        ohlcv=df,
    )
