from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict


class SignalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    timeframe: str
    pattern_key: str
    pattern_name: str
    direction: str
    candle_timestamp: dt.datetime
    detected_at: dt.datetime
    quality_score: float
    classification: str
    score_breakdown: dict
    current_price: float
    entry_price: float
    stop_loss: float
    target_1: float
    target_2: float
    target_3: float
    risk_per_share: float
    reward_to_t1: float
    reward_to_t2: float
    reward_to_t3: float
    rr_t1: float
    rr_t2: float
    rr_t3: float
    risk_methodology: str
    technical_confirmations: list
    news_context: dict
    market_context: dict
    explanation: str
    status: str


class SignalListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    timeframe: str
    pattern_name: str
    direction: str
    detected_at: dt.datetime
    quality_score: float
    classification: str
    status: str
    current_price: float
    entry_price: float
