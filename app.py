"""
app.py — Long Trade Checklist Scanner — Wyckoff Method
"""
from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

import analyzer
import config
import screener
from analyzer import ChecklistResult, SpyAnalysis

# ─────────────────────────────────────────────
#  Page config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Benja · Wyckoff Method",
    page_icon="📈",
    layout="wide",
)

# ─────────────────────────────────────────────
#  CSS — Warm White + Orange
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: #FAF8F5;
}

[data-testid="stSidebar"] {
    background: #FFFFFF !important;
    border-right: 1px solid #EDE8E0;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #1A1A1A !important;
    font-weight: 700;
}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span {
    color: #444 !important;
}

div[data-testid="stHorizontalBlock"] .stButton > button {
    background: #F5F1EB;
    border: 1px solid #DDD5C8;
    color: #555;
    border-radius: 6px;
    font-size: 0.75rem;
    padding: 0.4rem 0.2rem;
    transition: all 0.15s;
}
div[data-testid="stHorizontalBlock"] .stButton > button:hover {
    border-color: #F97316;
    color: #F97316;
    background: #FFF7F0;
}
div[data-testid="stHorizontalBlock"] .stButton > button[kind="primary"] {
    background: #F97316;
    border: 1px solid #F97316;
    color: #FFFFFF;
    font-weight: 600;
}

div[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: #F97316 !important;
    color: #FFFFFF !important;
    border: none !important;
    font-weight: 700 !important;
    letter-spacing: 0.03em;
    border-radius: 6px;
    box-shadow: 0 2px 10px rgba(249,115,22,0.35);
}
div[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
    background: #EA6A0A !important;
    box-shadow: 0 4px 16px rgba(249,115,22,0.5);
}

[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #EDE8E0;
    border-top: 3px solid #F97316;
    border-radius: 8px;
    padding: 1rem 1.2rem;
}
[data-testid="stMetricLabel"] {
    color: #999 !important;
    font-size: 0.75rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}
[data-testid="stMetricValue"] {
    color: #1A1A1A !important;
    font-size: 1.8rem;
    font-weight: 700;
}

