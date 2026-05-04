"""
daily_scan.py — סריקת LPS יומית ושליחת תוצאות לטלגרם.
"""
from __future__ import annotations

import os
import requests

import config
import analyzer
import screener


def send_telegram(token: str, chat_id: str, message: str) -> None:
    MAX_LEN = 4096
    while message:
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": message[:MAX_LEN], "parse_mode": "Markdown"},
                timeout=15,
            )
            print(f"Telegram: {resp.status_code}")
        except Exception as e:
            print(f"Telegram error: {e}")
        message = message[MAX_LEN:]


def run_scan(preset_name: str, mode: str = "long") -> list[str]:
    filters = config.PRESETS[preset_name]
    try:
        tickers = screener.get_tickers(filters)
    except screener.ScreenerError as e:
        print(f"Finviz error for {preset_name}: {e}")
        return []

    found = []
    for ticker, _ in tickers:
        r = analyzer.analyze(ticker, mode=mode)
        if r.detected:
            found.append(ticker)
    return sorted(found)


def main() -> None:
    token   = os.environ["TELEGRAM_TOKEN"].strip()
    chat_id = os.environ["TELEGRAM_CHAT_ID"].strip()

    annual_plus  = run_scan("📈 גבוה שנתי", mode="long")
    annual_minus = run_scan("📈 גבוה שנתי", mode="short")
    cap_plus     = run_scan("💰 Market Cap", mode="long")
    cap_minus    = run_scan("💰 Market Cap", mode="short")
    short_plus   = run_scan("🔻 שורטים",    mode="long")
    short_minus  = run_scan("🔻 שורטים",    mode="short")

    all_tickers = set(annual_plus + annual_minus + cap_plus + cap_minus + short_plus + short_minus)

    def fmt(label: str, tickers: list[str]) -> str:
        if not tickers:
            return f"{label} — 0 מניות: None"
        return f"{label} — {len(tickers)} מניות:\n{', '.join(tickers)}"

    message = (
        "*Benja · LPS Scanner*\n\n"
        f"{fmt('📈 גבוה שנתי LPS+', annual_plus)}\n\n"
        f"{fmt('📈 גבוה שנתי LPS-', annual_minus)}\n\n"
        f"{fmt('💰 Market Cap LPS+', cap_plus)}\n\n"
        f"{fmt('💰 Market Cap LPS-', cap_minus)}\n\n"
        f"{fmt('🔻 שורטים LPS+', short_plus)}\n\n"
        f"{fmt('🔻 שורטים LPS-', short_minus)}\n\n"
        f"✅ Total: {len(all_tickers)}"
    )

    print(message)
    send_telegram(token, chat_id, message)


if __name__ == "__main__":
    main()
