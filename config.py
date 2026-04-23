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

# ---- הגדרות בסיס ----
LOOKBACK_DAYS: int = 30
ROLLING_BASELINE: int = 20       # ימים לחישוב ממוצע גוף / volume

# ---- פרמטרים LPS יומי ----
PULLBACK_MIN_DAYS: int = 3
PULLBACK_MAX_DAYS: int = 7
PULLBACK_BODY_THRESHOLD: float = 1.0
PULLBACK_RECENCY: int = 2
LPS_DIRECTION_TOLERANCE: float = 0.02
MAX_SINGLE_SPIKE: float = 0.015
MIN_AVG_BODY_PCT: float = 0.005

# ---- פרמטרים LPS חודשי ----
MONTHLY_LPS_MIN_MONTHS: int = 2
MONTHLY_LPS_MAX_MONTHS: int = 5
PHASE_DE_THRESHOLD: float = 0.60   # מחיר בחלק העליון 40% של טווח 12 חודש

# ---- פרמטרים מיני-איסוף יומי ----
MINI_ACCUM_RANGE_MAX: float = 0.20  # טווח מקס 20% = מיני-איסוף

# ---- פרמטרים SPY / סיכון ----
SPY_LPS_RSI_MAX: float = 45.0       # RSI מתחת = חולשת מוכרים ב-SPY
SPY_PHASE_B_RSI_MAX: float = 55.0   # RSI מתחת + היפוך = פאזה B ב-SPY

# מקסימום מניות לסריקה
MAX_TICKERS: int = 2000
