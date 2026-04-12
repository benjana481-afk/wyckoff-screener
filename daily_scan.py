"""
daily_scan.py — סריקת LPS יומית ושליחת תוצאות לוואטסאפ דרך CallMeBot.
רץ ב-GitHub Actions כל יום לפני פתיחת שוק (08:00 ישראל).
"""
from __future__ import annotations

import os
import urllib.parse
import urllib.request

import config
import analyzer
import screener


def send_whatsapp(phone: str, api_key: str, message: str) -> None:
    """שליחת הודעת וואטסאפ דרך CallMeBot (חינמי)."""
    encoded = urllib.parse.quote(message)
    url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={encoded}&apikey={api_key}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            print(f"WhatsApp sent: {resp.status}")
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

    # ── בניית הודעה ──
    lines = ["🕯️ *Benja · LPS Scanner — Daily Report*\n"]

    if long_tickers or cap_tickers:
        combined = sorted(set(long_tickers + cap_tickers))
        lines.append(f"📈 *LPS (Long)*: {', '.join(combined) if combined else 'None'}")
    else:
        lines.append("📈 *LPS (Long)*: None")

    if short_tickers:
        lines.append(f"📉 *LPSy (Short)*: {', '.join(sorted(short_tickers))}")
    else:
        lines.append("📉 *LPSy (Short)*: None")

    total = len(set(long_tickers + cap_tickers + short_tickers))
    lines.append(f"\n✅ Total setups: {total}")

    message = "\n".join(lines)
    print(message)
    send_whatsapp(phone, api_key, message)


if __name__ == "__main__":
    main()
