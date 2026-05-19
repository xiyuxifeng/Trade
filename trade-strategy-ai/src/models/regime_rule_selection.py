from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


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


@dataclass(frozen=True)
class RegimeRuleSelectionRecord:
    """单条规则在 regime-aware selection 中的结果。"""

    rule_id: str
    decision: str
    score: float
    reason: str
    evidence: list[str] = field(default_factory=list)
    regime_version: str = ""
    applicability_profile_version: str | None = None
    sample_count: int = 0
    profile_confidence: float = 0.0
    override_applied: bool = False
    rule_applicability_profile_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """返回 JSON 兼容字典。"""
        return _to_plain(self)


@dataclass(frozen=True)
class RegimeRuleSelectionResult:
    """Regime-aware rule selection 的输出。"""

    selection_id: str
    strategy_version_id: str
    snapshot_id: str
    market_regime_version: str
    source_feature_version: str | None
    applicability_profile_version: str | None
    selected_rules: list[RegimeRuleSelectionRecord] = field(default_factory=list)
    skipped_rules: list[RegimeRuleSelectionRecord] = field(default_factory=list)
    blocked_rules: list[RegimeRuleSelectionRecord] = field(default_factory=list)
    selection_reason: str = ""
    evidence: list[str] = field(default_factory=list)
    override: dict[str, Any] | None = None
    confidence: float = 0.0
    quality_status: str = "partial"
    warnings: list[str] = field(default_factory=list)
    created_at: datetime | None = None
    selected_by: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """返回 JSON 兼容字典。"""
        return _to_plain(self)
