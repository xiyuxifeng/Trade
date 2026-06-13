from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Callable, Protocol
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from src.common.paths import resolve_project_path
from src.db.session import session_scope
from src.models.job import Job
from src.models.market_data_snapshot import MarketSnapshot
from src.models.market_regime_record import MarketRegimeRecord
from src.models.trader_strategy_version import TraderStrategyVersion
from src.rule_pool.models import RulePool


HOME_STATUS_KEYS = (
    "data_readiness",
    "premarket",
    "postmarket",
    "pending_rules",
    "profile_proposals",
    "strategy_proposals",
    "current_strategy",
    "market_state",
)

HOME_STATUS_TARGETS = {
    "data_readiness": "/system/data",
    "premarket": "/daily/pre-market",
    "postmarket": "/daily/after-close",
    "pending_rules": "/rules/review",
    "profile_proposals": "/authors",
    "strategy_proposals": "/strategies",
    "current_strategy": "/strategies",
    "market_state": "/daily/overview",
}

MARKET_STATE_LABELS = {
    "strong_bull": "强势上涨",
    "weak_bull": "温和上涨",
    "range": "震荡",
    "weak_bear": "温和下跌",
    "panic": "快速下跌",
}


def format_market_state_label(value: str) -> str:
    return MARKET_STATE_LABELS.get(value, "状态待确认")


class Calendar(Protocol):
    def is_trade_date(self, value: date) -> bool: ...

    def latest_on_or_before(self, value: date) -> date | None: ...


class StatusSource(Protocol):
    async def load(self, *, business_date: date, latest_trading_day: date | None, profile_id: str | None) -> dict[str, dict[str, Any]]: ...


def _status(
    status: str,
    value: str | int | bool | None,
    label: str,
    detail: str,
    source: str,
    target_path: str,
    *,
    updated_at: str | None = None,
    unavailable_reason: str | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "value": value,
        "label": label,
        "detail": detail,
        "source": source,
        "updated_at": updated_at,
        "target_path": target_path,
        "unavailable_reason": unavailable_reason,
    }


def _unavailable(label: str, detail: str, target_path: str) -> dict[str, Any]:
    return _status(
        "unavailable",
        None,
        label,
        detail,
        "unavailable",
        target_path,
        unavailable_reason=detail,
    )


