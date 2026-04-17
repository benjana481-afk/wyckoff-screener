# ---- פרסטים מ-Finviz ----
PRESETS: dict[str, dict[str, str]] = {
    "📈 גבוה שנתי": {
        "Industry": "Stocks only (ex-Funds)",
        "Market Cap.": "+Small (over $300mln)",
        "Performance": "Year +30%",
        "50-Day Simple Moving Average": "Price above SMA50",
        "200-Day Simple Moving Average": "Price above SMA200",
        "Average Volume": "Over 100K",
        "Price": "Over $5",
    },
    "💰 Market Cap": {
        "Industry": "Stocks only (ex-Funds)",
        "Market Cap.": "+Small (over $300mln)",
        "Average Volume": "Over 100K",
        "Price": "Over $5",
    },
    "🔻 שורטים": {
        "Industry": "Stocks only (ex-Funds)",
        "52-Week High/Low": "5% or more above Low",
        "50-Day High/Low": "0-5% above Low",
        "Average Volume": "Over 100K",
        "Price": "Over $3",
    },
}

DEFAULT_PRESET: str = "📈 גבוה שנתי"

# ---- הגדרות אלגוריתם Wyckoff ----
LOOKBACK_DAYS: int = 30
ROLLING_BASELINE: int = 20       # ימים לחישוב ממוצע גוף / volume

SOS_WINDOW: int = 15             # חיפוש SOS רק ב-15 ימים אחרונים
SOS_BODY_MULTIPLIER: float = 1.5  # קבוע, לא בשימוש לזיהוי LPS
SOS_VOLUME_MULTIPLIER: float = 1.5  # קבוע, לא בשימוש לזיהוי LPS

# ---- פרמטרים שנחשפים ב-UI ----
PULLBACK_MIN_DAYS: int = 3        # מינימום ימי pullback
PULLBACK_MAX_DAYS: int = 7        # מקסימום ימי pullback
PULLBACK_BODY_THRESHOLD: float = 1.0   # גוף נר < ממוצע (body below average)
PULLBACK_RECENCY: int = 2         # ה-LPS חייב להסתיים ב-2 ימים האחרונים
LPS_DIRECTION_TOLERANCE: float = 0.02  # מאפשר עד +2% עליה כוללת בסדרה (Wyckoff consolidation)
MAX_SINGLE_SPIKE: float = 0.015       # נר בודד לא יזוז יותר מ-1.5% (open vs close)
MIN_AVG_BODY_PCT: float = 0.005      # ממוצע גוף חייב להיות לפחות 0.5% מהמחיר — מסנן מניות "קפואות"

# מקסימום מניות לסריקה
MAX_TICKERS: int = 2000
