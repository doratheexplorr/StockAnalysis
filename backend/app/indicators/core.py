"""
Core technical indicator calculations.

Every function here is a pure function of a pandas DataFrame with columns
`open, high, low, close, volume` (indexed by UTC timestamp, oldest first) and
returns either a pandas Series (same index) or a scalar for the latest bar.
Nothing in this module knows about candlestick patterns, scoring, or alerts -
that separation is intentional (see README "Architecture") so each layer can
be unit tested and replaced independently.
"""
from __future__ import annotations

import pandas as pd


REQUIRED_COLUMNS = ("open", "high", "low", "close", "volume")


def _validate(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"OHLCV dataframe missing required columns: {missing}")


def sma(df: pd.DataFrame, period: int, column: str = "close") -> pd.Series:
    _validate(df)
    return df[column].rolling(window=period, min_periods=period).mean()


def ema(df: pd.DataFrame, period: int, column: str = "close") -> pd.Series:
    _validate(df)
    return df[column].ewm(span=period, adjust=False, min_periods=period).mean()


def rsi(df: pd.DataFrame, period: int = 14, column: str = "close") -> pd.Series:
    """Wilder's RSI."""
    _validate(df)
    delta = df[column].diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, pd.NA)
    result = 100 - (100 / (1 + rs))
    # where avg_loss is 0 and avg_gain > 0 -> RSI is 100; where both 0 -> 50 (flat market)
    result = result.where(avg_loss != 0, 100.0)
    result = result.where(~((avg_loss == 0) & (avg_gain == 0)), 50.0)
    return result


def macd(
    df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9, column: str = "close"
) -> pd.DataFrame:
    """Returns a DataFrame with columns: macd, signal, hist."""
    _validate(df)
    ema_fast = df[column].ewm(span=fast, adjust=False, min_periods=fast).mean()
    ema_slow = df[column].ewm(span=slow, adjust=False, min_periods=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    hist = macd_line - signal_line
    return pd.DataFrame({"macd": macd_line, "signal": signal_line, "hist": hist})


def true_range(df: pd.DataFrame) -> pd.Series:
    _validate(df)
    prev_close = df["close"].shift(1)
    tr1 = df["high"] - df["low"]
    tr2 = (df["high"] - prev_close).abs()
    tr3 = (df["low"] - prev_close).abs()
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Wilder's ATR (smoothed true range)."""
    tr = true_range(df)
    return tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


def average_volume(df: pd.DataFrame, period: int = 20) -> pd.Series:
    _validate(df)
    return df["volume"].rolling(window=period, min_periods=period).mean()


def relative_volume(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Latest volume / trailing average volume (excluding the current bar)."""
    _validate(df)
    avg = df["volume"].shift(1).rolling(window=period, min_periods=period).mean()
    return df["volume"] / avg.replace(0, pd.NA)


def recent_high(df: pd.DataFrame, period: int = 20) -> pd.Series:
    _validate(df)
    return df["high"].rolling(window=period, min_periods=1).max()


def recent_low(df: pd.DataFrame, period: int = 20) -> pd.Series:
    _validate(df)
    return df["low"].rolling(window=period, min_periods=1).min()
