from __future__ import annotations

import json
import re
from datetime import date, timedelta
from collections import defaultdict
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.common.paths import resolve_project_path
from src.db.repositories import (
    MarketDataQualityRepository,
    MarketDatasetRepository,
    MarketRegimeFeatureRepository,
    MarketSnapshotItemRepository,
    MarketSnapshotRepository,
    MarketSnapshotSectionRepository,
)
from src.db.session import get_session_factory
from src.models.market_dataset import MarketDataset
from src.models.ohlcv_bar import OHLCVBar
from src.models.market_regime import MarketRegimeFeature
from src.services.base import BaseService, ServiceResult

DEFAULT_FEATURE_VERSION = "market-regime-features-v2"
FULL_MARKET_FEATURE_VERSION = "market-regime-features-v3"


def _normalize_date(value: Any) -> date | None:
    """把日期参数归一化为 date。"""
    if value in {None, ""}:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise ValueError(f"invalid date value: {value}")


def _to_plain(value: Any) -> Any:
    """把 dataclass / 容器值转成可序列化结构。"""
    if hasattr(value, "model_dump"):
        return _to_plain(value.model_dump())
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    return value


def _first_number(value: Any) -> int | None:
    """从任意 JSON 值中提取第一个数值。"""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        match = re.search(r"-?\d+(?:\.\d+)?", value.replace(",", ""))
        if match:
            return int(float(match.group(0)))
        return None
    if isinstance(value, dict):
        for nested in value.values():
            number = _first_number(nested)
            if number is not None:
                return number
        return None
    if isinstance(value, (list, tuple)):
        for nested in value:
            number = _first_number(nested)
            if number is not None:
                return number
        return None
    return None


def _first_text(value: Any) -> str | None:
    """从任意 JSON 值中提取第一个非空文本。"""
    if value is None:
        return None
    if isinstance(value, str) and value.strip():
        return value
    if isinstance(value, dict):
        for nested in value.values():
            text = _first_text(nested)
            if text is not None:
                return text
        return None
    if isinstance(value, (list, tuple)):
        for nested in value:
            text = _first_text(nested)
            if text is not None:
                return text
        return None
    return str(value)


def _safe_float(value: Any) -> float | None:
    """把值安全转换为 float。"""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", ""))
        except ValueError:
            return None
    return None


