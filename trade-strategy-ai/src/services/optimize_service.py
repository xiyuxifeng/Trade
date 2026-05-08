from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from src.backtest.schemas import BacktestResult, RuleValidationResult
from src.common.config import load_app_config
from src.optimization.active_trader_filter import ActiveTraderFilter, TraderFilterResult
from src.optimization.candidate_builder import CandidateBuildInput, CandidateBuildResult, build_candidate_version
from src.optimization.config import ActiveTraderFilterConfig
from src.optimization.strategy_advisor import AdvisorResult, RuleAdjustment, StrategyAdvisor
from src.services.base import BaseService, ServiceResult
from src.strategy_library.schemas import StrategyAdjustment, StrategyRecommendation, StrategyVersion, StrategyVersionStatus, StrategyVersionType


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
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "__dict__"):
        return _to_plain(vars(value))
    return value


def _load_json_list(path: str | Path) -> list[dict[str, Any]]:
    """从 JSON 文件中读取对象列表。"""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict) and "adjustments" in data:
        data = data["adjustments"]
    if isinstance(data, dict):
        return [data]
    if not isinstance(data, list):
        raise TypeError(f"Unsupported JSON payload: {type(data)!r}")
    return [item for item in data if isinstance(item, dict)]


def _load_strategy_version(path: str | Path) -> StrategyVersion:
    """从 JSON 文件恢复 StrategyVersion。"""
    def _parse_version_type(raw: Any) -> StrategyVersionType:
        try:
            return StrategyVersionType(raw)
        except Exception:
            return StrategyVersionType.manual

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return StrategyVersion(
        version_id=data["version_id"],
        trader_id=data["trader_id"],
        strategy_date=data["strategy_date"],
        status=StrategyVersionStatus(data["status"]),
        version_type=_parse_version_type(data.get("version_type", "manual")),
        parent_version_id=data.get("parent_version_id"),
        recommendations=[
            StrategyRecommendation(**item) for item in data.get("recommendations", [])
        ],
        source_article_ids=data.get("source_article_ids", []),
        evidence_refs=data.get("evidence_refs", []),
        notes=data.get("notes"),
        released_at=data.get("released_at"),
        rules_snapshot=data.get("rules_snapshot", []),
    )


def _rule_adjustment_to_strategy_adjustment(adjustment: RuleAdjustment) -> StrategyAdjustment:
    """将 RuleAdjustment 转换为 StrategyAdjustment。"""
    return StrategyAdjustment(
        trader_id=adjustment.trader_id,
        rule_id=adjustment.rule_id,
        current_status=adjustment.current_status,
        suggestion=adjustment.suggestion,
        confidence=adjustment.confidence,
        依据=f"hit_rate={adjustment.hit_rate}, rule_text={adjustment.rule_text}",
    )


