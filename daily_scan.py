"""
daily_scan.py — סריקת צ'קליסט לונג יומית ושליחת תוצאות לטלגרם.
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


def run_scan_both(preset_name: str) -> tuple[list[str], list[str]]:
    """מריץ סריקה על פרסט נתון בשני מצבים ומחזיר (lps_plus, lps_minus)."""
    filters = config.PRESETS[preset_name]
    try:
        tickers = screener.get_tickers(filters)
    except screener.ScreenerError as e:
        print(f"Finviz error for {preset_name}: {e}")
        return [], []

    plus_found, minus_found = [], []
    for ticker, _ in tickers:
        r_long  = analyzer.analyze(ticker, mode="long")
        r_short = analyzer.analyze(ticker, mode="short")
        if r_long.detected:  plus_found.append(ticker)
        if r_short.detected: minus_found.append(ticker)
    return sorted(plus_found), sorted(minus_found)


def _send_long(token: str, chat_id: str, message: str) -> None:
    """שולח הודעה — מפצל אוטומטית אם עולה על 4096 תווים."""
    MAX_LEN = 4096
    while message:
        send_telegram(token, chat_id, message[:MAX_LEN])
        message = message[MAX_LEN:]


def main() -> None:
    token   = os.environ["TELEGRAM_TOKEN"].strip()
    chat_id = os.environ["TELEGRAM_CHAT_ID"].strip()

    # ── ניתוח SPY לרמת סיכון ──
    spy = analyzer.analyze_spy()
    if spy.phase_b_reversal:
        risk_label = "🟢 סיכון שלם (SPY פאזה B + היפוך)"
    elif spy.lps_sellers_weakness:
        risk_label = "🟡 חצי סיכון (SPY LPS — חולשת מוכרים)"
    else:
        risk_label = f"🔴 רבע סיכון (SPY RSI {spy.rsi_daily})"

    # ── סריקות — כל פרסט בשני מצבים ──
    annual_plus,  annual_minus  = run_scan_both("📈 גבוה שנתי")
    cap_plus,     cap_minus     = run_scan_both("💰 Market Cap")
    short_plus,   short_minus   = run_scan_both("🔻 שורטים")

    all_tickers = set(annual_plus + annual_minus + cap_plus + cap_minus + short_plus + short_minus)
    total = len(all_tickers)

    def fmt_section(label: str, tickers: list[str]) -> str:
        count = len(tickers)
        if count == 0:
            return f"{label} — 0 מניות: None"
        return f"{label} — {count} מניות:\n{', '.join(tickers)}"

    message = (
        "*Benja · LPS Scanner*\n"
        f"{risk_label}\n"
        "\n"
        f"{fmt_section('📈 גבוה שנתי LPS+', annual_plus)}\n"
        "\n"
        f"{fmt_section('📈 גבוה שנתי LPS-', annual_minus)}\n"
        "\n"
        f"{fmt_section('💰 Market Cap LPS+', cap_plus)}\n"
        "\n"
        f"{fmt_section('💰 Market Cap LPS-', cap_minus)}\n"
        "\n"
        f"{fmt_section('🔻 שורטים LPS+', short_plus)}\n"
        "\n"
        f"{fmt_section('🔻 שורטים LPS-', short_minus)}\n"
        "\n"
        f"✅ Total setups: {total}"
    )

    print(message)
    _send_long(token, chat_id, message)


if __name__ == "__main__":
    main()
