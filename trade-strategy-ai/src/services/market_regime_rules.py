from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import date, datetime
from typing import Any

from src.models.market_regime_record import (
    RegimeEvidenceRecord,
    RegimeFeatureRecord,
    RegimeLabelRecord,
)


def _to_plain(value: Any) -> Any:
    """把 dataclass / 容器值转成可序列化结构。"""
    if hasattr(value, "model_dump"):
        return _to_plain(value.model_dump())
    if is_dataclass(value):
        return {k: _to_plain(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


@dataclass(frozen=True)
class MarketRegimeEvaluation:
    """Market Regime 的最终判定结果。"""

    regime_id: str | None
    snapshot_id: str
    trade_date: date
    market: str
    regime_version: str
    source_feature_version: str
    primary_label: str
    labels: list[RegimeLabelRecord] = field(default_factory=list)
    features: list[RegimeFeatureRecord] = field(default_factory=list)
    confidence: float = 0.0
    quality_status: str = "partial"
    missing_reason: str | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """返回 JSON 兼容字典。"""
        return _to_plain(self)


def _extract_feature_entry(features: dict[str, Any], key: str) -> dict[str, Any]:
    """从 feature payload 中提取单个 feature 条目。"""
    value = features.get(key)
    if isinstance(value, dict):
        return value
    return {"feature_key": key, "value": value, "confidence": 0.0, "missing_reason": None}


def _feature_value(entry: dict[str, Any]) -> Any:
    """返回 feature 的有效值。"""
    return entry.get("value") if isinstance(entry, dict) else None


def _feature_confidence(entry: dict[str, Any]) -> float:
    """返回 feature 的置信度。"""
    value = entry.get("confidence") if isinstance(entry, dict) else None
    return float(value) if isinstance(value, (int, float)) else 0.0


def _feature_source_section(entry: dict[str, Any], fallback: str = "unknown") -> str:
    """返回 feature 来源 section。"""
    value = entry.get("source_section") if isinstance(entry, dict) else None
    return str(value) if value else fallback


def _feature_source_field(entry: dict[str, Any]) -> str | None:
    """返回 feature 来源字段。"""
    value = entry.get("source_field") if isinstance(entry, dict) else None
    return str(value) if value else None


def _feature_missing_reason(entry: dict[str, Any]) -> str | None:
    """返回 feature 缺失原因。"""
    value = entry.get("missing_reason") if isinstance(entry, dict) else None
    return str(value) if value else None


def _is_missing_feature_value(value: Any) -> bool:
    """判断 feature 值是否缺失。"""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == "" or value == "unknown"
    return False


def _build_feature_record(key: str, entry: dict[str, Any]) -> RegimeFeatureRecord:
    """把 feature payload 转成结构化 record。"""
    return RegimeFeatureRecord(
        feature_key=key,
        raw_value=_feature_value(entry),
        normalized_value=entry.get("normalized_value") if isinstance(entry, dict) else None,
        source_section=_feature_source_section(entry),
        source_field=_feature_source_field(entry),
        source_version=str(entry.get("source_version") or entry.get("feature_version") or "market-regime-features-v1") if isinstance(entry, dict) else "market-regime-features-v1",
        confidence=_feature_confidence(entry),
        weight=float(entry.get("weight") or 1.0) if isinstance(entry, dict) else 1.0,
        missing_reason=_feature_missing_reason(entry),
    )


def _trend_score(value: Any) -> float:
    """把趋势特征转换成方向分数。"""
    if isinstance(value, str):
        mapping = {
            "strong_bull": 3.0,
            "weak_bull": 2.0,
            "trend_up": 2.0,
            "bull": 2.0,
            "range": 0.0,
            "range_bound": 0.0,
            "weak_bear": -2.0,
            "trend_down": -2.0,
            "bear": -2.0,
            "panic": -4.0,
        }
        return mapping.get(value, 0.0)
    if isinstance(value, dict):
        score = 0.0
        ret_20d = value.get("ret_20d")
        ret_5d = value.get("ret_5d")
        ma20_gap = value.get("ma20_gap")
        ma60_gap = value.get("ma60_gap")
        if isinstance(ret_20d, (int, float)):
            score += 2.0 if ret_20d >= 0.06 else 1.0 if ret_20d > 0 else -2.0 if ret_20d <= -0.06 else -1.0
        if isinstance(ret_5d, (int, float)):
            score += 1.0 if ret_5d > 0 else -1.0
        if isinstance(ma20_gap, (int, float)):
            score += 1.0 if ma20_gap > 0 else -1.0
        if isinstance(ma60_gap, (int, float)):
            score += 1.0 if ma60_gap > 0 else -1.0
        return score
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def _breadth_score(value: Any) -> float:
    """把广度特征转换成分数。"""
    if isinstance(value, str):
        return {
            "strong": 2.0,
            "weak": -2.0,
            "neutral": 0.0,
        }.get(value, 0.0)
    if isinstance(value, dict):
        up_ratio = value.get("up_ratio")
        down_ratio = value.get("down_ratio")
        score = 0.0
        if isinstance(up_ratio, (int, float)):
            score += 2.0 if up_ratio >= 0.6 else 1.0 if up_ratio >= 0.55 else -1.0 if up_ratio <= 0.45 else 0.0
        if isinstance(down_ratio, (int, float)):
            score += -2.0 if down_ratio >= 0.6 else -1.0 if down_ratio >= 0.55 else 1.0 if down_ratio <= 0.45 else 0.0
        return score
    return 0.0


def _volatility_score(value: Any) -> float:
    """把波动特征转换成风险分数。"""
    if isinstance(value, str):
        return {
            "low": 0.5,
            "mid": 0.0,
            "high": -1.5,
            "unknown": 0.0,
        }.get(value, 0.0)
    if isinstance(value, (int, float)):
        return -1.0 if float(value) > 0.03 else 0.0
    return 0.0


def _liquidity_score(value: Any) -> float:
    """把流动性特征转换成分数。"""
    if isinstance(value, str):
        return {
            "good": 1.0,
            "mid": 0.0,
            "bad": -1.5,
            "high": 1.0,
            "low": -1.0,
            "unknown": 0.0,
        }.get(value, 0.0)
    if isinstance(value, dict):
        level = value.get("level") or value.get("turnover_level")
        if isinstance(level, str):
            return _liquidity_score(level)
    return 0.0


def _turnover_score(value: Any) -> float:
    """把换手特征转换成分数。"""
    if isinstance(value, str):
        return {
            "high": 0.8,
            "mid": 0.0,
            "low": -1.0,
        }.get(value, 0.0)
    if isinstance(value, dict):
        ratio = value.get("turnover_ratio")
        if isinstance(ratio, (int, float)):
            return 0.8 if ratio >= 1.1 else 0.0 if ratio >= 0.8 else -0.8
    return 0.0


def _limit_down_score(value: Any) -> float:
    """把跌停特征转换成风险分数。"""
    if isinstance(value, (int, float)):
        if float(value) >= 10:
            return -3.0
        if float(value) >= 5:
            return -1.5
    if isinstance(value, dict):
        count = value.get("count") or value.get("limit_down_count")
        if isinstance(count, (int, float)):
            return _limit_down_score(count)
    return 0.0


def _theme_hot(value: Any) -> bool:
    """判断是否命中 theme_hot。"""
    if isinstance(value, str):
        return value not in {"", "unknown", "low"}
    if isinstance(value, dict):
        topic_count = value.get("topic_count")
        constituent_count = value.get("constituent_count")
        strong_symbol_count = value.get("strong_symbol_count")
        if isinstance(topic_count, (int, float)) and topic_count >= 3:
            return True
        if isinstance(constituent_count, (int, float)) and constituent_count >= 8:
            return True
        if isinstance(strong_symbol_count, (int, float)) and strong_symbol_count >= 5:
            return True
    return False


def _low_liquidity(value: Any) -> bool:
    """判断是否命中 low_liquidity。"""
    if isinstance(value, str):
        return value in {"low", "bad"}
    if isinstance(value, dict):
        level = value.get("level") or value.get("turnover_level")
        turnover_ratio = value.get("turnover_ratio")
        if isinstance(level, str) and level in {"low", "bad"}:
            return True
        if isinstance(turnover_ratio, (int, float)) and turnover_ratio < 0.8:
            return True
    return False


def _build_label(
    *,
    label: str,
    label_type: str,
    score: float,
    confidence: float,
    status: str,
    evidence: list[RegimeEvidenceRecord],
    reason: str,
) -> RegimeLabelRecord:
    """构造标签 record。"""
    return RegimeLabelRecord(
        label=label,
        label_type=label_type,
        score=score,
        confidence=confidence,
        status=status,
        evidence=evidence,
        reason=reason,
    )


def score_market_regime(
    features: dict[str, Any],
    *,
    regime_version: str,
    snapshot_id: str | None = None,
    trade_date: date | None = None,
    market: str = "CN",
    source_feature_version: str | None = None,
) -> MarketRegimeEvaluation:
    """根据 market_regime_features 计算最终 Market Regime。"""
    feature_keys = ("trend", "breadth", "volatility", "liquidity", "turnover_level", "theme_strength", "limit_up_count", "limit_down_count")
    feature_records = [_build_feature_record(key, _extract_feature_entry(features, key)) for key in feature_keys if key in features]
    if not feature_records:
        feature_records = []

    trend_entry = _extract_feature_entry(features, "trend")
    breadth_entry = _extract_feature_entry(features, "breadth")
    volatility_entry = _extract_feature_entry(features, "volatility")
    liquidity_entry = _extract_feature_entry(features, "liquidity")
    turnover_entry = _extract_feature_entry(features, "turnover_level")
    theme_entry = _extract_feature_entry(features, "theme_strength")
    limit_up_entry = _extract_feature_entry(features, "limit_up_count")
    limit_down_entry = _extract_feature_entry(features, "limit_down_count")

    trend_score = _trend_score(_feature_value(trend_entry))
    breadth_score = _breadth_score(_feature_value(breadth_entry))
    volatility_score = _volatility_score(_feature_value(volatility_entry))
    liquidity_score = _liquidity_score(_feature_value(liquidity_entry))
    turnover_score = _turnover_score(_feature_value(turnover_entry))
    limit_up_score = 0.5 if isinstance(_feature_value(limit_up_entry), (int, float)) and float(_feature_value(limit_up_entry)) >= 5 else 0.0
    limit_down_score = _limit_down_score(_feature_value(limit_down_entry))

    total_score = trend_score + breadth_score + volatility_score + liquidity_score + turnover_score + limit_up_score + limit_down_score

    primary_label = "range"
    if total_score >= 4.0:
        primary_label = "strong_bull"
    elif total_score >= 2.0:
        primary_label = "weak_bull"
    elif total_score <= -5.0:
        primary_label = "panic"
    elif total_score <= -2.0:
        primary_label = "weak_bear"

    trend_conf = _feature_confidence(trend_entry)
    breadth_conf = _feature_confidence(breadth_entry)
    volatility_conf = _feature_confidence(volatility_entry)
    liquidity_conf = _feature_confidence(liquidity_entry)
    turnout_conf = _feature_confidence(turnover_entry)
    key_confidences = [c for c in (trend_conf, breadth_conf, volatility_conf, liquidity_conf, turnout_conf) if c > 0]

    coverage = len(key_confidences) / 5 if key_confidences else 0.0
    certainty = min(1.0, max(0.0, (abs(total_score) / 6.0) + (sum(key_confidences) / len(key_confidences) if key_confidences else 0.0) / 2))
    confidence = round(min(1.0, max(0.0, (coverage * 0.45) + (certainty * 0.55))), 4)

    labels: list[RegimeLabelRecord] = []
    labels.append(
        _build_label(
            label=primary_label,
            label_type="primary",
            score=round(total_score, 4),
            confidence=confidence,
            status="active" if confidence >= 0.55 else "low_confidence",
            evidence=[
                RegimeEvidenceRecord(feature_key="trend", feature_value=_feature_value(trend_entry), source_section=_feature_source_section(trend_entry), source_field=_feature_source_field(trend_entry), contribution=trend_score, note="趋势分数"),
                RegimeEvidenceRecord(feature_key="breadth", feature_value=_feature_value(breadth_entry), source_section=_feature_source_section(breadth_entry), source_field=_feature_source_field(breadth_entry), contribution=breadth_score, note="广度分数"),
                RegimeEvidenceRecord(feature_key="volatility", feature_value=_feature_value(volatility_entry), source_section=_feature_source_section(volatility_entry), source_field=_feature_source_field(volatility_entry), contribution=volatility_score, note="波动修正"),
                RegimeEvidenceRecord(feature_key="liquidity", feature_value=_feature_value(liquidity_entry), source_section=_feature_source_section(liquidity_entry), source_field=_feature_source_field(liquidity_entry), contribution=liquidity_score, note="流动性修正"),
            ],
            reason=f"combined_score={total_score:.2f}",
        )
    )

    if _theme_hot(_feature_value(theme_entry)):
        labels.append(
            _build_label(
                label="theme_hot",
                label_type="structural",
                score=1.0,
                confidence=max(_feature_confidence(theme_entry), 0.6),
                status="active",
                evidence=[
                    RegimeEvidenceRecord(
                        feature_key="theme_strength",
                        feature_value=_feature_value(theme_entry),
                        source_section=_feature_source_section(theme_entry),
                        source_field=_feature_source_field(theme_entry),
                        contribution=1.0,
                        note="热点集中度较高",
                    )
                ],
                reason="hot_topics / strong_symbols indicate concentrated theme activity",
            )
        )

    if _low_liquidity(_feature_value(liquidity_entry)) or _low_liquidity(_feature_value(turnover_entry)):
        labels.append(
            _build_label(
                label="low_liquidity",
                label_type="structural",
                score=-1.0,
                confidence=max(_feature_confidence(liquidity_entry), _feature_confidence(turnover_entry), 0.6),
                status="active",
                evidence=[
                    RegimeEvidenceRecord(
                        feature_key="liquidity",
                        feature_value=_feature_value(liquidity_entry),
                        source_section=_feature_source_section(liquidity_entry),
                        source_field=_feature_source_field(liquidity_entry),
                        contribution=-1.0,
                        note="流动性偏弱",
                    ),
                    RegimeEvidenceRecord(
                        feature_key="turnover_level",
                        feature_value=_feature_value(turnover_entry),
                        source_section=_feature_source_section(turnover_entry),
                        source_field=_feature_source_field(turnover_entry),
                        contribution=-0.5,
                        note="换手水平偏弱",
                    ),
                ],
                reason="liquidity or turnover is below normal",
            )
        )

    missing_features = [entry for entry in (trend_entry, breadth_entry, volatility_entry, liquidity_entry, turnover_entry) if _is_missing_feature_value(_feature_value(entry))]
    quality_status = "ok"
    missing_reason = None
    if missing_features:
        quality_status = "partial"
        missing_reason = "missing critical features: " + ", ".join(sorted({str(entry.get("feature_key") or "unknown") for entry in missing_features}))
    if confidence < 0.55:
        quality_status = "low_confidence" if quality_status == "ok" else quality_status
        if missing_reason is None:
            missing_reason = "insufficient signal confidence"

    if primary_label == "panic":
        quality_status = "low_confidence" if confidence < 0.7 else quality_status

    if source_feature_version is None:
        source_candidates = [str(entry.get("source_version")) for entry in (trend_entry, breadth_entry, volatility_entry, liquidity_entry, turnover_entry, theme_entry, limit_up_entry, limit_down_entry) if isinstance(entry, dict) and entry.get("source_version")]
        source_feature_version = source_candidates[0] if source_candidates else "market-regime-features-v1"

    if trade_date is None:
        trade_date = date.today()

    regime_id = f"{snapshot_id or 'snapshot-unknown'}:{regime_version}"

    return MarketRegimeEvaluation(
        regime_id=regime_id,
        snapshot_id=snapshot_id or "snapshot-unknown",
        trade_date=trade_date,
        market=market,
        regime_version=regime_version,
        source_feature_version=source_feature_version,
        primary_label=primary_label,
        labels=labels,
        features=feature_records,
        confidence=confidence,
        quality_status=quality_status,
        missing_reason=missing_reason,
        warnings=[],
    )
