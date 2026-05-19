from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from hashlib import sha1
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from src.common.paths import resolve_project_path
from src.models.market_regime_record import MarketRegimeRecord
from src.models.regime_rule_selection import RegimeRuleSelectionRecord, RegimeRuleSelectionResult
from src.models.rule_applicability import RuleApplicabilityProfile
from src.services.base import BaseService, ServiceResult
from src.strategy_library.schemas import StrategyVersion
from src.trader_profile.schemas import TraderProfile


_REVIEW_STATUS_PRIORITY = {
    "active": 3,
    "reviewed": 2,
    "draft": 1,
    "archived": 0,
}


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
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _normalize_text(value: Any) -> str:
    """把文本归一化成可比较形式。"""
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = text.replace("-", "_").replace(" ", "_")
    return text


def _unique_ordered(values: list[str]) -> list[str]:
    """按出现顺序去重。"""
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _strategy_rule_text(rule: dict[str, Any]) -> str:
    """提取规则文本。"""
    parts = [
        rule.get("rule_id"),
        rule.get("rule_text"),
        rule.get("name"),
        rule.get("title"),
        rule.get("summary"),
    ]
    return " ".join(str(part) for part in parts if part not in {None, ""})


def _profile_rule_sort_key(profile: RuleApplicabilityProfile) -> tuple[int, int, str, str]:
    """画像选择排序键。"""
    created_at = getattr(profile, "created_at", None)
    created_order = int(created_at.timestamp() * 1_000_000) if created_at is not None else 0
    return (
        1 if profile.market_regime_version else 0,
        _REVIEW_STATUS_PRIORITY.get(profile.review_status, -1),
        created_order,
        str(profile.profile_id),
    )


def _extract_regime_labels(market_regime: MarketRegimeRecord) -> list[str]:
    """从 MarketRegime 中提取当前标签集合。"""
    labels = [market_regime.primary_label]
    for label in market_regime.labels:
        if isinstance(label, dict):
            value = label.get("label")
        else:
            value = getattr(label, "label", None)
        if value:
            labels.append(str(value))
    return _unique_ordered([_normalize_text(item) for item in labels if item])


def _extract_profile_regime_records(profile: RuleApplicabilityProfile, decision: str) -> list[dict[str, Any]]:
    """提取 profile 中的某类 regime 记录。"""
    if decision == "applicable":
        records = profile.applicable_regimes
    elif decision == "blocked":
        records = profile.blocked_regimes
    else:
        records = profile.neutral_regimes
    return [dict(item) for item in records]


def _match_regime_record(
    profile: RuleApplicabilityProfile,
    *,
    regime_labels: set[str],
) -> tuple[str, dict[str, Any] | None]:
    """根据当前 regime 标签匹配 profile 的决策记录。"""
    for decision in ("blocked", "applicable", "neutral"):
        for record in _extract_profile_regime_records(profile, decision):
            label = _normalize_text(record.get("regime_label"))
            if label and label in regime_labels:
                return decision, record
    return "skipped", None


def _record_score(
    *,
    decision: str,
    profile: RuleApplicabilityProfile,
    record: dict[str, Any] | None,
    trader_profile: TraderProfile,
    rule_text: str,
) -> tuple[float, list[str]]:
    """计算单条 rule 的综合分数和证据。"""
    evidence: list[str] = []
    if record is None:
        return 0.0, evidence

    base_score = {
        "applicable": 1.0,
        "neutral": 0.55,
        "blocked": 0.0,
        "skipped": 0.1,
    }.get(decision, 0.1)
    score = base_score
    evidence.append(f"decision={decision}")
    evidence.append(f"profile_confidence={profile.confidence:.2f}")
    evidence.append(f"sample_count={record.get('sample_count', 0)}")

    sample_count = int(record.get("sample_count", 0) or 0)
    score += min(sample_count, 50) / 250.0
    score += max(0.0, min(profile.confidence, 1.0)) * 0.18
    record_confidence = record.get("confidence")
    if record_confidence is not None:
        score += max(0.0, min(float(record_confidence), 1.0)) * 0.12

    normalized_rule_text = _normalize_text(rule_text)
    trader_signals: list[str] = []

    for tag in trader_profile.concept_tags:
        normalized_tag = _normalize_text(tag)
        if normalized_tag and normalized_tag in normalized_rule_text:
            trader_signals.append(f"concept_tag:{tag}")

    for theme in trader_profile.theme_preference:
        normalized_theme = _normalize_text(theme.theme)
        if normalized_theme and normalized_theme in normalized_rule_text:
            trader_signals.append(f"theme_preference:{theme.theme}")

    if trader_profile.strategy_preference and trader_profile.strategy_preference.entry_type:
        entry_type = _normalize_text(trader_profile.strategy_preference.entry_type)
        if entry_type and entry_type in normalized_rule_text:
            trader_signals.append(f"entry_type:{trader_profile.strategy_preference.entry_type}")

    if trader_signals:
        score += min(0.12, 0.04 * len(trader_signals))
        evidence.extend(trader_signals)

    if decision == "blocked":
        score = 0.0
    elif decision == "neutral":
        score = min(score, 0.85)
    else:
        score = min(score, 1.0)

    return round(score, 4), evidence


