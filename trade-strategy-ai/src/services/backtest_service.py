from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable

from src.backtest.engine import BacktestEngine, validate_rules_for_trader
from src.backtest.reporting import (
    render_backtest_csv,
    render_backtest_json,
    render_backtest_markdown,
    render_rule_validation_markdown,
)
from src.backtest.reproducibility import fingerprint_result
from src.backtest.schemas import (
    BacktestRequest,
    BacktestResult,
    BacktestSummary,
    BacktestTradeRecord,
    RuleValidationResult,
    RegimeBacktestMetric,
)
from src.backtest.snapshot_loader import SnapshotLoader
from src.common.config import apply_database_config_to_env, load_app_config
from src.db.repositories.market_snapshot_repository import MarketSnapshotRepository
from src.services.base import BaseService, ServiceResult
from src.services.config_profile_service import ConfigProfileService
from src.services.market_regime_feature_service import DEFAULT_FEATURE_VERSION, FULL_MARKET_FEATURE_VERSION, MarketRegimeFeatureService
from src.services.market_regime_service import DEFAULT_REGIME_VERSION, MarketRegimeService


def _to_plain(value: Any) -> Any:
    """把 dataclass / Pydantic / 容器转换为前端可序列化结构。"""
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
    if isinstance(value, Path):
        return str(value)
    return value


def _parse_date(value: str | date) -> date:
    """兼容字符串与 date 输入。"""
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def _coerce_backtest_record(value: Any) -> BacktestTradeRecord:
    """把字典记录恢复为 BacktestTradeRecord。"""
    if isinstance(value, BacktestTradeRecord):
        return value
    if not isinstance(value, dict):
        if hasattr(value, "__dict__"):
            value = dict(vars(value))
        else:
            raise TypeError(f"Unsupported backtest record type: {type(value)!r}")
    return BacktestTradeRecord(
        trade_date=_parse_date(value["trade_date"]),
        trader_id=value.get("trader_id", ""),
        strategy_version_id=value.get("strategy_version_id", ""),
        symbol=value.get("symbol", ""),
        status=value.get("status", "skipped"),
        entry_price=value.get("entry_price"),
        exit_price=value.get("exit_price"),
        entry_date=value.get("entry_date"),
        exit_date=value.get("exit_date"),
        return_pct=value.get("return_pct"),
        mfe=value.get("mfe"),
        mae=value.get("mae"),
        volume=value.get("volume"),
        is_valid_lot_size=value.get("is_valid_lot_size"),
        skip_reason=value.get("skip_reason"),
        evidence_refs=value.get("evidence_refs", []),
    )


def _coerce_backtest_summary(value: Any | None) -> BacktestSummary | None:
    """把字典汇总恢复为 BacktestSummary。"""
    if value is None:
        return None
    if isinstance(value, BacktestSummary):
        return value
    if not isinstance(value, dict):
        if hasattr(value, "__dict__"):
            value = dict(vars(value))
        else:
            raise TypeError(f"Unsupported backtest summary type: {type(value)!r}")
    return BacktestSummary(
        total_days=value.get("total_days", 0),
        total_trades=value.get("total_trades", 0),
        valid_trades=value.get("valid_trades", 0),
        skipped_trades=value.get("skipped_trades", 0),
        win_rate=value.get("win_rate"),
        avg_return_pct=value.get("avg_return_pct"),
    )


def _coerce_regime_metric(value: Any) -> RegimeBacktestMetric:
    """把字典恢复为 RegimeBacktestMetric。"""
    if isinstance(value, RegimeBacktestMetric):
        return value
    if not isinstance(value, dict):
        if hasattr(value, "__dict__"):
            value = dict(vars(value))
        else:
            raise TypeError(f"Unsupported regime metric type: {type(value)!r}")
    return RegimeBacktestMetric(
        regime_label=value.get("regime_label", "unknown"),
        sample_count=int(value.get("sample_count", 0)),
        win_trades=int(value.get("win_trades", 0)),
        loss_trades=int(value.get("loss_trades", 0)),
        win_rate=value.get("win_rate"),
        avg_return=value.get("avg_return"),
        avg_win_return=value.get("avg_win_return"),
        avg_loss_return=value.get("avg_loss_return"),
        max_drawdown=value.get("max_drawdown"),
        profit_factor=value.get("profit_factor"),
        confidence=float(value.get("confidence", 0.0) or 0.0),
        low_sample=bool(value.get("low_sample", False)),
    )