hr { border-color: #EDE8E0 !important; }

[data-testid="stExpander"] {
    background: #FFFFFF;
    border: 1px solid #EDE8E0 !important;
    border-radius: 8px;
    margin-bottom: 0.4rem;
}
[data-testid="stExpander"] summary {
    color: #1A1A1A !important;
    font-weight: 500;
}

[data-testid="stDataFrame"] {
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #EDE8E0;
}

::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #FAF8F5; }
::-webkit-scrollbar-thumb { background: #DDD5C8; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  Header
# ─────────────────────────────────────────────
st.markdown("""
<div style="
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1.4rem 0 0.8rem;
    border-bottom: 1px solid #EDE8E0;
    margin-bottom: 1.5rem;
">
    <div>
        <div style="
            font-size: 2.6rem;
            font-weight: 900;
            color: #1A1A1A;
            letter-spacing: -0.04em;
            line-height: 1;
            font-family: 'Inter', sans-serif;
        ">
            benja<span style="color:#F97316;">·</span>
        </div>
        <div style="
            font-size: 0.7rem;
            font-weight: 600;
            color: #F97316;
            letter-spacing: 0.22em;
            text-transform: uppercase;
            margin-top: 0.1rem;
        ">WYCKOFF METHOD</div>
    </div>
    <div style="
        margin-left: auto;
        font-size: 0.78rem;
        color: #AAA;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        align-self: flex-end;
        padding-bottom: 0.2rem;
    ">Long Trade Checklist Scanner</div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  Sidebar
# ─────────────────────────────────────────────
with st.sidebar:

    st.markdown("### 🗂 Finviz Presets")

    preset_names = list(config.PRESETS.keys())
    if "preset" not in st.session_state:
        st.session_state["preset"] = config.DEFAULT_PRESET

    col1, col2, col3 = st.columns(3)
    for i, name in enumerate(preset_names):
        col = [col1, col2, col3][i]
        is_active = st.session_state["preset"] == name
        if col.button(name, use_container_width=True,
                      type="primary" if is_active else "secondary"):
            st.session_state["preset"] = name
            st.rerun()

    active_preset = st.session_state["preset"]
    active_filters = config.PRESETS[active_preset]

    with st.expander("Active Filters", expanded=False):
        for k, v in active_filters.items():
            st.markdown(f"<small style='color:#AAA'>{k}</small><br>"
                        f"<span style='color:#F97316; font-weight:500'>{v}</span>",
                        unsafe_allow_html=True)

    st.divider()

    st.markdown("### ⚙️ LPS Settings")

    pb_min, pb_max = st.slider(
        "Pullback Days (Daily LPS)",
        min_value=2, max_value=10,
        value=(config.PULLBACK_MIN_DAYS, config.PULLBACK_MAX_DAYS),
        help="מספר ימים רצופים של חולשה ביומי",
    )

    max_tickers = st.slider(
        "Tickers to Scan",
        min_value=100, max_value=config.MAX_TICKERS,
        value=2000, step=100,
        help="יותר טיקרים = זמן סריקה ארוך יותר",
    )

    st.divider()
    run_btn = st.button("🔍  Run Scan", type="primary", use_container_width=True)


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _risk_badge(spy: SpyAnalysis, scan_mode: str) -> str:
    """מחשב תווית רמת סיכון לפי מצב SPY."""
    if scan_mode == "short":
        return ""
    if spy.phase_b_reversal:
        return "🟢 סיכון שלם"
    if spy.lps_sellers_weakness:
        return "🟡 חצי סיכון"
    return "🔴 רבע סיכון"


def _risk_color(spy: SpyAnalysis, scan_mode: str) -> str:
    if scan_mode == "short":
        return "#F97316"
    if spy.phase_b_reversal:
        return "#16A34A"
    if spy.lps_sellers_weakness:
        return "#CA8A04"
    return "#DC2626"


def _checklist_html(r: ChecklistResult) -> str:
    """HTML של 4 פריטי הצ'קליסט + תזמון."""
    def item(ok: bool, label: str, detail: str = "") -> str:
        icon = "✅" if ok else "⬜"
        color = "#16A34A" if ok else "#AAA"
        det = f"<span style='color:#999; font-size:0.75rem; margin-right:0.4rem'>{detail}</span>" if detail else ""
        return (
            f"<div style='display:flex; align-items:baseline; gap:0.4rem; margin:0.15rem 0;'>"
            f"{det}"
            f"<span style='color:{color}; font-size:0.82rem'>{icon} {label}</span>"
            f"</div>"
        )

    entry_label = ""
    if r.entry_mode == "breakout":
        entry_label = "📈 פריצת גבוה"
    elif r.entry_mode == "spring":
        entry_label = "🔄 Spring + חזרה"

    months_txt = f"{r.monthly_lps_months}m" if r.monthly_lps_months else ""
    days_txt = f"{r.daily_accum_days}d" if r.daily_accum_days else ""
    lps_txt = f"{r.lps_days}d / {abs(r.total_decline_pct or 0):.1f}%" if r.lps_days else ""
    entry_txt = entry_label if entry_label else ("⬜ ממתין לכניסה" if r.daily_lps_ok else "")

    html = (
        f"<div style='background:#FAFAF8; border-radius:6px; padding:0.6rem 0.8rem;"
        f"border:1px solid #EDE8E0; font-family:Inter,sans-serif;'>"
        + item(r.monthly_lps_ok, f"LPS חודשי", months_txt)
        + item(r.monthly_phase_de, "פאזה D-E (חודשי)")
        + item(r.daily_mini_accum_ok, "מיני-איסוף יומי (2+ חודשים)", days_txt)
        + item(r.daily_lps_ok, "LPS יומי — חולשת מוכרים", lps_txt)
        + (f"<div style='margin-top:0.4rem; padding-top:0.4rem; border-top:1px solid #EDE8E0;"
           f"color:#F97316; font-size:0.82rem; font-weight:600;'>{entry_txt}</div>"
           if entry_txt else "")
        + "</div>"
    )
    return html


def _score_color(score: int) -> str:
    if score >= 4:
        return "#16A34A"
    if score >= 3:
        return "#CA8A04"
    if score >= 2:
        return "#F97316"
    return "#DC2626"


# ─────────────────────────────────────────────
#  Scan logic
# ─────────────────────────────────────────────
if run_btn:
    config.PULLBACK_MIN_DAYS = pb_min
    config.PULLBACK_MAX_DAYS = pb_max

    scan_mode = "long"
    pattern_name = "LPS"

    # ── שליפת טיקרים מ-Finviz ──
    with st.spinner("Fetching tickers from Finviz..."):
        try:
            tickers = screener.get_tickers(active_filters, limit=max_tickers)
        except screener.ScreenerError as e:
            st.error(f"Finviz error: {e}")
            st.stop()

    st.info(f"Found **{len(tickers)}** tickers — running full checklist analysis...")

    progress_bar = st.progress(0.0)
    status_text = st.empty()
    results: list[ChecklistResult] = []
    errors: list[str] = []

    for i, (ticker, _) in enumerate(tickers):
        status_text.text(f"Analyzing {ticker}  ({i + 1} / {len(tickers)})")
        result = analyzer.analyze(ticker, mode=scan_mode)
        if result.error and "volatility" not in result.error and "Insufficient data" not in result.error and "No data" not in result.error:
            errors.append(f"{ticker}: {result.error}")
        elif result.detected:
            results.append(result)
        progress_bar.progress((i + 1) / len(tickers))

    progress_bar.empty()
    status_text.empty()

    # ── רשימה מצטברת ──
    new_tickers = {r.ticker for r in results}
    existing_list: list[str] = st.session_state.get("ticker_list", [])
    existing_set = set(existing_list)
    for t in new_tickers:
        if t not in existing_set:
            existing_list.append(t)
            existing_set.add(t)
    st.session_state["ticker_list"] = existing_list

    st.session_state["results"] = results
    st.session_state["scan_info"] = {
        "total": len(tickers),
        "detected": len(results),
        "errors": errors,
        "preset": active_preset,
        "pattern_name": pattern_name,
        "scan_mode": scan_mode,
    }


# ─────────────────────────────────────────────
#  Results
# ─────────────────────────────────────────────
results: list[ChecklistResult] = st.session_state.get("results", [])
scan_info: dict = st.session_state.get("scan_info", {})
spy_analysis: SpyAnalysis = st.session_state.get("spy_analysis", SpyAnalysis())

# ── Metrics ──
if scan_info:
    col1, col2, col3 = st.columns(3)
    col1.metric("Tickers Scanned", scan_info.get("total", 0))
    col2.metric("Setups Found", scan_info.get("detected", 0))
    col3.metric("Errors", len(scan_info.get("errors", [])))

    if scan_info.get("errors"):
        with st.expander(f"Errors ({len(scan_info['errors'])})"):
            for e in scan_info["errors"]:
                st.text(e)

# ── רשימה מצטברת ──
ticker_list: list[str] = st.session_state.get("ticker_list", [])
if ticker_list:
    ticker_str = ", ".join(ticker_list)
    col_l, col_r = st.columns([5, 1])
    with col_l:
        st.markdown(f"""
        <div style="
            background: #FFFFFF;
            border: 1px solid #EDE8E0;
            border-left: 3px solid #F97316;
            border-radius: 8px;
            padding: 0.8rem 1.2rem;
            margin-bottom: 1rem;
        ">
            <div style="color:#F97316; font-size:0.72rem; font-weight:700;
                        letter-spacing:0.12em; margin-bottom:0.4rem; text-transform:uppercase;">
                Accumulated List ({len(ticker_list)} tickers)
            </div>
            <div style="color:#333; font-size:0.92rem; line-height:1.8;
                        word-break:break-word; font-family:monospace;">
                {ticker_str}
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col_r:
        if st.button("🗑 Clear List", use_container_width=True):
            st.session_state["ticker_list"] = []
            st.rerun()

# ── Empty state ──
if not results and scan_info:
    st.markdown("""
    <div style="text-align:center; padding:3rem; color:#CCC;">
        <div style="font-size:2.5rem">📉</div>
        <p style="margin-top:0.5rem; color:#AAA;">No setups detected.<br>
        <small>Try a different preset or adjust the Pullback Days range.</small></p>
    </div>
    """, unsafe_allow_html=True)

elif results:
    smode = scan_info.get("scan_mode", "long")
    pname = scan_info.get("pattern_name", "LPS")
    accent = "#16A34A" if smode == "long" else "#DC2626"
    accent_bg = "#F0FDF4" if smode == "long" else "#FEF2F2"

    st.markdown(f"""
    <div style="
        background: {accent_bg};
        border: 1px solid {'#BBF7D0' if smode == 'long' else '#FECACA'};
        border-left: 3px solid {accent};
        border-radius: 8px;
        padding: 0.8rem 1.2rem;
        margin-bottom: 1.5rem;
    ">
        <span style="color:{accent}; font-weight:700; font-size:1rem;">
            {'📈' if smode == 'long' else '📉'} {len(results)} Setup{'s' if len(results) != 1 else ''} Found
        </span>
        <span style="color:#999; font-size:0.85rem; margin-left:0.8rem;">
            Preset: {scan_info.get('preset', '')}
        </span>
    </div>
    """, unsafe_allow_html=True)

    # ── Summary table ──
    table_data = {
        "Ticker":      [r.ticker for r in results],
        "LPS Days":    [r.lps_days or "—" for r in results],
        "Decline %":   [f"{abs(r.total_decline_pct or 0):.1f}%" for r in results],
        "Volume":      [r.volume_trend or "—" for r in results],
        "Price ($)":   [r.current_price for r in results],
    }
    st.dataframe(table_data, use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("### 📊 Charts")

    # צבעי נרות
    if smode == "long":
        candle_up, candle_down = "#16A34A", "#DC2626"
        lps_fill = "rgba(22,163,74,0.08)"
        lps_line = "rgba(22,163,74,0.5)"
        lps_font = "#16A34A"
    else:
        candle_up, candle_down = "#F97316", "#DC2626"
        lps_fill = "rgba(249,115,22,0.08)"
        lps_line = "rgba(249,115,22,0.5)"
        lps_font = "#F97316"

    for result in results:
        label = (
            f"📈  **{result.ticker}**"
            f"  ·  {result.lps_days} days"
            f"  ·  {abs(result.total_decline_pct or 0):.1f}% decline"
            f"  ·  ${result.current_price}"
        )

        with st.expander(label):
            if result.ohlcv is None or result.ohlcv.empty:
                st.warning("No chart data available.")
                continue

            df = result.ohlcv.tail(25).copy()

            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                row_heights=[0.72, 0.28],
                vertical_spacing=0.03,
            )

            fig.add_trace(
                go.Candlestick(
                    x=df.index,
                    open=df["Open"], high=df["High"],
                    low=df["Low"],   close=df["Close"],
                    name="Price",
                    increasing_line_color=candle_up,
                    decreasing_line_color=candle_down,
                    increasing_fillcolor=candle_up,
                    decreasing_fillcolor=candle_down,
                    whiskerwidth=0.5,
                ),
                row=1, col=1,
            )

            vol_colors = [
                candle_up if c >= o else candle_down
                for c, o in zip(df["Close"], df["Open"])
            ]
            fig.add_trace(
                go.Bar(
                    x=df.index, y=df["Volume"],
                    marker_color=vol_colors, opacity=0.5,
                    name="Volume",
                ),
                row=2, col=1,
            )

            if "avg_volume" in df.columns:
                avg_vol_val = float(df["avg_volume"].dropna().iloc[-1]) if not df["avg_volume"].dropna().empty else 0
                if avg_vol_val > 0:
                    fig.add_hline(
                        y=avg_vol_val,
                        line_dash="dot", line_color="#CCC",
                        annotation_text="avg vol",
                        annotation_font_color="#AAA",
                        annotation_position="bottom right",
                        row=2, col=1,
                    )

            date_strs = [str(d.date()) for d in df.index]
            if result.lps_start_date in date_strs and result.lps_end_date in date_strs:
                fig.add_vrect(
                    x0=result.lps_start_date,
                    x1=result.lps_end_date,
                    fillcolor=lps_fill,
                    line_color=lps_line,
                    line_width=1,
                    annotation_text="LPS",
                    annotation_position="top left",
                    annotation_font_color=lps_font,
                    annotation_font_size=11,
                )

            fig.update_layout(
                title=dict(
                    text=f"<b>{result.ticker}</b>  —  Score {result.checklist_score}/4",
                    font=dict(color="#1A1A1A", size=14),
                ),
                xaxis_rangeslider_visible=False,
                height=480,
                template="plotly_white",
                paper_bgcolor="#FFFFFF",
                plot_bgcolor="#FAFAFA",
                showlegend=False,
                margin=dict(l=50, r=20, t=50, b=20),
                font=dict(color="#555", size=11),
                xaxis=dict(gridcolor="#F0EDE8", showgrid=True, linecolor="#EDE8E0"),
                yaxis=dict(gridcolor="#F0EDE8", showgrid=True, linecolor="#EDE8E0"),
                xaxis2=dict(gridcolor="#F0EDE8", showgrid=True, linecolor="#EDE8E0"),
                yaxis2=dict(gridcolor="#F0EDE8", showgrid=True, linecolor="#EDE8E0"),
            )
            fig.update_yaxes(title_text="Price", title_font_color="#AAA", row=1, col=1)
            fig.update_yaxes(title_text="Volume", title_font_color="#AAA", row=2, col=1)

            st.plotly_chart(fig, use_container_width=True)
