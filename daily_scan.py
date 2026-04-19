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
        tickers = screener.get_tickers(filters)   # ללא limit — כל מה שפינביז מחזיר
    except screener.ScreenerError as e:
        print(f"Finviz error for {preset_name}: {e}")
        return []

    found = []
    for ticker, _ in tickers:
        result = analyzer.analyze(ticker, mode=mode)
        if result.detected:
            found.append(result.ticker)
    return found


def _send_long(token: str, chat_id: str, message: str) -> None:
    """שולח הודעה — מפצל אוטומטית אם עולה על 4096 תווים."""
    MAX_LEN = 4096
    while message:
        send_telegram(token, chat_id, message[:MAX_LEN])
        message = message[MAX_LEN:]


def main() -> None:
    token   = os.environ["TELEGRAM_TOKEN"].strip()
    chat_id = os.environ["TELEGRAM_CHAT_ID"].strip()

    # ── סריקות — כל פרסט בנפרד ──
    annual_tickers = run_scan("📈 גבוה שנתי", mode="long")
    cap_tickers    = run_scan("💰 Market Cap",  mode="long")
    short_tickers  = run_scan("🔻 שורטים",     mode="short")

    total = len(set(annual_tickers + cap_tickers + short_tickers))

    def fmt_section(label: str, tickers: list[str]) -> str:
        tickers = sorted(tickers)
        count = len(tickers)
        if count == 0:
            return f"{label} — 0 מניות: None"
        return f"{label} — {count} מניות:\n{', '.join(tickers)}"

    message = (
        "*Benja · LPS Scanner*\n"
        "\n"
        f"{fmt_section('📈 גבוה שנתי', annual_tickers)}\n"
        "\n"
        f"{fmt_section('💰 Market Cap', cap_tickers)}\n"
        "\n"
        f"{fmt_section('🔻 LPSy Short', short_tickers)}\n"
        "\n"
        f"✅ Total setups: {total}"
    )

    print(message)
    _send_long(token, chat_id, message)


if __name__ == "__main__":
    main()