def build_unavailable_business_status(
    reason: str,
    failed_runs: list[dict[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    statuses = {
        key: _unavailable("状态暂不可用", reason, HOME_STATUS_TARGETS[key])
        for key in HOME_STATUS_KEYS
    }
    if failed_runs is None:
        statuses["failed_runs"] = _unavailable(
            "失败运行状态不可用",
            "未能读取失败运行记录，不显示为零。",
            "/system/runs",
        )
        return statuses
    failed_count = len(failed_runs)
    statuses["failed_runs"] = _status(
        "ready",
        failed_count,
        f"有 {failed_count} 项失败运行" if failed_count else "暂无失败运行",
        "数量复用现有系统 Dashboard 的失败记录。",
        "jobs",
        "/system/runs",
    )
    return statuses


class StoredTradeCalendar:
    """只读取已保存交易日历，不触发在线数据源。"""

    def __init__(self, path: str | Path = "data/backtest/trading_calendar.json") -> None:
        payload = json.loads(resolve_project_path(path).read_text(encoding="utf-8"))
        self._trade_dates = {date.fromisoformat(item) for item in payload.get("trade_dates", [])}
        if not self._trade_dates:
            raise ValueError("stored trading calendar is empty")

    def is_trade_date(self, value: date) -> bool:
        return value in self._trade_dates

    def latest_on_or_before(self, value: date) -> date | None:
        candidates = [item for item in self._trade_dates if item <= value]
        return max(candidates) if candidates else None


class DatabaseHomeStatusSource:
    async def load(self, *, business_date: date, latest_trading_day: date | None, profile_id: str | None) -> dict[str, dict[str, Any]]:
        return {
            "data_readiness": await self._safe(
                lambda: self._load_data_readiness(latest_trading_day),
                _unavailable("今日数据状态不可用", "未能读取目标日期的市场快照。", "/system/data"),
            ),
            "premarket": (
                await self._safe(
                    lambda: self._load_run("run-pre-market", business_date, "今日盘前", "/daily/pre-market"),
                    _unavailable("今日盘前状态不可用", "未能读取今日盘前记录。", "/daily/pre-market"),
                )
                if latest_trading_day == business_date
                else _status("ready", None, "非交易日无需盘前", "今天不是交易日，不生成盘前待办。", "trading_calendar", "/daily/pre-market")
            ),
            "postmarket": await self._safe(
                lambda: self._load_run("run-after-close", latest_trading_day, "最近交易日盘后", "/daily/after-close"),
                _unavailable("盘后状态不可用", "未能读取最近交易日盘后记录。", "/daily/after-close"),
            ),
            "pending_rules": await self._safe(
                self._load_pending_rules,
                _unavailable("待审核规则状态不可用", "未能读取规则审核数量。", "/rules/review"),
            ),
            "profile_proposals": _unavailable("画像建议能力尚未建立", "当前没有正式画像建议事实源，不显示为零。", "/authors"),
            "strategy_proposals": _unavailable("策略建议能力尚未建立", "当前没有正式策略建议事实源，不显示为零。", "/strategies"),
            "current_strategy": await self._safe(
                self._load_current_strategy,
                _unavailable("当前策略版本不可用", "未能读取已发布策略版本。", "/strategies"),
            ),
            "market_state": await self._safe(
                lambda: self._load_market_state(latest_trading_day),
                _unavailable("当前市场状态不可用", "未能读取最近交易日市场状态。", "/daily/overview"),
            ),
        }

    async def _safe(self, loader: Callable[[], Any], fallback: dict[str, Any]) -> dict[str, Any]:
        try:
            return await loader()
        except Exception:
            return fallback

    async def _load_data_readiness(self, target_date: date | None) -> dict[str, Any]:
        if target_date is None:
            return _unavailable("数据状态不可用", "交易日历不可用，无法确定目标日期。", "/system/data")
        async with session_scope() as session:
            row = await session.scalar(
                select(MarketSnapshot)
                .where(MarketSnapshot.trade_date == target_date)
                .order_by(MarketSnapshot.created_at.desc())
                .limit(1)
            )
        if row is None:
            return _unavailable("今日数据尚未生成", "目标日期没有市场快照，不能判断为已就绪。", "/system/data")
        ready = row.quality_status == "ok" and row.missing_section_count == 0
        state = "ready" if ready else "blocked"
        label = "今日数据已就绪" if ready else f"今日数据缺少 {row.missing_section_count} 项"
        return _status(
            state,
            ready,
            label,
            "市场快照质量已确认。" if ready else "缺失部分会影响盘前分析和后续验证。",
            "market_snapshots",
            "/system/data",
            updated_at=row.updated_at.isoformat() if row.updated_at else None,
        )

    async def _load_run(self, job_type: str, target_date: date | None, title: str, target_path: str) -> dict[str, Any]:
        if target_date is None:
            return _unavailable(f"{title}状态不可用", "交易日历不可用，无法确定目标日期。", target_path)
        variants = {job_type, job_type.replace("-", "_")}
        async with session_scope() as session:
            rows = list((await session.scalars(
                select(Job).where(Job.job_type.in_(variants)).order_by(Job.created_at.desc()).limit(20)
            )).all())
        row = next((item for item in rows if self._job_date(item) == target_date), None)
        if row is None:
            return _status("pending", False, f"{title}尚未完成", "没有找到目标日期的真实记录。", "jobs", target_path)
        complete = row.status == "success"
        state = "complete" if complete else "blocked" if row.status == "failed" else "pending"
        labels = {"complete": f"{title}已完成", "blocked": f"{title}失败", "pending": f"{title}处理中"}
        return _status(
            state,
            complete,
            labels[state],
            "状态来自现有兼容运行记录。",
            "jobs",
            target_path,
            updated_at=row.updated_at.isoformat() if row.updated_at else None,
        )

    def _job_date(self, row: Job) -> date | None:
        params = row.params if isinstance(row.params, dict) else {}
        raw = params.get("as_of_date") or params.get("date") or params.get("strategy_date")
        if isinstance(raw, str):
            try:
                return date.fromisoformat(raw[:10])
            except ValueError:
                return None
        return None

    async def _load_pending_rules(self) -> dict[str, Any]:
        async with session_scope() as session:
            count = int((await session.scalar(
                select(func.count()).select_from(RulePool).where(RulePool.review_status == "pending")
            )) or 0)
        return _status(
            "ready",
            count,
            f"有 {count} 条规则待审核" if count else "暂无规则待审核",
            "数量来自真实规则池。",
            "rule_pool",
            "/rules/review",
        )

    async def _load_current_strategy(self) -> dict[str, Any]:
        async with session_scope() as session:
            row = await session.scalar(
                select(TraderStrategyVersion)
                .where(TraderStrategyVersion.status == "released")
                .order_by(TraderStrategyVersion.released_at.desc(), TraderStrategyVersion.strategy_date.desc())
                .limit(1)
            )
        if row is None:
            return _unavailable("当前策略版本尚未建立", "没有已发布策略版本，不显示虚构版本。", "/strategies")
        return _status(
            "ready",
            row.version_name,
            f"当前策略版本：{row.version_name}",
            "当前仍来自兼容策略版本记录。",
            "trader_strategy_versions",
            "/strategies",
            updated_at=row.updated_at.isoformat() if row.updated_at else None,
        )

    async def _load_market_state(self, target_date: date | None) -> dict[str, Any]:
        if target_date is None:
            return _unavailable("当前市场状态不可用", "交易日历不可用，无法确定目标日期。", "/daily/overview")
        async with session_scope() as session:
            row = await session.scalar(
                select(MarketRegimeRecord)
                .where(MarketRegimeRecord.trade_date == target_date)
                .order_by(MarketRegimeRecord.created_at.desc())
                .limit(1)
            )
        if row is None:
            return _unavailable("当前市场状态尚未生成", "最近交易日没有市场状态记录。", "/daily/overview")
        state = "ready" if row.quality_status == "ok" else "partial"
        label = format_market_state_label(row.primary_label)
        return _status(
            state,
            label,
            f"当前市场状态：{label}",
            "质量不足时仅作为部分结果展示。",
            "market_regimes",
            "/daily/overview",
            updated_at=row.updated_at.isoformat() if row.updated_at else None,
        )


def select_next_action(business_status: dict[str, dict[str, Any]]) -> dict[str, str]:
    priorities = (
        ("data_readiness", {"blocked", "partial", "unavailable"}, "repair_data", "补齐缺失数据", "/system/data"),
        ("premarket", {"pending", "blocked"}, "prepare_premarket", "生成盘前计划", "/daily/pre-market"),
        ("postmarket", {"pending", "blocked"}, "review_market", "开始盘后复盘", "/daily/after-close"),
    )
    for key, actionable, action_id, label, target_path in priorities:
        if business_status.get(key, {}).get("status") in actionable:
            return {"id": action_id, "label": label, "target_path": target_path}
    pending_rules = business_status.get("pending_rules", {})
    if pending_rules.get("status") == "ready" and isinstance(pending_rules.get("value"), int) and pending_rules["value"] > 0:
        return {"id": "review_rules", "label": "审核候选规则", "target_path": "/rules/review"}
    failed_runs = business_status.get("failed_runs", {})
    if failed_runs.get("status") == "ready" and isinstance(failed_runs.get("value"), int) and failed_runs["value"] > 0:
        return {"id": "review_failures", "label": "查看失败原因", "target_path": "/system/runs"}
    return {"id": "view_status", "label": "查看今日状态", "target_path": "/daily/overview"}


class HomeDashboardService:
    def __init__(
        self,
        *,
        clock: Callable[[], datetime] | None = None,
        calendar: Calendar | None = None,
        status_source: StatusSource | None = None,
    ) -> None:
        self._clock = clock or (lambda: datetime.now(UTC))
        self._calendar = calendar
        self._status_source = status_source or DatabaseHomeStatusSource()

    async def build_summary(
        self,
        *,
        profile_id: str | None,
        failed_runs: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        now = self._clock().astimezone(ZoneInfo("Asia/Shanghai"))
        business_date = now.date()
        partial = False
        try:
            calendar = self._calendar or StoredTradeCalendar()
            is_trading_day: bool | None = calendar.is_trade_date(business_date)
            latest_trading_day = calendar.latest_on_or_before(business_date)
        except Exception:
            is_trading_day = None
            latest_trading_day = None
            partial = True

        try:
            business_status = await self._status_source.load(
                business_date=business_date,
                latest_trading_day=latest_trading_day,
                profile_id=profile_id,
            )
        except Exception as exc:
            reason = f"业务状态事实源不可用：{exc}"
            business_status = build_unavailable_business_status(reason, failed_runs)
            partial = True

        fallback_status = build_unavailable_business_status("状态事实尚未返回。", failed_runs)
        fallback_status.update(business_status)
        business_status = fallback_status
        if any(item.get("status") in {"partial", "unavailable"} for item in business_status.values()):
            partial = True
        return {
            "status": "partial" if partial else "ok",
            "business_date": business_date.isoformat(),
            "is_trading_day": is_trading_day,
            "latest_trading_day": latest_trading_day.isoformat() if latest_trading_day else None,
            "business_status": business_status,
            "next_action": select_next_action(business_status),
        }
