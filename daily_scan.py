"""
daily_scan.py — סריקת LPS יומית ושליחת תוצאות לטלגרם.
רץ ב-GitHub Actions כל יום לפני פתיחת שוק (08:00 ישראל).
"""
from __future__ import annotations

import os
import requests

import config
import analyzer
import screener


def send_telegram(token: str, chat_id: str, message: str) -> None:
    """שליחת הודעה לטלגרם."""
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
            timeout=15,
        )
        print(f"Telegram sent: {resp.status_code} — {resp.text[:100]}")
    except Exception as e:
        print(f"Telegram error: {e}")


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
    token   = os.environ["TELEGRAM_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    # ── סריקות ──
    long_tickers  = run_scan("📈 גבוה שנתי", mode="long")
    cap_tickers   = run_scan("💰 Market Cap",  mode="long")
    short_tickers = run_scan("🔻 שורטים",     mode="short")

    # ── בניית הודעה ──
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

    message = (
        "*Benja · LPS Scanner*\n"
        "\n"
        f"📈 LPS Long ({len(combined_long)}): {fmt(combined_long)}\n"
        f"📉 LPSy Short ({len(combined_short)}): {fmt(combined_short)}\n"
        "\n"
        f"✅ Total setups: {total}"
    )

    print(message)
    send_telegram(token, chat_id, message)


if __name__ == "__main__":
    main()