class OptimizeService(BaseService):
    """优化与候选版本生成共享服务。"""

    service_name = "optimize"

    def __init__(
        self,
        *,
        filter_factory: Callable[[ActiveTraderFilterConfig | None], ActiveTraderFilter] = ActiveTraderFilter,
        advisor_factory: Callable[[], StrategyAdvisor] = StrategyAdvisor,
        candidate_builder: Callable[[CandidateBuildInput], CandidateBuildResult] = build_candidate_version,
        strategy_service_factory: Callable[[], Any] | None = None,
        session_scope_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._filter_factory = filter_factory
        self._advisor_factory = advisor_factory
        self._candidate_builder = candidate_builder
        self._strategy_service_factory = strategy_service_factory
        self._session_scope_factory = session_scope_factory

    def filter_active_traders(
        self,
        *,
        backtest_results: dict[str, BacktestResult],
        config: ActiveTraderFilterConfig | None = None,
        rule_validations: dict[str, list[RuleValidationResult]] | None = None,
    ) -> ServiceResult:
        """对多个 trader 执行筛选。"""
        flt = self._filter_factory(config)
        results = flt.filter(
            backtest_results=backtest_results,
            rule_validations=rule_validations,
        )
        return ServiceResult(
            status="ok",
            message="active trader filter completed",
            payload={
                "config": _to_plain(config or ActiveTraderFilterConfig()),
                "results": _to_plain(results),
            },
        )

    def advise_rule_validations(
        self,
        rule_validations: list[RuleValidationResult],
    ) -> ServiceResult:
        """基于规则验真结果生成优化建议。"""
        advisor = self._advisor_factory()
        result: AdvisorResult = advisor.advise(rule_validations)
        return ServiceResult(
            status="ok",
            message="strategy advise completed",
            payload={
                "trader_id": result.trader_id,
                "adjustments": _to_plain(result.adjustments),
                "skipped_rules": result.skipped_rules,
            },
        )

    async def create_candidate(
        self,
        *,
        parent_path: str | Path | None = None,
        adjustments_path: str | Path | None = None,
        trader_id: str | None = None,
        strategy_date: date | None = None,
        version_id: str | None = None,
        output: str | Path | None = None,
        use_db: bool = False,
    ) -> ServiceResult:
        """生成候选版本，支持文件链路与 DB 链路。"""
        if adjustments_path is None:
            raise ValueError("adjustments_path is required")

        adjustment_dicts = _load_json_list(adjustments_path)
        adjustments = [RuleAdjustment(**item) for item in adjustment_dicts]

        if use_db:
            if trader_id is None or strategy_date is None:
                raise ValueError("use_db=True requires trader_id and strategy_date")
            if self._strategy_service_factory is None or self._session_scope_factory is None:
                from src.db.session import session_scope
                from src.strategy_library.service import StrategyLibraryService

                self._session_scope_factory = session_scope
                self._strategy_service_factory = StrategyLibraryService

            strategy_service = self._strategy_service_factory()
            async def _run() -> StrategyVersion:
                async with self._session_scope_factory() as session:
                    parent = await strategy_service.get_current_released_version(
                        session=session,
                        trader_id=trader_id,
                        strategy_date=strategy_date,
                    )
                    if parent is None:
                        raise ValueError(f"未找到正式版本: trader={trader_id}, date={strategy_date}")
                    candidate = await strategy_service.create_candidate_version(
                        session=session,
                        trader_id=trader_id,
                        strategy_date=strategy_date,
                        parent_version_id=parent.version_id,
                        adjustments=[_rule_adjustment_to_strategy_adjustment(adj) for adj in adjustments],
                        recommendations=[],
                    )
                    await session.commit()
                    return candidate

            candidate = await _run()
            payload = {"candidate": _to_plain(candidate), "summary": {"deleted_rules": [], "modified_rules": [], "kept_rules": []}}
            if output:
                out_path = Path(output)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            return ServiceResult(status="ok", message="candidate version created from db", payload=payload)

        if parent_path is None:
            if trader_id is None or strategy_date is None or version_id is None:
                raise ValueError("file mode requires parent_path or trader_id + strategy_date + version_id")
            raise ValueError("parent_path is required for file mode")

        parent_version = _load_strategy_version(parent_path)
        input_obj = CandidateBuildInput(
            trader_id=parent_version.trader_id if trader_id is None else trader_id,
            strategy_date=parent_version.strategy_date if strategy_date is None else strategy_date,
            parent_version_id=parent_version.version_id if version_id is None else version_id,
            parent_rules_snapshot=parent_version.rules_snapshot or [],
            adjustments=adjustments,
            recommendations=[],
        )
        result = self._candidate_builder(input_obj)
        payload = {
            "version": _to_plain(result.version),
            "summary": {
                "deleted_rules": result.deleted_rules,
                "modified_rules": result.modified_rules,
                "kept_rules": result.kept_rules,
            },
        }
        if output:
            out_path = Path(output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return ServiceResult(status="ok", message="candidate version created", payload=payload)
