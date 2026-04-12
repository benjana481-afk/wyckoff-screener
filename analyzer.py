"""
analyzer.py — זיהוי LPS (Last Point of Support) של Wyckoff.

הגדרת LPS:
  - גוף נר קטן מהממוצע (body < avg_body rolling 20 יום)
  - רצף של 3–8 ימים רצופים עם גוף קטן
  - הכיוון הכללי של הסדרה הוא יורד / flat (close אחרון < open ראשון × 1.02)
  - הסדרה מסתיימת ב-3 הימים האחרונים
  - volume — לתצוגה בלבד, לא משמש לזיהוי
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

import config


@dataclass
class WyckoffResult:
    ticker: str
    detected: bool
    lps_start_date: Optional[str] = None
    lps_end_date: Optional[str] = None
    lps_days: Optional[int] = None
    volume_trend: Optional[str] = None      # "Declining" | "Below Avg" | "Mixed" — display only
    total_decline_pct: Optional[float] = None  # % שינוי כולל בסדרה
    current_price: Optional[float] = None
    ohlcv: Optional[pd.DataFrame] = field(default=None, repr=False)
    error: Optional[str] = None


def _volume_trend_label(volumes: list[float], avg_volume: float) -> str:
    """מחשב תווית מגמת volume — לתצוגה בלבד, לא משמש לזיהוי."""
    if len(volumes) < 2:
        return "Below Avg"
    arr = np.array(volumes, dtype=float)
    slope = float(np.polyfit(np.arange(len(arr)), arr, 1)[0])
    if slope < 0:
        return "Declining"
    if all(v < avg_volume for v in volumes):
        return "Below Avg"
    return "Mixed"


def analyze(ticker: str, mode: str = "long") -> WyckoffResult:
    """
    mode="long"  → LPS רגיל: נרות צרים יורדים (חולשת מוכרים)
    mode="short" → LPS הפוך: נרות צרים עולים (חולשת קונים)
    """
    # ---- 1. הורדת OHLCV ----
    try:
        raw: pd.DataFrame = yf.download(
            ticker, period="40d", interval="1d", progress=False, auto_adjust=True
        )
    except Exception as exc:
        return WyckoffResult(ticker=ticker, detected=False, error=str(exc))

    if raw is None or raw.empty:
        return WyckoffResult(ticker=ticker, detected=False, error="No data returned by yfinance")

    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)

    # הסרת עמודות כפולות (מתרחש כשיש הורדות מקביליות)
    raw = raw.loc[:, ~raw.columns.duplicated()]

    df = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.dropna(inplace=True)
    df = df.tail(config.LOOKBACK_DAYS).copy()

    if len(df) < config.ROLLING_BASELINE:
        return WyckoffResult(
            ticker=ticker,
            detected=False,
            error=f"Insufficient data ({len(df)} days < {config.ROLLING_BASELINE} required)",
        )

    # ---- 2. ממוצעים נעים ----
    df["body"] = (df["Close"] - df["Open"]).abs()
    df["avg_body"] = df["body"].rolling(config.ROLLING_BASELINE).mean()
    df["avg_volume"] = df["Volume"].rolling(config.ROLLING_BASELINE).mean()
    df.dropna(inplace=True)

    if df.empty:
        return WyckoffResult(ticker=ticker, detected=False, error="Not enough data after rolling calc")

    current_price = float(df["Close"].iloc[-1])
    total_rows = len(df)

    # ---- 3. חיפוש LPS ----
    # נסה כל נקודת סיום אפשרית (מהיום ועד PULLBACK_RECENCY ימים אחורה)
    for end_offset in range(config.PULLBACK_RECENCY):
        end_pos = total_rows - 1 - end_offset

        if end_pos < config.PULLBACK_MIN_DAYS - 1:
            break

        # ספור ימים רצופים אחורה שעומדים בתנאי גוף קטן
        count = 0
        for i in range(end_pos, -1, -1):
            row = df.iloc[i]
            if row["body"] < config.PULLBACK_BODY_THRESHOLD * row["avg_body"]:
                count += 1
            else:
                break

        if not (config.PULLBACK_MIN_DAYS <= count <= config.PULLBACK_MAX_DAYS):
            continue

        lps_start_pos = end_pos - count + 1

        # ---- 4. בדיקת כיוון ----
        open_first = float(df.iloc[lps_start_pos]["Open"])
        close_last = float(df.iloc[end_pos]["Close"])

        if mode == "long":
            # לונג: הסדרה לא עולה יותר מ-2%
            if close_last > open_first * (1 + config.LPS_DIRECTION_TOLERANCE):
                continue
        else:
            # שורט: הסדרה לא יורדת יותר מ-2%
            if close_last < open_first * (1 - config.LPS_DIRECTION_TOLERANCE):
                continue

        # שינוי % כולל
        total_decline_pct = round((open_first - close_last) / open_first * 100, 2)

        # ---- 5. volume trend — לתצוגה בלבד ----
        lps_volumes = [float(df.iloc[i]["Volume"]) for i in range(lps_start_pos, end_pos + 1)]
        avg_vol = float(df.iloc[end_pos]["avg_volume"])

        return WyckoffResult(
            ticker=ticker,
            detected=True,
            lps_start_date=str(df.index[lps_start_pos].date()),
            lps_end_date=str(df.index[end_pos].date()),
            lps_days=count,
            volume_trend=_volume_trend_label(lps_volumes, avg_vol),
            total_decline_pct=total_decline_pct,
            current_price=round(current_price, 2),
            ohlcv=df,
        )

    return WyckoffResult(ticker=ticker, detected=False, current_price=current_price, ohlcv=df)