def _coerce_regime_metric_list(value: Any | None) -> list[RegimeBacktestMetric]:
    """把 regime metric 容器恢复为结构化列表。"""
    if value is None:
        return []
    if not isinstance(value, list):
        if hasattr(value, "__iter__") and not isinstance(value, (str, bytes, dict)):
            value = list(value)
        else:
            return []
    return [_coerce_regime_metric(item) for item in value]


def _coerce_backtest_result(value: Any) -> BacktestResult:
    """把前端/序列化对象恢复为 BacktestResult。"""
    if isinstance(value, BacktestResult):
        return value
    if not isinstance(value, dict):
        if hasattr(value, "__dict__"):
            value = dict(vars(value))
        else:
            raise TypeError(f"Unsupported backtest result type: {type(value)!r}")

    records = [_coerce_backtest_record(item) for item in value.get("records", [])]
    summary = _coerce_backtest_summary(value.get("summary"))
    raw_rule_regime_metrics = value.get("rule_regime_metrics")
    rule_regime_metrics: dict[str, list[RegimeBacktestMetric]] = {}
    if isinstance(raw_rule_regime_metrics, dict):
        rule_regime_metrics = {
            str(rule_id): _coerce_regime_metric_list(metrics)
            for rule_id, metrics in raw_rule_regime_metrics.items()
        }
    return BacktestResult(
        request_trader_id=value["request_trader_id"],
        request_date_from=_parse_date(value["request_date_from"]),
        request_date_to=_parse_date(value["request_date_to"]),
        benchmark_symbol=value.get("benchmark_symbol"),
        regime_version=value.get("regime_version"),
        source_feature_version=value.get("source_feature_version"),
        records=records,
        summary=summary,
        regime_metrics=_coerce_regime_metric_list(value.get("regime_metrics")),
        rule_regime_metrics=rule_regime_metrics,
        result_version=value.get("result_version", "1.0"),
    )


def _coerce_rule_validation_result(value: Any) -> RuleValidationResult:
    """把序列化对象恢复为 RuleValidationResult。"""
    if isinstance(value, RuleValidationResult):
        return value
    if not isinstance(value, dict):
        if hasattr(value, "__dict__"):
            value = dict(vars(value))
        else:
            raise TypeError(f"Unsupported rule validation result type: {type(value)!r}")
    return RuleValidationResult(
        trader_id=value.get("trader_id", ""),
        strategy_version_id=value.get("strategy_version_id", ""),
        rule_id=value.get("rule_id", ""),
        rule_text=value.get("rule_text", ""),
        programmable=value.get("programmable", False),
        validation_status=value.get("validation_status", "invalid_rule"),
        hit_count=value.get("hit_count", 0),
        sample_count=value.get("sample_count", 0),
        hit_rate=value.get("hit_rate"),
        posterior_return_mean=value.get("posterior_return_mean"),
        posterior_return_median=value.get("posterior_return_median"),
        notes=value.get("notes", []),
        result_version=value.get("result_version", "1.0"),
    )