class MarketRegimeFeatureService(BaseService):
    """市场状态特征派生服务。"""

    service_name = "market-regime-feature"

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        snapshot_repository: MarketSnapshotRepository | None = None,
        section_repository: MarketSnapshotSectionRepository | None = None,
        item_repository: MarketSnapshotItemRepository | None = None,
        dataset_repository: MarketDatasetRepository | None = None,
        quality_repository: MarketDataQualityRepository | None = None,
        feature_repository: MarketRegimeFeatureRepository | None = None,
        artifact_root: str | Path | None = None,
    ) -> None:
        self._session_factory = session_factory or get_session_factory()
        self._snapshot_repository = snapshot_repository or MarketSnapshotRepository()
        self._section_repository = section_repository or MarketSnapshotSectionRepository()
        self._item_repository = item_repository or MarketSnapshotItemRepository()
        self._dataset_repository = dataset_repository or MarketDatasetRepository()
        self._quality_repository = quality_repository or MarketDataQualityRepository()
        self._feature_repository = feature_repository or MarketRegimeFeatureRepository()
        self._artifact_root = Path(artifact_root).expanduser().resolve() if artifact_root is not None else resolve_project_path("data/processed/market_regime_features")

    def _error(
        self,
        *,
        status: str,
        error_type: str,
        message: str,
        detail: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ServiceResult:
        """构造结构化错误结果。"""
        return ServiceResult(
            status=status,  # type: ignore[arg-type]
            message=message,
            payload={
                "error": {
                    "type": error_type,
                    "message": message,
                    "detail": detail,
                    "metadata": metadata or {},
                }
            },
        )

    def _snapshot_summary(self, feature: MarketRegimeFeature) -> dict[str, Any]:
        """构造 feature 列表项。"""
        return feature.to_dict()

    def _section_payload(self, sections: dict[str, Any], section_id: str) -> dict[str, Any]:
        """返回指定 section 的 payload。"""
        section = sections.get(section_id)
        payload = getattr(section, "payload_json", None) if section is not None else None
        return payload if isinstance(payload, dict) else {}

    def _market_state_payload(self, sections: dict[str, Any]) -> dict[str, Any]:
        """返回 market_state 的内部 payload。"""
        market_state_section = self._section_payload(sections, "market_state")
        payload = market_state_section.get("market_state")
        return payload if isinstance(payload, dict) else {}

    def _build_feature_entry(
        self,
        *,
        key: str,
        value: Any,
        source_section: str | None,
        confidence: float,
        missing_reason: str | None = None,
    ) -> dict[str, Any]:
        """构造单个 feature 条目。"""
        return {
            "feature_key": key,
            "value": value,
            "source_section": source_section,
            "confidence": confidence,
            "missing_reason": missing_reason,
        }

    def _band_turnover(self, value: Any) -> str | None:
        """把成交额/换手强度粗分成等级。"""
        number = _first_number(value)
        if number is None:
            return _first_text(value)
        if number >= 20000:
            return "high"
        if number >= 10000:
            return "mid"
        return "low"

    async def _full_market_ohlcv_metrics(self, session: AsyncSession, *, trade_date: date, lookback_days: int = 90) -> dict[str, Any]:
        """基于全市场 OHLCV 计算风险压力特征。"""
        lookback = trade_date - timedelta(days=lookback_days)
        stmt = (
            select(OHLCVBar)
            .where(OHLCVBar.trade_date >= lookback)
            .where(OHLCVBar.trade_date <= trade_date)
            .order_by(OHLCVBar.symbol.asc(), OHLCVBar.trade_date.asc())
        )
        result = await session.scalars(stmt)
        rows = list(result.all())
        if not rows:
            return {}

        rows_by_symbol: dict[str, list[OHLCVBar]] = defaultdict(list)
        for row in rows:
            rows_by_symbol[row.symbol].append(row)

        def as_float(value: Any) -> float | None:
            if isinstance(value, bool):
                return None
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                try:
                    return float(value.replace(",", ""))
                except ValueError:
                    return None
            return None

        def pct_change(current: float | None, previous: float | None) -> float | None:
            if current is None or previous in {None, 0}:
                return None
            return current / previous - 1.0

        gap_down_count = 0
        extreme_drop_count = 0
        transition_count = 0
        symbol_count = len(rows_by_symbol)
        for symbol_rows in rows_by_symbol.values():
            prev_close: float | None = None
            for bar in symbol_rows:
                close = as_float(bar.close)
                open_value = as_float(bar.open)
                if prev_close is not None:
                    transition_count += 1
                    if open_value is not None and open_value < prev_close:
                        gap_down_count += 1
                    if close is not None:
                        daily_return = pct_change(close, prev_close)
                        if daily_return is not None and daily_return <= -0.05:
                            extreme_drop_count += 1
                if close is not None:
                    prev_close = close

        gap_down_rate_full_market = round(gap_down_count / transition_count, 4) if transition_count else None
        return {
            "full_market_ohlcv_window": {
                "start_date": lookback.isoformat(),
                "end_date": trade_date.isoformat(),
                "lookback_days": lookback_days,
                "symbol_count": symbol_count,
                "bar_count": len(rows),
                "transition_count": transition_count,
                "gap_down_count": gap_down_count,
                "extreme_drop_count": extreme_drop_count,
            },
            "gap_down_rate_full_market": gap_down_rate_full_market,
            "extreme_drop_count_full_market": extreme_drop_count,
        }

    def _extract_feature_map(
        self,
        *,
        sections: dict[str, Any],
    ) -> tuple[dict[str, Any], list[str], list[str], int, int]:
        """从 sections 中提取 feature payload。"""
        overview = self._section_payload(sections, "overview")
        limit_up_down = self._section_payload(sections, "limit_up_down")
        sector_activity = self._section_payload(sections, "sector_activity")
        hot_topics = self._section_payload(sections, "hot_topics")
        topic_constituents = self._section_payload(sections, "topic_constituents")
        strong_symbols = self._section_payload(sections, "strong_symbols")
        market_sentiment = self._section_payload(sections, "market_sentiment")
        market_index = self._section_payload(sections, "market_index")
        sharp_withdrawal = self._section_payload(sections, "sharp_withdrawal")
        sector_ranking = self._section_payload(sections, "sector_ranking")
        ohlcv = self._section_payload(sections, "ohlcv")
        market_state = self._market_state_payload(sections)

        features: dict[str, Any] = {}
        warnings: list[str] = []
        source_sections: list[str] = []
        available = 0
        missing = 0

        def add_feature(key: str, value: Any, source_section: str | None, confidence: float, missing_reason: str | None = None) -> None:
            nonlocal available, missing
            features[key] = self._build_feature_entry(
                key=key,
                value=value,
                source_section=source_section,
                confidence=confidence,
                missing_reason=missing_reason,
            )
            if source_section and source_section not in source_sections:
                source_sections.append(source_section)
            if value is None:
                missing += 1
                if missing_reason:
                    warnings.append(f"{key}: {missing_reason}")
            else:
                available += 1

        def ohlcv_rows() -> list[dict[str, Any]]:
            rows = ohlcv.get("items") if isinstance(ohlcv, dict) else []
            if not isinstance(rows, list):
                return []
            normalized_rows: list[dict[str, Any]] = []
            for row in rows:
                if isinstance(row, dict):
                    normalized_rows.append(row)
            normalized_rows.sort(key=lambda row: str(row.get("time") or ""))
            return normalized_rows

        def as_float(value: Any) -> float | None:
            if isinstance(value, bool):
                return None
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                try:
                    return float(value.replace(",", ""))
                except ValueError:
                    return None
            return None

        def rolling_mean(values: list[float], window: int) -> float | None:
            if len(values) < window or window <= 0:
                return None
            return sum(values[-window:]) / float(window)

        def pct_change(current: float | None, previous: float | None) -> float | None:
            if current is None or previous in {None, 0}:
                return None
            return current / previous - 1.0

        def mean(values: list[float]) -> float | None:
            if not values:
                return None
            return sum(values) / float(len(values))

        def build_ohlcv_metrics() -> dict[str, Any]:
            rows = ohlcv_rows()
            if not rows:
                return {}

            closes: list[float] = []
            volumes: list[float] = []
            turnovers: list[float] = []
            gap_down_count = 0
            extreme_drop_count = 0
            prev_close: float | None = None

            for row in rows:
                close = as_float(row.get("close"))
                open_value = as_float(row.get("open"))
                volume = as_float(row.get("volume"))
                turnover = as_float(row.get("turnover"))
                if close is not None:
                    closes.append(close)
                if volume is not None:
                    volumes.append(volume)
                if turnover is not None:
                    turnovers.append(turnover)
                if prev_close is not None:
                    if open_value is not None and open_value < prev_close:
                        gap_down_count += 1
                    if close is not None:
                        daily_return = pct_change(close, prev_close)
                        if daily_return is not None and daily_return <= -0.05:
                            extreme_drop_count += 1
                if close is not None:
                    prev_close = close

            latest_close = closes[-1] if closes else None
            latest_volume = volumes[-1] if volumes else None
            latest_turnover = turnovers[-1] if turnovers else latest_volume
            previous_volume = volumes[:-1] if len(volumes) > 1 else volumes
            previous_turnover = turnovers[:-1] if len(turnovers) > 1 else turnovers
            avg_volume_20 = mean(previous_volume[-20:])
            avg_turnover_20 = mean(previous_turnover[-20:])
            ma20 = rolling_mean(closes, 20)
            ma60 = rolling_mean(closes, 60)

            benchmark_window = {
                "symbol": ohlcv.get("symbol"),
                "start_date": ohlcv.get("start_date"),
                "end_date": ohlcv.get("end_date"),
                "count": len(rows),
                "items": rows[-60:],
            }

            metrics = {
                "benchmark_ohlcv_window": benchmark_window,
                "ret_5d": pct_change(latest_close, closes[-6]) if len(closes) >= 6 else None,
                "ret_20d": pct_change(latest_close, closes[-21]) if len(closes) >= 21 else None,
                "ma20_gap": pct_change(latest_close, ma20),
                "ma60_gap": pct_change(latest_close, ma60),
                "vol_spike": pct_change(latest_volume, avg_volume_20) if latest_volume is not None else None,
                "turnover_ratio": pct_change(latest_turnover, avg_turnover_20) if latest_turnover is not None else None,
                "gap_down_rate": round(gap_down_count / max(len(rows) - 1, 1), 4) if len(rows) > 1 else None,
                "extreme_drop_count": extreme_drop_count,
            }
            if isinstance(metrics["vol_spike"], float):
                metrics["vol_spike"] = round(metrics["vol_spike"], 4)
            if isinstance(metrics["turnover_ratio"], float):
                metrics["turnover_ratio"] = round(metrics["turnover_ratio"], 4)
            if isinstance(metrics["ma20_gap"], float):
                metrics["ma20_gap"] = round(metrics["ma20_gap"], 4)
            if isinstance(metrics["ma60_gap"], float):
                metrics["ma60_gap"] = round(metrics["ma60_gap"], 4)
            if isinstance(metrics["ret_5d"], float):
                metrics["ret_5d"] = round(metrics["ret_5d"], 4)
            if isinstance(metrics["ret_20d"], float):
                metrics["ret_20d"] = round(metrics["ret_20d"], 4)
            return metrics

        def build_theme_concentration() -> dict[str, Any] | None:
            topics = hot_topics.get("topics", [])
            topic_scores: list[float] = []
            if isinstance(topics, list):
                for topic in topics:
                    if not isinstance(topic, dict):
                        continue
                    score = as_float(topic.get("score"))
                    if score is not None:
                        topic_scores.append(score)
            sector_entries = sector_ranking.get("sectors", [])
            sector_counts: list[int] = []
            if isinstance(sector_entries, list):
                for sector in sector_entries:
                    if not isinstance(sector, dict):
                        continue
                    count = _first_number(sector.get("stock_count"))
                    if count is not None:
                        sector_counts.append(count)
            if not topic_scores and not sector_counts and not strong_symbol_count and not constituent_count:
                return None
            topic_scores_sorted = sorted(topic_scores, reverse=True)
            total_topic_score = sum(topic_scores_sorted)
            top3_topic_share = round(sum(topic_scores_sorted[:3]) / total_topic_score, 4) if total_topic_score else None
            total_sector_count = sum(sector_counts)
            top_sector_share = round(max(sector_counts) / total_sector_count, 4) if total_sector_count else None
            return {
                "topic_count": topic_count,
                "constituent_count": constituent_count,
                "strong_symbol_count": strong_symbol_count,
                "sector_count": len(sector_counts),
                "top_topic_share": top3_topic_share,
                "top_sector_share": top_sector_share,
            }

        ohlcv_metrics = build_ohlcv_metrics()
        if ohlcv_metrics:
            add_feature(
                "benchmark_ohlcv_window",
                ohlcv_metrics["benchmark_ohlcv_window"],
                "ohlcv",
                0.95,
            )
            trend = {
                "benchmark_symbol": ohlcv_metrics["benchmark_ohlcv_window"].get("symbol"),
                "start_date": ohlcv_metrics["benchmark_ohlcv_window"].get("start_date"),
                "end_date": ohlcv_metrics["benchmark_ohlcv_window"].get("end_date"),
                "count": ohlcv_metrics["benchmark_ohlcv_window"].get("count"),
                "ret_5d": ohlcv_metrics["ret_5d"],
                "ret_20d": ohlcv_metrics["ret_20d"],
                "ma20_gap": ohlcv_metrics["ma20_gap"],
                "ma60_gap": ohlcv_metrics["ma60_gap"],
            }
            add_feature("trend", trend, "ohlcv", 0.95)
            add_feature("ret_5d", ohlcv_metrics["ret_5d"], "ohlcv", 0.95)
            add_feature("ret_20d", ohlcv_metrics["ret_20d"], "ohlcv", 0.95)
            add_feature("ma20_gap", ohlcv_metrics["ma20_gap"], "ohlcv", 0.95)
            add_feature("ma60_gap", ohlcv_metrics["ma60_gap"], "ohlcv", 0.95)
            add_feature("vol_spike", ohlcv_metrics["vol_spike"], "ohlcv", 0.9)
            add_feature("turnover_ratio", ohlcv_metrics["turnover_ratio"], "ohlcv", 0.9)
            add_feature("gap_down_rate", ohlcv_metrics["gap_down_rate"], "ohlcv", 0.8)
            add_feature("extreme_drop_count", ohlcv_metrics["extreme_drop_count"], "ohlcv", 0.8)
        else:
            trend = market_state.get("regime") or overview.get("trend") or _first_text(overview.get("indices", {}).get("trend") if isinstance(overview.get("indices"), dict) else None)
            if trend is None:
                add_feature("trend", None, None, 0.0, "missing market_state.regime or overview trend")
            else:
                add_feature("trend", trend, "market_state" if market_state.get("regime") else "overview", 0.95 if market_state.get("regime") else 0.7)

        sentiment_payload = overview.get("sentiment")
        sentiment = None
        sentiment_confidence = 0.0
        sentiment_source = None
        if isinstance(sentiment_payload, dict):
            sentiment = sentiment_payload.get("label") or sentiment_payload.get("value") or sentiment_payload.get("score")
            sentiment_confidence = 0.9 if sentiment_payload.get("label") else 0.75
            sentiment_source = "overview"
        elif sentiment_payload is not None:
            sentiment = sentiment_payload
            sentiment_confidence = 0.8
            sentiment_source = "overview"
        elif market_state.get("features", {}).get("sentiment") is not None:
            sentiment = market_state["features"].get("sentiment")
            sentiment_confidence = 0.8
            sentiment_source = "market_state"
        if sentiment is None:
            add_feature("sentiment", None, None, 0.0, "missing overview.sentiment")
        else:
            add_feature("sentiment", sentiment, sentiment_source, sentiment_confidence)

        liquidity = market_state.get("liquidity")
        liquidity_source = "market_state" if liquidity is not None else None
        liquidity_confidence = 0.95 if liquidity is not None else 0.0
        if liquidity is None and isinstance(overview.get("capacity"), dict):
            capacity = overview["capacity"]
            liquidity = capacity.get("turnover_level") or self._band_turnover(capacity.get("last"))
            if liquidity is not None:
                liquidity_source = "overview"
                liquidity_confidence = 0.8
        if liquidity is None:
            add_feature("liquidity", None, None, 0.0, "missing market_state.liquidity or overview.capacity")
        else:
            add_feature("liquidity", liquidity, liquidity_source, liquidity_confidence)

        volatility = market_state.get("volatility")
        volatility_source = "market_state" if volatility is not None else None
        volatility_confidence = 0.95 if volatility is not None else 0.0
        if volatility is None:
            volatility = overview.get("volatility") or _first_text(overview.get("indices", {}).get("volatility") if isinstance(overview.get("indices"), dict) else None)
            if volatility is None and ohlcv_metrics.get("vol_spike") is not None:
                vol_spike_value = ohlcv_metrics["vol_spike"]
                if isinstance(vol_spike_value, (int, float)):
                    volatility = "high" if vol_spike_value >= 0.25 else "mid" if vol_spike_value >= 0.1 else "low"
                    volatility_source = "ohlcv"
                    volatility_confidence = 0.75
            if volatility is not None and volatility_source is None:
                volatility_source = "overview"
                volatility_confidence = 0.7
        if volatility is None:
            add_feature("volatility", None, None, 0.0, "missing market_state.volatility or overview volatility")
        else:
            add_feature("volatility", volatility, volatility_source, volatility_confidence)

        sentiment_summary = market_sentiment.get("summary") if isinstance(market_sentiment.get("summary"), dict) else {}
        up_count = _first_number(sentiment_summary.get("up_count"))
        down_count = _first_number(sentiment_summary.get("down_count"))
        flat_count = _first_number(sentiment_summary.get("flat_count"))
        total_count = sum(value for value in (up_count, down_count, flat_count) if isinstance(value, int))
        if total_count > 0:
            breadth = {
                "up_count": up_count,
                "down_count": down_count,
                "flat_count": flat_count,
                "total": total_count,
                "up_ratio": round((up_count or 0) / total_count, 4),
                "down_ratio": round((down_count or 0) / total_count, 4),
            }
            add_feature("breadth", breadth, "market_sentiment", 0.95)
            add_feature("breadth_up_ratio", breadth["up_ratio"], "market_sentiment", 0.95)
            add_feature("breadth_down_ratio", breadth["down_ratio"], "market_sentiment", 0.95)
        else:
            breadth = market_state.get("breadth")
            breadth_source = "market_state" if breadth is not None else None
            breadth_confidence = 0.95 if breadth is not None else 0.0
            if breadth is None and isinstance(sector_activity, dict):
                if any(sector_activity.get(key) for key in ("board_strength", "industry_ranking", "weight_performance")):
                    breadth = "strong"
                    breadth_source = "sector_activity"
                    breadth_confidence = 0.65
            if breadth is None and isinstance(overview.get("indices"), dict):
                breadth = overview["indices"].get("breadth")
                if breadth is not None:
                    breadth_source = "overview"
                    breadth_confidence = 0.7
            if breadth is None:
                add_feature("breadth", None, None, 0.0, "missing market_state.breadth or market_sentiment")
                add_feature("breadth_up_ratio", None, None, 0.0, "missing market_sentiment.summary counts")
                add_feature("breadth_down_ratio", None, None, 0.0, "missing market_sentiment.summary counts")
            else:
                add_feature("breadth", breadth, breadth_source, breadth_confidence)
                if isinstance(breadth, dict):
                    add_feature("breadth_up_ratio", breadth.get("up_ratio"), breadth_source, breadth_confidence)
                    add_feature("breadth_down_ratio", breadth.get("down_ratio"), breadth_source, breadth_confidence)

        topic_count = len(hot_topics.get("topics", [])) if isinstance(hot_topics.get("topics"), list) else 0
        constituent_count = len(topic_constituents.get("constituents", [])) if isinstance(topic_constituents.get("constituents"), list) else 0
        strong_symbol_count = len(strong_symbols.get("symbols", [])) if isinstance(strong_symbols.get("symbols"), list) else 0
        if topic_count or constituent_count or strong_symbol_count:
            add_feature(
                "theme_strength",
                {
                    "topic_count": topic_count,
                    "constituent_count": constituent_count,
                    "strong_symbol_count": strong_symbol_count,
                },
                "hot_topics",
                0.8 if topic_count or constituent_count else 0.6,
            )
        else:
            add_feature("theme_strength", None, None, 0.0, "missing hot_topics / topic_constituents / strong_symbols")

        limit_up_value = (
            _first_number(limit_up_down.get("limit_up_counts", {}).get("info", {}).get("SJZT"))
            if isinstance(limit_up_down.get("limit_up_counts"), dict)
            else None
        )
        if limit_up_value is None:
            limit_up_value = _first_number(limit_up_down.get("limit_up_reason", {}).get("nums", {}).get("ZT")) if isinstance(limit_up_down.get("limit_up_reason"), dict) else None
        if limit_up_value is None and isinstance(limit_up_down.get("limit_up_info"), dict):
            info = limit_up_down["limit_up_info"].get("info")
            if isinstance(info, list):
                limit_up_value = len(info)
        if limit_up_value is None:
            add_feature("limit_up_count", None, None, 0.0, "missing limit_up_down counts")
        else:
            add_feature("limit_up_count", limit_up_value, "limit_up_down", 0.9)

        limit_down_value = (
            _first_number(limit_up_down.get("limit_up_counts", {}).get("info", {}).get("SJDT"))
            if isinstance(limit_up_down.get("limit_up_counts"), dict)
            else None
        )
        if limit_down_value is None:
            limit_down_value = _first_number(limit_up_down.get("limit_up_reason", {}).get("nums", {}).get("DT")) if isinstance(limit_up_down.get("limit_up_reason"), dict) else None
        if limit_down_value is None:
            add_feature("limit_down_count", None, None, 0.0, "missing limit_up_down counts")
        else:
            add_feature("limit_down_count", limit_down_value, "limit_up_down", 0.9)

        turnover_level = market_state.get("features", {}).get("turnover_level") if isinstance(market_state.get("features"), dict) else None
        turnover_source = "market_state" if turnover_level is not None else None
        turnover_confidence = 0.95 if turnover_level is not None else 0.0
        if turnover_level is None and isinstance(overview.get("capacity"), dict):
            capacity = overview["capacity"]
            turnover_level = capacity.get("turnover_level") or self._band_turnover(capacity.get("last"))
            if turnover_level is not None:
                turnover_source = "overview"
                turnover_confidence = 0.8
        if turnover_level is None and ohlcv_metrics.get("turnover_ratio") is not None:
            turnover_ratio = ohlcv_metrics["turnover_ratio"]
            if isinstance(turnover_ratio, (int, float)):
                turnover_level = "high" if turnover_ratio >= 0.15 else "mid" if turnover_ratio >= -0.05 else "low"
                turnover_source = "ohlcv"
                turnover_confidence = 0.7
        if turnover_level is None:
            add_feature("turnover_level", None, None, 0.0, "missing market_state.features.turnover_level or overview.capacity")
        else:
            add_feature("turnover_level", turnover_level, turnover_source, turnover_confidence)

        theme_concentration = build_theme_concentration()
        if theme_concentration is None:
            add_feature("theme_concentration", None, None, 0.0, "missing hot_topics / sector_ranking / strong_symbols")
        else:
            add_feature("theme_concentration", theme_concentration, "hot_topics", 0.8)

        if ohlcv_metrics:
            if isinstance(ohlcv_metrics.get("vol_spike"), (int, float)) and volatility is None:
                vol_spike_value = ohlcv_metrics["vol_spike"]
                if vol_spike_value >= 0.25:
                    volatility = "high"
                elif vol_spike_value >= 0.1:
                    volatility = "mid"
                else:
                    volatility = "low"
                volatility_source = "ohlcv"
                volatility_confidence = 0.75
            if isinstance(ohlcv_metrics.get("turnover_ratio"), (int, float)) and turnover_level is None:
                turnover_level = "high" if ohlcv_metrics["turnover_ratio"] >= 0.15 else "mid" if ohlcv_metrics["turnover_ratio"] >= -0.05 else "low"
                turnover_source = "ohlcv"
                turnover_confidence = 0.7

        return features, warnings, source_sections, available, missing

    def _artifact_path(self, *, trade_date: date, snapshot_id: str, feature_version: str) -> Path:
        """返回 feature artifact 路径。"""
        return self._artifact_root / trade_date.isoformat() / snapshot_id / f"{feature_version}.json"

    def _artifact_ref(self, artifact_path: Path) -> dict[str, Any]:
        """返回 artifact 的安全引用。"""
        try:
            relative = artifact_path.relative_to(self._artifact_root)
        except ValueError:
            relative = artifact_path.name
        return {
            "artifact_type": "market-regime-features-json",
            "artifact_root": str(self._artifact_root.name or "market_regime_features"),
            "relative_path": str(relative),
        }

    async def build_market_regime_features(
        self,
        *,
        snapshot_id: str,
        feature_version: str = DEFAULT_FEATURE_VERSION,
    ) -> ServiceResult:
        """基于指定 snapshot 生成 market_regime_features。"""
        async with self._session_factory() as session:
            snapshot = await self._snapshot_repository.get_by_snapshot_id(session, snapshot_id)
            if snapshot is None:
                return self._error(
                    status="error",
                    error_type="snapshot_not_found",
                    message="snapshot not found",
                    detail=snapshot_id,
                    metadata={"snapshot_id": snapshot_id},
                )

            sections = await self._section_repository.list_by_snapshot_id(session, snapshot_id)
            section_map = {section.section_id: section for section in sections}
            quality = await self._quality_repository.get_by_snapshot_id(session, snapshot_id)
            dataset = await self._dataset_repository.get_by_dataset_id(session, f"{snapshot_id}:dataset")
            items = await self._item_repository.list_by_snapshot_id(session, snapshot_id)

            feature_payload_json, warnings, source_sections, available_count, missing_count = self._extract_feature_map(sections=section_map)
            for entry in feature_payload_json.values():
                if isinstance(entry, dict) and entry.get("feature_version") is None:
                    entry["feature_version"] = feature_version
            if feature_version == FULL_MARKET_FEATURE_VERSION:
                full_market_metrics = await self._full_market_ohlcv_metrics(session, trade_date=snapshot.trade_date)
                if full_market_metrics:
                    feature_payload_json["full_market_ohlcv_window"] = self._build_feature_entry(
                        key="full_market_ohlcv_window",
                        value=full_market_metrics["full_market_ohlcv_window"],
                        source_section="ohlcv_full_market",
                        confidence=0.85,
                    )
                    feature_payload_json["gap_down_rate_full_market"] = self._build_feature_entry(
                        key="gap_down_rate_full_market",
                        value=full_market_metrics["gap_down_rate_full_market"],
                        source_section="ohlcv_full_market",
                        confidence=0.85,
                    )
                    feature_payload_json["extreme_drop_count_full_market"] = self._build_feature_entry(
                        key="extreme_drop_count_full_market",
                        value=full_market_metrics["extreme_drop_count_full_market"],
                        source_section="ohlcv_full_market",
                        confidence=0.85,
                    )
                    available_count += 3
                    if "ohlcv_full_market" not in source_sections:
                        source_sections.append("ohlcv_full_market")
                else:
                    for key in (
                        "full_market_ohlcv_window",
                        "gap_down_rate_full_market",
                        "extreme_drop_count_full_market",
                    ):
                        feature_payload_json[key] = self._build_feature_entry(
                            key=key,
                            value=None,
                            source_section=None,
                            confidence=0.0,
                            missing_reason="missing full-market ohlcv coverage",
                        )
                        missing_count += 1
                        warnings.append(f"{key}: missing full-market ohlcv coverage")
            for entry in feature_payload_json.values():
                if isinstance(entry, dict) and entry.get("feature_version") is None:
                    entry["feature_version"] = feature_version
            partial_count = sum(1 for entry in feature_payload_json.values() if entry["missing_reason"] is not None and entry["value"] is None)
            quality_status = "ok" if missing_count == 0 else "partial"

            summary_json = {
                "snapshot_id": snapshot.snapshot_id,
                "trade_date": snapshot.trade_date.isoformat() if snapshot.trade_date else None,
                "market": snapshot.market,
                "feature_version": feature_version,
                "quality_status": quality_status,
                "available_feature_count": available_count,
                "partial_feature_count": partial_count,
                "missing_feature_count": missing_count,
                "source_sections": source_sections,
                "section_count": len(sections),
                "item_count": len(items),
                "quality_report": quality.to_dict() if quality is not None else None,
                "dataset": dataset.to_dict() if dataset is not None else None,
                "warnings": warnings,
            }
            artifact_path = self._artifact_path(trade_date=snapshot.trade_date, snapshot_id=snapshot.snapshot_id, feature_version=feature_version)
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_payload = {
                "snapshot_id": snapshot.snapshot_id,
                "trade_date": snapshot.trade_date.isoformat() if snapshot.trade_date else None,
                "market": snapshot.market,
                "feature_version": feature_version,
                "quality_status": quality_status,
                "features": feature_payload_json,
                "summary": summary_json,
                "source_sections": source_sections,
                "warnings": warnings,
            }
            artifact_path.write_text(json.dumps(_to_plain(artifact_payload), ensure_ascii=False, indent=2), encoding="utf-8")

            feature = MarketRegimeFeature(
                snapshot_id=snapshot.snapshot_id,
                trade_date=snapshot.trade_date,
                market=snapshot.market,
                feature_version=feature_version,
                quality_status=quality_status,
                available_feature_count=available_count,
                partial_feature_count=partial_count,
                missing_feature_count=missing_count,
                feature_payload_json=feature_payload_json,
                summary_json=summary_json,
                storage_ref=self._artifact_ref(artifact_path),
            )
            dataset_record = MarketDataset(
                dataset_id=f"{snapshot.snapshot_id}:{feature_version}",
                dataset_type="market_regime_features",
                trade_date=snapshot.trade_date,
                market=snapshot.market,
                source="market-regime-feature",
                storage_ref={
                    "snapshot_id": snapshot.snapshot_id,
                    "feature_version": feature_version,
                    "artifact_type": "market-regime-features-json",
                },
                snapshot_id=snapshot.snapshot_id,
                profile_id=getattr(snapshot, "profile_id", None),
                quality_status=quality_status,
            )

            saved = feature
            db_error: str | None = None
            try:
                saved = await self._feature_repository.upsert_feature(session, feature)
                await self._dataset_repository.upsert_dataset(session, dataset_record)
                await session.commit()
            except Exception as exc:  # noqa: BLE001
                db_error = str(exc)
                warnings.append(f"database persistence failed: {exc}")

        payload = {
            "feature": saved.to_dict(),
            "feature_payload_json": saved.feature_payload_json,
            "summary_json": saved.summary_json,
            "summary": saved.summary_json,
            "artifact_ref": saved.storage_ref,
            "artifact_path": saved.storage_ref.get("relative_path"),
            "dataset_id": dataset_record.dataset_id,
            "warnings": warnings,
        }
        status = "partial" if db_error is not None else quality_status
        message = "market regime features written" if db_error is None else "market regime features written with database warning"
        return ServiceResult(status=status, message=message, payload=payload, warnings=warnings)

    async def get_feature_detail(self, snapshot_id: str, feature_version: str | None = None) -> ServiceResult:
        """按 snapshot_id / feature_version 查询 feature 详情。"""
        version = feature_version or DEFAULT_FEATURE_VERSION
        async with self._session_factory() as session:
            snapshot = await self._snapshot_repository.get_by_snapshot_id(session, snapshot_id)
            if snapshot is None:
                return self._error(
                    status="error",
                    error_type="snapshot_not_found",
                    message="snapshot not found",
                    detail=snapshot_id,
                    metadata={"snapshot_id": snapshot_id},
                )

            feature = None
            feature = await self._feature_repository.get_by_snapshot_and_version(session, snapshot_id, version)

        if feature is None:
            return self._error(
                status="error",
                error_type="feature_not_found",
                message="market regime feature not found",
                detail=snapshot_id,
                metadata={"snapshot_id": snapshot_id, "feature_version": version},
            )

        payload = {
            "feature": feature.to_dict(),
            "feature_payload_json": feature.feature_payload_json,
            "summary_json": feature.summary_json,
            "summary": feature.summary_json,
            "warnings": feature.summary_json.get("warnings", []),
        }
        return ServiceResult(status=feature.quality_status, message="market regime feature found", payload=payload, warnings=payload["warnings"])

    async def list_features(
        self,
        *,
        trade_date: date | str | None = None,
        snapshot_id: str | None = None,
        market: str | None = None,
        feature_version: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ServiceResult:
        """按条件查询 market regime features。"""
        if limit < 1 or offset < 0:
            return self._error(
                status="error",
                error_type="invalid_query",
                message="invalid pagination",
                detail="limit must be >= 1 and offset must be >= 0",
                metadata={"limit": limit, "offset": offset},
            )

        try:
            normalized_trade_date = _normalize_date(trade_date)
        except ValueError as exc:
            return self._error(
                status="error",
                error_type="invalid_query",
                message="invalid trade_date",
                detail=str(exc),
                metadata={"trade_date": trade_date},
            )

        async with self._session_factory() as session:
            total = await self._feature_repository.count_features(
                session,
                trade_date=normalized_trade_date,
                snapshot_id=snapshot_id,
                market=market,
                feature_version=feature_version,
            )
            features = await self._feature_repository.list_features(
                session,
                trade_date=normalized_trade_date,
                snapshot_id=snapshot_id,
                market=market,
                feature_version=feature_version,
                limit=limit,
                offset=offset,
            )

        if not features:
            return self._error(
                status="error",
                error_type="empty_data",
                message="market regime feature not found",
                detail="no feature matches query",
                metadata={
                    "trade_date": normalized_trade_date.isoformat() if normalized_trade_date else None,
                    "snapshot_id": snapshot_id,
                    "market": market,
                    "feature_version": feature_version,
                },
            )

        payload = {
            "filters": {
                "trade_date": normalized_trade_date.isoformat() if normalized_trade_date else None,
                "snapshot_id": snapshot_id,
                "market": market,
                "feature_version": feature_version,
            },
            "page": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "count": len(features),
            },
            "items": [feature.to_dict() for feature in features],
        }
        return ServiceResult(status="ok", message="market regime features found", payload=payload)