def _selection_priority(decision: str) -> int:
    """选择排序优先级。"""
    return {
        "blocked": 3,
        "applicable": 2,
        "neutral": 1,
        "skipped": 0,
    }.get(decision, 0)


class RegimeRuleSelectionService(BaseService):
    """Regime-aware rule selection 服务。"""

    service_name = "regime-rule-selection"

    def __init__(
        self,
        *,
        artifact_root: str | Path | None = None,
    ) -> None:
        self._artifact_root = Path(artifact_root).expanduser().resolve() if artifact_root is not None else resolve_project_path("data/processed/strategy_regime_selection")

    def _artifact_path(
        self,
        *,
        strategy_version_id: str,
        snapshot_id: str,
        market_regime_version: str,
        selection_id: str,
    ) -> Path:
        """返回 selection artifact 路径。"""
        return self._artifact_root / strategy_version_id / snapshot_id / market_regime_version / f"{selection_id}.json"

    def _artifact_ref(self, artifact_path: Path) -> dict[str, Any]:
        """返回 artifact 的安全引用。"""
        try:
            relative = artifact_path.relative_to(self._artifact_root)
        except ValueError:
            relative = artifact_path.name
        return {
            "artifact_type": "regime-rule-selection-json",
            "artifact_root": str(self._artifact_root.name or "strategy_regime_selection"),
            "relative_path": str(relative),
        }

    async def build_regime_rule_selection(
        self,
        *,
        strategy_version: StrategyVersion,
        trader_profile: TraderProfile,
        market_regime: MarketRegimeRecord,
        applicability_profiles: list[RuleApplicabilityProfile],
        selected_by: str,
        applicability_profile_version: str | None = None,
        override: dict[str, Any] | None = None,
    ) -> ServiceResult:
        """生成 regime-aware rule selection。"""
        regime_labels = set(_extract_regime_labels(market_regime))
        if not regime_labels:
            regime_labels = {_normalize_text(market_regime.primary_label)}

        selection_seed = "|".join(
            [
                strategy_version.version_id,
                strategy_version.trader_id,
                market_regime.snapshot_id,
                market_regime.regime_version,
                selected_by,
                applicability_profile_version or "",
            ]
        )
        selection_id = str(uuid5(NAMESPACE_URL, selection_seed))
        artifact_path = self._artifact_path(
            strategy_version_id=strategy_version.version_id,
            snapshot_id=market_regime.snapshot_id,
            market_regime_version=market_regime.regime_version,
            selection_id=selection_id,
        )

        profiles_by_rule: dict[str, list[RuleApplicabilityProfile]] = defaultdict(list)
        for profile in applicability_profiles:
            if applicability_profile_version and profile.profile_version != applicability_profile_version:
                continue
            profiles_by_rule[profile.rule_id].append(profile)

        selected_rules: list[RegimeRuleSelectionRecord] = []
        skipped_rules: list[RegimeRuleSelectionRecord] = []
        blocked_rules: list[RegimeRuleSelectionRecord] = []
        warnings: list[str] = []
        candidate_versions: list[str] = []

        for raw_rule in strategy_version.rules_snapshot:
            rule = raw_rule if isinstance(raw_rule, dict) else _to_plain(raw_rule)
            rule_id = str(rule.get("rule_id") or rule.get("id") or rule.get("name") or "").strip()
            if not rule_id:
                warnings.append("strategy rule missing rule_id")
                continue
            rule_text = _strategy_rule_text(rule)
            candidates = sorted(profiles_by_rule.get(rule_id, []), key=_profile_rule_sort_key, reverse=True)
            if not candidates:
                skipped_rules.append(
                    RegimeRuleSelectionRecord(
                        rule_id=rule_id,
                        decision="skipped",
                        score=0.0,
                        reason="没有可用的 Rule Applicability Profile",
                        evidence=[f"strategy_rule={rule_id}", "missing_applicability_profile"],
                        regime_version=market_regime.regime_version,
                    )
                )
                continue

            best_decision = "skipped"
            best_record: dict[str, Any] | None = None
            best_profile: RuleApplicabilityProfile | None = None
            for profile in candidates:
                decision, matched_record = _match_regime_record(profile, regime_labels=regime_labels)
                if decision == "skipped":
                    continue
                if _selection_priority(decision) > _selection_priority(best_decision):
                    best_decision = decision
                    best_record = matched_record
                    best_profile = profile
                elif _selection_priority(decision) == _selection_priority(best_decision) and best_profile is not None:
                    current_key = _profile_rule_sort_key(profile)
                    best_key = _profile_rule_sort_key(best_profile)
                    if current_key > best_key:
                        best_decision = decision
                        best_record = matched_record
                        best_profile = profile

            if best_profile is None or best_record is None:
                skipped_rules.append(
                    RegimeRuleSelectionRecord(
                        rule_id=rule_id,
                        decision="skipped",
                        score=0.0,
                        reason="画像存在但未匹配当前 Market Regime",
                        evidence=[f"strategy_rule={rule_id}", f"regime_labels={sorted(regime_labels)}"],
                        regime_version=market_regime.regime_version,
                        applicability_profile_version=candidates[0].profile_version if candidates else None,
                        rule_applicability_profile_id=str(candidates[0].profile_id) if candidates else None,
                    )
                )
                continue

            score, evidence = _record_score(
                decision=best_decision,
                profile=best_profile,
                record=best_record,
                trader_profile=trader_profile,
                rule_text=rule_text,
            )
            evidence.extend(
                [
                    f"rule_id={rule_id}",
                    f"regime_label={best_record.get('regime_label')}",
                    f"profile_version={best_profile.profile_version}",
                ]
            )
            candidate_versions.append(best_profile.profile_version)
            rule_result = RegimeRuleSelectionRecord(
                rule_id=rule_id,
                decision=best_decision,
                score=score,
                reason=str(best_record.get("reason") or ""),
                evidence=evidence,
                regime_version=market_regime.regime_version,
                applicability_profile_version=best_profile.profile_version,
                sample_count=int(best_record.get("sample_count") or 0),
                profile_confidence=float(best_profile.confidence),
                override_applied=bool(override),
                rule_applicability_profile_id=str(best_profile.profile_id),
            )
            if best_decision == "blocked" and not override:
                blocked_rules.append(rule_result)
            else:
                selected_rules.append(rule_result)

        selected_rules.sort(
            key=lambda item: (
                -_selection_priority(item.decision),
                -item.score,
                -item.profile_confidence,
                -item.sample_count,
                item.rule_id,
            )
        )
        skipped_rules.sort(
            key=lambda item: (
                -_selection_priority(item.decision),
                -item.score,
                item.rule_id,
            )
        )
        blocked_rules.sort(
            key=lambda item: (
                -item.score,
                item.rule_id,
            )
        )

        selection_confidence_parts = [item.score for item in selected_rules]
        confidence = round(sum(selection_confidence_parts) / len(selection_confidence_parts), 4) if selection_confidence_parts else 0.0
        quality_status = "ok"
        if skipped_rules:
            quality_status = "partial"
        if confidence < 0.45:
            quality_status = "low_confidence"
        if warnings:
            quality_status = "partial" if quality_status == "ok" else quality_status

        if candidate_versions:
            profile_version = Counter(candidate_versions).most_common(1)[0][0]
        else:
            profile_version = applicability_profile_version

        selection = RegimeRuleSelectionResult(
            selection_id=selection_id,
            strategy_version_id=strategy_version.version_id,
            snapshot_id=market_regime.snapshot_id,
            market_regime_version=market_regime.regime_version,
            source_feature_version=market_regime.source_feature_version,
            applicability_profile_version=profile_version,
            selected_rules=selected_rules,
            skipped_rules=skipped_rules,
            blocked_rules=blocked_rules,
            selection_reason="applicable 优先，neutral 低权重补充，blocked 默认排除",
            evidence=[
                f"market_regime={market_regime.primary_label}",
                f"regime_labels={sorted(regime_labels)}",
                f"strategy_rules={len(strategy_version.rules_snapshot)}",
                f"selected_rules={len(selected_rules)}",
                f"blocked_rules={len(blocked_rules)}",
            ],
            override=_to_plain(override) if override else None,
            confidence=confidence,
            quality_status=quality_status,
            warnings=warnings,
            created_at=datetime.now(UTC),
            selected_by=selected_by,
        )

        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_payload = {
            "selection": selection.to_dict(),
            "strategy_version": {
                "version_id": strategy_version.version_id,
                "trader_id": strategy_version.trader_id,
                "strategy_date": strategy_version.strategy_date.isoformat() if hasattr(strategy_version.strategy_date, "isoformat") else str(strategy_version.strategy_date),
                "status": str(strategy_version.status),
                "version_type": str(strategy_version.version_type),
                "rules_snapshot_count": len(strategy_version.rules_snapshot),
            },
            "selected_by": selected_by,
            "market_regime": market_regime.to_dict(),
            "trader_profile": _to_plain(trader_profile),
            "warnings": warnings,
        }
        artifact_path.write_text(json.dumps(_to_plain(artifact_payload), ensure_ascii=False, indent=2), encoding="utf-8")

        payload = {
            "selection": selection.to_dict(),
            "artifact_ref": self._artifact_ref(artifact_path),
            "artifact_path": self._artifact_ref(artifact_path)["relative_path"],
            "warnings": warnings,
        }
        status = "ok" if quality_status == "ok" and not warnings else "partial"
        return ServiceResult(
            status=status,  # type: ignore[arg-type]
            message="regime-aware rule selection completed",
            payload=payload,
            warnings=warnings,
        )