def _default_engine_factory(
    *,
    config_path: str | Path | None = None,
    config: Any | None = None,
    base_dir: Path | None = None,
    use_snapshot_only: bool = True,
    scoring_profile: str = "stage5",
) -> BacktestEngine:
    """从配置文件构建默认回测引擎。"""
    del scoring_profile
    if config is None and config_path is None:
        return BacktestEngine()

    loaded_config_path: Path | None = None
    if config is None:
        try:
            loaded = load_app_config(config_path)
        except Exception:
            return BacktestEngine()
        config = loaded.config
        loaded_config_path = loaded.config_path
        if base_dir is None:
            base_dir = Path(loaded.config_path).parent.parent if Path(loaded.config_path).parent.name == "config" else Path(loaded.config_path).parent

    apply_database_config_to_env(config)

    from config.database import get_session_factory
    from src.backtest.snapshot_loader import SnapshotLoader
    from src.indicators.indicator_service import IndicatorService
    from src.market_data.strategy_repo_adapter import StrategyRepoAdapter
    from src.market_universe.snapshot_service import SnapshotService
    from src.services.market_snapshot_service import MarketSnapshotService

    snapshot_base_dir = config.data.market_universe_snapshot_dir
    if not snapshot_base_dir:
        snapshot_base_dir = "data/market_universe/snapshots"
    snapshot_base_dir = Path(snapshot_base_dir)
    if not snapshot_base_dir.is_absolute():
        snapshot_base_dir = (base_dir or Path.cwd()) / snapshot_base_dir

    session_factory = get_session_factory()
    loader = SnapshotLoader(
        snapshot_service=SnapshotService(base_dir=snapshot_base_dir),
        market_snapshot_service=MarketSnapshotService(),
        strategy_repo=StrategyRepoAdapter(),
        indicator_service=IndicatorService(session_factory),
        session_factory=session_factory,
        use_snapshot_only=use_snapshot_only,
        config_path=str(loaded_config_path) if loaded_config_path is not None else None,
        market_universe_slot=getattr(config.pre_market_formal_flow, "market_universe_slot", "09-25"),
    )
    return BacktestEngine(loader=loader, strategy_loader=loader)


