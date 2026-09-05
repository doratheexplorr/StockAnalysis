"""
Static, extensible sector mapping.

A production system would source this from a market-data provider's
reference/fundamentals endpoint; a hardcoded map is a deliberate MVP
shortcut (see README "Known limitations") that keeps sector-context scoring
working out of the box for common large-cap tickers without another paid
API dependency. Unmapped symbols fall back to "Diversified" with no sector
ETF trend contribution (scoring degrades gracefully, never crashes).
"""
from __future__ import annotations

SECTOR_MAP: dict[str, str] = {
    "NVDA": "Semiconductors", "AMD": "Semiconductors", "INTC": "Semiconductors",
    "TSM": "Semiconductors", "AVGO": "Semiconductors", "QCOM": "Semiconductors",
    "MU": "Semiconductors", "ASML": "Semiconductors",
    "AAPL": "Technology/Consumer Electronics", "MSFT": "Technology/Software",
    "GOOGL": "Technology/Internet", "GOOG": "Technology/Internet", "META": "Technology/Internet",
    "AMZN": "Consumer Discretionary/E-commerce", "NFLX": "Media/Streaming",
    "TSLA": "Consumer Discretionary/Auto",
    "JPM": "Banks/Financials", "BAC": "Banks/Financials", "WFC": "Banks/Financials",
    "GS": "Banks/Financials", "MS": "Banks/Financials", "C": "Banks/Financials",
    "XOM": "Energy", "CVX": "Energy", "COP": "Energy",
    "JNJ": "Healthcare/Pharma", "PFE": "Healthcare/Pharma", "UNH": "Healthcare/Insurance",
    "LLY": "Healthcare/Pharma",
    "V": "Financials/Payments", "MA": "Financials/Payments", "PYPL": "Financials/Payments",
    "WMT": "Consumer Staples/Retail", "COST": "Consumer Staples/Retail", "TGT": "Consumer Staples/Retail",
    "BA": "Industrials/Aerospace", "CAT": "Industrials",
    "DIS": "Media/Entertainment",
}

# proxy ETF used for sector-trend context (spec section 26 "Sector context")
SECTOR_ETF: dict[str, str] = {
    "Semiconductors": "SMH",
    "Technology/Software": "XLK",
    "Technology/Internet": "XLK",
    "Technology/Consumer Electronics": "XLK",
    "Consumer Discretionary/E-commerce": "XLY",
    "Consumer Discretionary/Auto": "XLY",
    "Media/Streaming": "XLC",
    "Media/Entertainment": "XLC",
    "Banks/Financials": "XLF",
    "Financials/Payments": "XLF",
    "Energy": "XLE",
    "Healthcare/Pharma": "XLV",
    "Healthcare/Insurance": "XLV",
    "Consumer Staples/Retail": "XLP",
    "Industrials/Aerospace": "XLI",
    "Industrials": "XLI",
}


def get_sector(symbol: str) -> str:
    return SECTOR_MAP.get(symbol.upper(), "Diversified")


def get_sector_etf(sector: str) -> str | None:
    return SECTOR_ETF.get(sector)
