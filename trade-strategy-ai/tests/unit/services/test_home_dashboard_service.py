from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from src.services.home_dashboard_service import HomeDashboardService, format_market_state_label, select_next_action


class FakeCalendar:
    def __init__(self, trade_dates: set[date]) -> None:
        self.trade_dates = trade_dates

    def is_trade_date(self, value: date) -> bool:
        return value in self.trade_dates

    def latest_on_or_before(self, value: date) -> date | None:
        candidates = [item for item in self.trade_dates if item <= value]
        return max(candidates) if candidates else None


class FakeStatusSource:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error

    async def load(self, *, business_date: date, latest_trading_day: date | None, profile_id: str | None):
        if self.error is not None:
            raise self.error
        return {
            "data_readiness": status("ready", True, "今日数据已就绪", "/system/data"),
            "premarket": status("complete", True, "今日盘前已完成", "/daily/pre-market"),
            "postmarket": status("complete", True, "最近交易日盘后已完成", "/daily/after-close"),
            "pending_rules": status("ready", 2, "有 2 条规则待审核", "/rules/review"),
            "profile_proposals": status("unavailable", None, "画像建议能力尚未建立", "/authors"),
            "strategy_proposals": status("unavailable", None, "策略建议能力尚未建立", "/strategies"),
            "current_strategy": status("ready", "策略 2026.06", "当前策略版本", "/strategies"),
            "market_state": status("ready", "震荡", "当前市场状态", "/daily/overview"),
            "failed_runs": status("ready", 1, "有 1 项失败运行", "/system/runs"),
        }


def status(value_status: str, value: object, label: str, target_path: str) -> dict[str, object]:
    return {
        "status": value_status,
        "value": value,
        "label": label,
        "detail": label,
        "source": "test",
        "updated_at": None,
        "target_path": target_path,
        "unavailable_reason": None if value_status != "unavailable" else label,
    }


@pytest.mark.asyncio
async def test_build_summary_uses_latest_trade_day_on_non_trading_day() -> None:
    service = HomeDashboardService(
        clock=lambda: datetime(2026, 6, 13, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
        calendar=FakeCalendar({date(2026, 6, 12)}),
        status_source=FakeStatusSource(),
    )

    result = await service.build_summary(profile_id=None, failed_runs=[])

    assert result["is_trading_day"] is False
    assert result["latest_trading_day"] == "2026-06-12"
    assert result["business_status"]["profile_proposals"]["value"] is None
    assert result["next_action"]["id"] == "review_rules"


@pytest.mark.asyncio
async def test_build_summary_does_not_convert_source_failure_to_false_or_zero() -> None:
    service = HomeDashboardService(
        clock=lambda: datetime(2026, 6, 13, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
        calendar=FakeCalendar({date(2026, 6, 12)}),
        status_source=FakeStatusSource(error=RuntimeError("database unavailable")),
    )

    result = await service.build_summary(profile_id=None, failed_runs=[{"id": "failed-1"}])

    assert result["status"] == "partial"
    assert result["business_status"]["pending_rules"]["status"] == "unavailable"
    assert result["business_status"]["pending_rules"]["value"] is None
    assert result["business_status"]["failed_runs"]["value"] == 1


def test_select_next_action_uses_business_priority() -> None:
    assert select_next_action({"data_readiness": {"status": "blocked"}})["id"] == "repair_data"
    assert select_next_action({
        "data_readiness": {"status": "ready"},
        "premarket": {"status": "pending"},
    })["id"] == "prepare_premarket"
    assert select_next_action({
        "data_readiness": {"status": "ready"},
        "premarket": {"status": "complete"},
        "postmarket": {"status": "pending"},
    })["id"] == "review_market"
    assert select_next_action({
        "data_readiness": {"status": "ready"},
        "premarket": {"status": "complete"},
        "postmarket": {"status": "complete"},
        "pending_rules": {"status": "ready", "value": 0},
        "failed_runs": {"status": "ready", "value": 2},
    })["id"] == "review_failures"


def test_format_market_state_label_uses_business_chinese() -> None:
    assert format_market_state_label("strong_bull") == "强势上涨"
    assert format_market_state_label("range") == "震荡"