class BacktestService(BaseService):
    """回测、规则验真、复现检查与规则池回测的共享服务。"""

    service_name = "backtest"

    def __init__(
        self,
        *,
        engine_factory: Callable[..., BacktestEngine] = _default_engine_factory,
        rule_validation_runner: Callable[..., Any] = validate_rules_for_trader,
        session_scope_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._engine_factory = engine_factory
        self._rule_validation_runner = rule_validation_runner
        self._session_scope_factory = session_scope_factory

    def _build_engine(
        self,
        *,
        config_path: str | Path | None = None,
        config: Any | None = None,
        base_dir: Path | None = None,
        use_snapshot_only: bool = True,
        scoring_profile: str = "stage5",
    ) -> BacktestEngine:
        """按需构建回测引擎。"""
        return self._engine_factory(
            config_path=config_path,
            config=config,
            base_dir=base_dir,
            use_snapshot_only=use_snapshot_only,
            scoring_profile=scoring_profile,
        )

    def _build_request(
        self,
        *,
        trader_id: str,
        date_from: date,
        date_to: date,
        strategy_version_id: str | None = None,
        symbols: list[str] | None = None,
        market_regime_version: str | None = None,
        benchmark_symbol: str | None = None,
        mode: str = "full",
        use_snapshot_only: bool = True,
        scoring_profile: str = "stage5",
    ) -> BacktestRequest:
        """构造统一的回测请求模型。"""
        return BacktestRequest(
            trader_id=trader_id,
            date_from=date_from,
            date_to=date_to,
            strategy_version_id=strategy_version_id,
            symbols=symbols or [],
            market_regime_version=market_regime_version or DEFAULT_REGIME_VERSION,
            benchmark_symbol=benchmark_symbol,
            mode=mode,  # type: ignore[arg-type]
            use_snapshot_only=use_snapshot_only,
            scoring_profile=scoring_profile,
        )

    def _feature_version_for_regime_version(self, regime_version: str | None) -> str | None:
        """把 regime_version 映射到对应的 feature_version。"""
        if regime_version is None:
            return None
        if regime_version.endswith("-v3"):
            return FULL_MARKET_FEATURE_VERSION
        if regime_version.endswith("-v2"):
            return "market-regime-features-v2"
        return DEFAULT_FEATURE_VERSION

    async def _prepare_regime_backtest_inputs(
        self,
        *,
        start_date: date,
        end_date: date,
        market_regime_version: str | None,
    ) -> None:
        """在回测前补齐指定版本的 feature / regime。"""
        market_regime_version = market_regime_version or DEFAULT_REGIME_VERSION

        feature_version = self._feature_version_for_regime_version(market_regime_version)
        if feature_version is None:
            return

        if self._session_scope_factory is None:
            from src.db.session import session_scope

            self._session_scope_factory = session_scope

        snapshot_repo = MarketSnapshotRepository()
        feature_service = MarketRegimeFeatureService()
        regime_service = MarketRegimeService()

        from src.backtest.engine import iter_trade_dates

        async with self._session_scope_factory() as session:
            for trade_date in iter_trade_dates(start_date, end_date):
                snapshots = await snapshot_repo.list_snapshots(
                    session,
                    trade_date=trade_date,
                    market="CN",
                    quality_status="ok",
                    limit=1,
                )
                if not snapshots:
                    continue
                snapshot = snapshots[0]
                await feature_service.build_market_regime_features(
                    snapshot_id=snapshot.snapshot_id,
                    feature_version=feature_version,
                )
                await regime_service.build_market_regime(
                    snapshot_id=snapshot.snapshot_id,
                    regime_version=market_regime_version,
                    feature_version=feature_version,
                )

    async def _load_profile_runtime_context(self, profile_id: str) -> tuple[Any, Path]:
        """加载 Profile 运行态，供 Web 回测链路使用。"""
        runtime = await ConfigProfileService().load_profile_runtime_config(profile_id)
        return runtime.config, runtime.base_dir

    async def run_backtest_profile(
        self,
        *,
        profile_id: str,
        trader_id: str,
        date_from: date,
        date_to: date,
        strategy_version_id: str | None = None,
        symbols: list[str] | None = None,
        market_regime_version: str | None = DEFAULT_REGIME_VERSION,
        benchmark_symbol: str | None = None,
        mode: str = "full",
        config_path: str | Path | None = None,
        use_snapshot_only: bool = True,
        scoring_profile: str = "stage5",
        runtime_state: dict[str, Any] | None = None,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> ServiceResult:
        """基于 Profile 运行离线回测。"""
        runtime_config, runtime_base_dir = await self._load_profile_runtime_context(profile_id)
        request = self._build_request(
            trader_id=trader_id,
            date_from=date_from,
            date_to=date_to,
            strategy_version_id=strategy_version_id,
            symbols=symbols,
            market_regime_version=market_regime_version,
            benchmark_symbol=benchmark_symbol,
            mode=mode,
            use_snapshot_only=use_snapshot_only,
            scoring_profile=scoring_profile,
        )
        engine = self._build_engine(
            config=runtime_config,
            base_dir=runtime_base_dir,
            use_snapshot_only=use_snapshot_only,
            scoring_profile=scoring_profile,
        )
        apply_database_config_to_env(runtime_config)
        try:
            result = engine.run_sync(request, progress_callback=progress_callback, runtime_state=runtime_state)
        except TypeError as exc:
            if "progress_callback" not in str(exc) and "runtime_state" not in str(exc):
                raise
            try:
                result = engine.run_sync(request, progress_callback=progress_callback)
            except TypeError as inner_exc:
                if "progress_callback" not in str(inner_exc):
                    raise
                result = engine.run_sync(request)
        fingerprint = fingerprint_result(result)
        return ServiceResult(
            status="ok",
            message="backtest completed",
            payload={
                "profile_id": profile_id,
                "config_path": None,
                "request": _to_plain(request),
                "result": _to_plain(result),
                "summary": _to_plain(result.summary),
                "fingerprint": fingerprint,
            },
        )

    def run_backtest(
        self,
        *,
        trader_id: str,
        date_from: date,
        date_to: date,
        strategy_version_id: str | None = None,
        symbols: list[str] | None = None,
        market_regime_version: str | None = DEFAULT_REGIME_VERSION,
        benchmark_symbol: str | None = None,
        mode: str = "full",
        config_path: str | Path | None = None,
        use_snapshot_only: bool = True,
        scoring_profile: str = "stage5",
        runtime_state: dict[str, Any] | None = None,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> ServiceResult:
        """运行离线回测。"""
        request = self._build_request(
            trader_id=trader_id,
            date_from=date_from,
            date_to=date_to,
            strategy_version_id=strategy_version_id,
            symbols=symbols,
            market_regime_version=market_regime_version,
            benchmark_symbol=benchmark_symbol,
            mode=mode,
            use_snapshot_only=use_snapshot_only,
            scoring_profile=scoring_profile,
        )
        engine = self._build_engine(
            config_path=config_path,
            use_snapshot_only=use_snapshot_only,
            scoring_profile=scoring_profile,
        )
        try:
            result = engine.run_sync(request, progress_callback=progress_callback, runtime_state=runtime_state)
        except TypeError as exc:
            if "progress_callback" not in str(exc) and "runtime_state" not in str(exc):
                raise
            try:
                result = engine.run_sync(request, progress_callback=progress_callback)
            except TypeError as inner_exc:
                if "progress_callback" not in str(inner_exc):
                    raise
                result = engine.run_sync(request)
        fingerprint = fingerprint_result(result)
        return ServiceResult(
            status="ok",
            message="backtest completed",
            payload={
                "config_path": str(config_path) if config_path is not None else None,
                "request": _to_plain(request),
                "result": _to_plain(result),
                "summary": _to_plain(result.summary),
                "fingerprint": fingerprint,
            },
        )

    def load_backtest_result(self, *, result_file: str | Path) -> ServiceResult:
        """从 JSON 文件恢复回测结果。"""
        path = Path(result_file)
        data = json.loads(path.read_text(encoding="utf-8"))
        result = _coerce_backtest_result(data)
        return ServiceResult(
            status="ok",
            message="backtest result loaded",
            payload={
                "result_file": str(path),
                "result": _to_plain(result),
            },
        )

    def render_backtest_report(
        self,
        result: BacktestResult | dict[str, Any],
        *,
        format: str = "markdown",
    ) -> ServiceResult:
        """把回测结果渲染为 Markdown、JSON 或 CSV 文本。"""
        coerced = _coerce_backtest_result(result)
        if format == "json":
            content = render_backtest_json(coerced)
        elif format == "csv":
            content = render_backtest_csv(coerced)
        else:
            content = render_backtest_markdown(coerced)
        return ServiceResult(
            status="ok",
            message="backtest report rendered",
            payload={
                "format": format,
                "content": content,
                "result": _to_plain(coerced),
            },
        )

    async def validate_rules(
        self,
        *,
        trader_id: str,
        date_from: date,
        date_to: date,
        profile_id: str | None = None,
        config_path: str | Path | None = None,
        strategy_version_id: str | None = None,
        symbols: list[str] | None = None,
        benchmark_symbol: str | None = None,
        use_snapshot_only: bool = True,
        scoring_profile: str = "stage5",
        mode: str = "rule_validation",
        runtime_state: dict[str, Any] | None = None,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> ServiceResult:
        """执行规则验真并生成验真报告。"""
        del strategy_version_id, symbols, benchmark_symbol, use_snapshot_only, scoring_profile, mode
        runtime_config = None
        runtime_base_dir = None
        if profile_id is not None and str(profile_id).strip():
            runtime_config, runtime_base_dir = await self._load_profile_runtime_context(str(profile_id).strip())
            config_path = None
        engine = self._build_engine(
            config_path=config_path,
            config=runtime_config,
            base_dir=runtime_base_dir,
        )
        loader_obj = getattr(engine, "loader", None)
        loader = loader_obj if loader_obj is not None else SnapshotLoader()

        try:
            results = await self._rule_validation_runner(
                trader_id=trader_id,
                date_from=date_from,
                date_to=date_to,
                loader=loader,
                runtime_state=runtime_state,
                progress_callback=progress_callback,
            )
        except TypeError as exc:
            if "runtime_state" not in str(exc) and "progress_callback" not in str(exc):
                raise
            results = await self._rule_validation_runner(
                trader_id=trader_id,
                date_from=date_from,
                date_to=date_to,
                loader=loader,
            )
        coerced_results = [_coerce_rule_validation_result(item) for item in results]
        report = render_rule_validation_markdown(coerced_results)
        programmable_count = sum(1 for item in coerced_results if item.programmable)
        validated_count = sum(1 for item in coerced_results if item.validation_status == "validated")
        return ServiceResult(
            status="ok",
            message="rule validation completed",
            payload={
                "profile_id": str(profile_id).strip() if profile_id is not None and str(profile_id).strip() else None,
                "config_path": str(config_path) if config_path is not None else None,
                "trader_id": trader_id,
                "date_from": date_from.isoformat(),
                "date_to": date_to.isoformat(),
                "coverage": {
                    "total": len(coerced_results),
                    "programmable": programmable_count,
                    "validated": validated_count,
                },
                "results": _to_plain(coerced_results),
                "report": report,
            },
        )

    def render_rule_validation_report(
        self,
        results: list[RuleValidationResult] | list[dict[str, Any]],
    ) -> ServiceResult:
        """把规则验真结果渲染为 Markdown 文本。"""
        coerced_results = [_coerce_rule_validation_result(item) for item in results]
        return ServiceResult(
            status="ok",
            message="rule validation report rendered",
            payload={
                "content": render_rule_validation_markdown(coerced_results),
                "results": _to_plain(coerced_results),
            },
        )

    def reproducibility_check(
        self,
        *,
        trader_id: str,
        date_from: date,
        date_to: date,
        strategy_version_id: str | None = None,
        symbols: list[str] | None = None,
        market_regime_version: str | None = DEFAULT_REGIME_VERSION,
        benchmark_symbol: str | None = None,
        mode: str = "full",
        config_path: str | Path | None = None,
        use_snapshot_only: bool = True,
        scoring_profile: str = "stage5",
    ) -> ServiceResult:
        """运行两次回测并检查 fingerprint 是否一致。"""
        request = self._build_request(
            trader_id=trader_id,
            date_from=date_from,
            date_to=date_to,
            strategy_version_id=strategy_version_id,
            symbols=symbols,
            market_regime_version=market_regime_version,
            benchmark_symbol=benchmark_symbol,
            mode=mode,
            use_snapshot_only=use_snapshot_only,
            scoring_profile=scoring_profile,
        )
        engine = self._build_engine(config_path=config_path, use_snapshot_only=use_snapshot_only, scoring_profile=scoring_profile)
        result_a = engine.run_sync(request)
        result_b = engine.run_sync(request)
        fingerprint_a = fingerprint_result(_coerce_backtest_result(result_a))
        fingerprint_b = fingerprint_result(_coerce_backtest_result(result_b))
        matches = fingerprint_a == fingerprint_b
        status = "ok" if matches else "partial"
        warnings = [] if matches else ["reproducibility check failed"]
        return ServiceResult(
            status=status,
            message="reproducibility check completed" if matches else "reproducibility check failed",
            payload={
                "config_path": str(config_path) if config_path is not None else None,
                "request": _to_plain(request),
                "fingerprint_a": fingerprint_a,
                "fingerprint_b": fingerprint_b,
                "matches": matches,
                "result_a": _to_plain(result_a),
                "result_b": _to_plain(result_b),
            },
            warnings=warnings,
        )

    async def reproducibility_check_profile(
        self,
        *,
        profile_id: str,
        trader_id: str,
        date_from: date,
        date_to: date,
        strategy_version_id: str | None = None,
        symbols: list[str] | None = None,
        market_regime_version: str | None = DEFAULT_REGIME_VERSION,
        benchmark_symbol: str | None = None,
        mode: str = "full",
        config_path: str | Path | None = None,
        use_snapshot_only: bool = True,
        scoring_profile: str = "stage5",
    ) -> ServiceResult:
        """基于 Profile 运行两次回测并检查 fingerprint 是否一致。"""
        del config_path
        runtime_config, runtime_base_dir = await self._load_profile_runtime_context(profile_id)
        request = self._build_request(
            trader_id=trader_id,
            date_from=date_from,
            date_to=date_to,
            strategy_version_id=strategy_version_id,
            symbols=symbols,
            market_regime_version=market_regime_version,
            benchmark_symbol=benchmark_symbol,
            mode=mode,
            use_snapshot_only=use_snapshot_only,
            scoring_profile=scoring_profile,
        )
        engine = self._build_engine(
            config=runtime_config,
            base_dir=runtime_base_dir,
            use_snapshot_only=use_snapshot_only,
            scoring_profile=scoring_profile,
        )
        apply_database_config_to_env(runtime_config)
        result_a = engine.run_sync(request)
        result_b = engine.run_sync(request)
        fingerprint_a = fingerprint_result(_coerce_backtest_result(result_a))
        fingerprint_b = fingerprint_result(_coerce_backtest_result(result_b))
        matches = fingerprint_a == fingerprint_b
        status = "ok" if matches else "partial"
        warnings = [] if matches else ["reproducibility check failed"]
        return ServiceResult(
            status=status,
            message="reproducibility check completed" if matches else "reproducibility check failed",
            payload={
                "profile_id": profile_id,
                "config_path": None,
                "request": _to_plain(request),
                "fingerprint_a": fingerprint_a,
                "fingerprint_b": fingerprint_b,
                "matches": matches,
                "result_a": _to_plain(result_a),
                "result_b": _to_plain(result_b),
            },
            warnings=warnings,
        )

    def _ensure_session_scope_factory(self) -> None:
        """确保 session_scope_factory 已初始化（惰性单例）。"""
        if self._session_scope_factory is None:
            from src.db.session import session_scope

            self._session_scope_factory = session_scope

    async def run_rule_pool_backtest(
        self,
        *,
        start_date: date,
        end_date: date,
        rule_ids: list[str] | None = None,
        min_confidence: float = 0.5,
        market_regime_version: str | None = DEFAULT_REGIME_VERSION,
        profile_id: str | None = None,
        config_path: str | Path | None = None,
        use_snapshot_only: bool = True,
        scoring_profile: str = "stage5",
        runtime_state: dict[str, Any] | None = None,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> ServiceResult:
        """对规则池中的规则执行回测。"""
        self._ensure_session_scope_factory()

        await self._prepare_regime_backtest_inputs(
            start_date=start_date,
            end_date=end_date,
            market_regime_version=market_regime_version,
        )

        runtime_config = None
        runtime_base_dir = None
        if profile_id is not None and str(profile_id).strip():
            runtime_config, runtime_base_dir = await self._load_profile_runtime_context(str(profile_id).strip())
            config_path = None
        engine = self._build_engine(
            config_path=config_path,
            config=runtime_config,
            base_dir=runtime_base_dir,
            use_snapshot_only=use_snapshot_only,
            scoring_profile=scoring_profile,
        )
        try:
            async with self._session_scope_factory() as session:
                try:
                    result = await engine.run_rules_backtest(
                        session=session,
                        rule_ids=rule_ids,
                        start_date=start_date,
                        end_date=end_date,
                        min_confidence=min_confidence,
                        market_regime_version=market_regime_version,
                        runtime_state=runtime_state,
                        progress_callback=progress_callback,
                    )
                except TypeError as exc:
                    if "runtime_state" not in str(exc) and "progress_callback" not in str(exc):
                        raise
                    result = await engine.run_rules_backtest(
                        session=session,
                        rule_ids=rule_ids,
                        start_date=start_date,
                        end_date=end_date,
                        min_confidence=min_confidence,
                        market_regime_version=market_regime_version,
                        progress_callback=progress_callback,
                    )
        except Exception as e:
            logger = __import__("logging").getLogger(__name__)
            logger.error("rule pool backtest failed: %s", e, exc_info=True)
            return ServiceResult(
                status="error",
                message=f"rule pool backtest failed: {e!s}",
                payload={
                    "profile_id": str(profile_id).strip() if profile_id is not None and str(profile_id).strip() else None,
                    "config_path": str(config_path) if config_path is not None else None,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "rule_ids": rule_ids,
                    "min_confidence": min_confidence,
                    "market_regime_version": market_regime_version,
                },
            )

        return ServiceResult(
            status="ok",
            message="rule pool backtest completed",
            payload={
                "profile_id": str(profile_id).strip() if profile_id is not None and str(profile_id).strip() else None,
                "config_path": str(config_path) if config_path is not None else None,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "rule_ids": rule_ids,
                "min_confidence": min_confidence,
                "market_regime_version": market_regime_version,
                "summary": _to_plain(result.summary),
                "regime_version": result.regime_version,
                "source_feature_version": result.source_feature_version,
                "result": _to_plain(result),
                "record_count": len(result.records),
            },
        )
