from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo


SHANGHAI = ZoneInfo("Asia/Shanghai")
PRE_MARKET_DECISION_SLOT = "09-25"
POST_MARKET_REVIEW_SLOT = "17-30"


def slot_cutoff_at(trade_date: date, slot: str, *, timezone: ZoneInfo = SHANGHAI) -> datetime | None:
    parsed = _parse_slot(slot)
    if parsed is None:
        return None
    local_dt = datetime.combine(trade_date, parsed, tzinfo=timezone)
    return local_dt.astimezone(ZoneInfo("UTC"))


def is_available_by_cutoff(*, trade_date: date, slot: str, available_at: datetime | None) -> bool:
    cutoff = slot_cutoff_at(trade_date, slot)
    if cutoff is None or available_at is None:
        return False
    return available_at <= cutoff


def _parse_slot(value: str | None) -> time | None:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        hour, minute = raw.split("-", 1)
        return time(hour=int(hour), minute=int(minute))
    except (TypeError, ValueError):
        return None
