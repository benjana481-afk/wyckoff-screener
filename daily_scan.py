"""
daily_scan.py — סריקת LPS יומית ושליחת תוצאות לוואטסאפ דרך CallMeBot.
רץ ב-GitHub Actions כל יום לפני פתיחת שוק (08:00 ישראל).
"""
from __future__ import annotations

import os
import requests

import config
import analyzer
import screener


def send_whatsapp(phone: str, api_key: str, message: str) -> None:
    """שליחת הודעת וואטסאפ דרך CallMeBot (חינמי)."""
    try:
        resp = requests.get(
            "https://api.callmebot.com/whatsapp.php",
            params={"phone": phone, "text": message, "apikey": api_key},
            timeout=15,
        )
        print(f"WhatsApp sent: {resp.status_code} — {resp.text[:100]}")
    except Exception as e:
        print(f"WhatsApp error: {e}")


def run_scan(preset_name: str, mode: str) -> list[str]:
    """מריץ סריקה על פרסט נתון ומחזיר רשימת טיקרים."""
    filters = config.PRESETS[preset_name]
    try:
        tickers = screener.get_tickers(filters, limit=500)
    except screener.ScreenerError as e:
        print(f"Finviz error for {preset_name}: {e}")
        return []

    found = []
    for ticker, _ in tickers:
        result = analyzer.analyze(ticker, mode=mode)
        if result.detected:
            found.append(result.ticker)
    return found


def main() -> None:
    phone   = os.environ["CALLMEBOT_PHONE"]
    api_key = os.environ["CALLMEBOT_APIKEY"]

    # ── סריקת לונג ──
    long_tickers  = run_scan("📈 גבוה שנתי", mode="long")
    cap_tickers   = run_scan("💰 Market Cap",  mode="long")
    # ── סריקת שורט ──
    short_tickers = run_scan("🔻 שורטים",     mode="short")

    # ── בניית הודעה — מקוצרת ל-30 טיקרים לכל היותר ──
    MAX_SHOW = 30

    combined_long  = sorted(set(long_tickers + cap_tickers))
    combined_short = sorted(short_tickers)

    def fmt(tickers: list[str]) -> str:
        if not tickers:
            return "None"
        shown = tickers[:MAX_SHOW]
        extra = len(tickers) - len(shown)
        s = ", ".join(shown)
        if extra > 0:
            s += f" (+{extra} more)"
        return s

    total = len(set(long_tickers + cap_tickers + short_tickers))

    lines = [
        "*Benja - LPS Scanner*",
        "",
        f"LPS Long ({len(combined_long)}): {fmt(combined_long)}",
        f"LPSy Short ({len(combined_short)}): {fmt(combined_short)}",
        "",
        f"Total setups: {total}",
    ]

    message = "\n".join(lines)
    print(message)
    send_whatsapp(phone, api_key, message)


if __name__ == "__main__":
    main()
