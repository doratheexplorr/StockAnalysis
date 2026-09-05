from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict


class AlertHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    signal_id: int
    channel: str
    status: str
    sent_at: dt.datetime | None
    error_message: str | None
