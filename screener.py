"""
screener.py — Fetches tickers from Finviz using finvizfinance (no API key needed).
"""
from __future__ import annotations

import random
import time

import pandas as pd

import config


class ScreenerError(Exception):
    pass


def _patch_user_agent() -> None:
    """Set a realistic browser User-Agent on finvizfinance's shared session."""
    try:
        import finvizfinance.util as fv_util

        session = getattr(fv_util, "SESSION", None)
        if session is not None:
            session.headers.update(
                {
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),
                    "Accept-Language": "en-US,en;q=0.9",
                }
            )
    except Exception:
        pass  # If the internals changed, proceed without patching


def _build_finviz_filters(ui_filters: dict[str, str]) -> dict[str, str]:
    """
    Drop 'Any' values — finvizfinance treats absent keys as 'no filter'.
    """
    return {k: v for k, v in ui_filters.items() if v and v != "Any"}


def _fetch_with_retry(fv_filters: dict[str, str], limit: int, max_retries: int = 3) -> pd.DataFrame:
    from finvizfinance.screener.overview import Overview

    _patch_user_agent()

    for attempt in range(max_retries):
        try:
            screener = Overview()
            screener.set_filter(filters_dict=fv_filters)
            df = screener.screener_view(limit=limit, sleep_sec=1, verbose=0)
            return df if df is not None else pd.DataFrame()
        except Exception as exc:
            if attempt == max_retries - 1:
                raise ScreenerError(f"Finviz request failed after {max_retries} attempts: {exc}") from exc
            wait = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(wait)

    return pd.DataFrame()


def get_tickers(
    ui_filters: dict[str, str],
    limit: int = config.MAX_TICKERS,
) -> list[tuple[str, str]]:
    """
    Scrape Finviz with the given filters and return a list of (ticker, company_name) tuples.

    Raises ScreenerError if Finviz is unreachable or returns no results.
    """
    fv_filters = _build_finviz_filters(ui_filters)
    df = _fetch_with_retry(fv_filters, limit=limit)

    if df is None or df.empty:
        raise ScreenerError(
            "Finviz returned 0 results. Try broadening your filters "
            "(e.g., remove the Sector filter or widen the Market Cap range)."
        )

    ticker_col = next((c for c in df.columns if c.upper() in ("TICKER", "SYMBOL")), None)
    name_col = next((c for c in df.columns if c.upper() in ("COMPANY", "NAME")), None)

    if ticker_col is None:
        raise ScreenerError(f"Unexpected Finviz response columns: {list(df.columns)}")

    tickers: list[tuple[str, str]] = []
    for _, row in df.iterrows():
        ticker = str(row[ticker_col]).strip()
        name = str(row[name_col]).strip() if name_col else ticker
        if ticker:
            tickers.append((ticker, name))

    return tickers
