from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from uuid import UUID, uuid4

from src.backtest.schemas import BacktestResult, RegimeBacktestMetric
from src.common.paths import resolve_project_path
from src.db.repositories import RuleApplicabilityRepository
from src.models.rule_applicability import RuleApplicabilityProfile
from src.domain.enums import FormalLifecycleState
from src.models.stage2_canonical import RuleApplicabilityResultStatus
from src.services.base import BaseService, ServiceResult
from src.services.job_service import JobService
from src.common.stage2_writer_routing import canonical_write_scope

DEFAULT_PROFILE_VERSION = "rule-applicability-v1"
DEFAULT_MIN_SAMPLE_COUNT = 5
FORMAL_PROFILE_VERSION = "rule-applicability-stage6-v1"
FORMAL_RECOMMENDATION_POLICY_VERSION = "rule-applicability-policy-v1"
FORMAL_MIN_SAMPLE_COUNT = 5
FORMAL_MIN_COVERAGE = 0.5


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


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


def _coerce_backtest_result(value: Any) -> BacktestResult:
    """把字典或 dataclass 恢复为 BacktestResult。"""
    if isinstance(value, BacktestResult):
        return value
    if not isinstance(value, dict):
        if hasattr(value, "__dict__"):
            value = dict(vars(value))
        else:
            raise TypeError(f"Unsupported backtest result type: {type(value)!r}")
    raw_rule_regime_metrics = value.get("rule_regime_metrics") or {}
    rule_regime_metrics: dict[str, list[RegimeBacktestMetric]] = {}
    if isinstance(raw_rule_regime_metrics, dict):
        for rule_id, metrics in raw_rule_regime_metrics.items():
            rule_regime_metrics[str(rule_id)] = [_coerce_regime_metric(item) for item in (metrics or [])]
    return BacktestResult(
        request_trader_id=value.get("request_trader_id") or value.get("trader_id") or "",
        request_date_from=_parse_date(value.get("request_date_from") or value.get("date_from")),
        request_date_to=_parse_date(value.get("request_date_to") or value.get("date_to")),
        benchmark_symbol=value.get("benchmark_symbol"),
        regime_version=value.get("regime_version"),
        source_feature_version=value.get("source_feature_version"),
        records=[],
        summary=None,
        regime_metrics=[_coerce_regime_metric(item) for item in value.get("regime_metrics", [])],
        rule_regime_metrics=rule_regime_metrics,
        result_version=value.get("result_version", "1.0"),
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


def _parse_date(value: Any):
    """把字符串日期恢复成 date。"""
    from datetime import date

    if isinstance(value, date):
        return value
    if value in {None, ""}:
        raise ValueError("backtest result missing date")
    return date.fromisoformat(str(value))


def _score_metric(metric: RegimeBacktestMetric) -> float:
    """计算单个 regime 的适用性分数。"""
    score = 0.0
    if metric.win_rate is not None:
        score += (metric.win_rate - 0.5) * 2.0
    if metric.avg_return is not None:
        score += metric.avg_return * 4.0
    if metric.profit_factor is not None:
        score += (metric.profit_factor - 1.0) * 0.8
    if metric.max_drawdown is not None:
        score -= abs(metric.max_drawdown) * 1.5
    score *= 0.6 + min(metric.sample_count, 50) / 100.0
    score *= 0.7 + max(0.0, min(metric.confidence, 1.0)) * 0.3
    return round(score, 4)


def _format_pct(value: float | None) -> str:
    """格式化百分比。"""
    if value is None:
        return "n/a"
    return f"{value:.2%}"


def _build_evidence(metric: RegimeBacktestMetric) -> list[str]:
    """构造证据说明。"""
    evidence = [f"sample_count={metric.sample_count}"]
    if metric.win_rate is not None:
        evidence.append(f"win_rate={_format_pct(metric.win_rate)}")
    if metric.avg_return is not None:
        evidence.append(f"avg_return={_format_pct(metric.avg_return)}")
    if metric.max_drawdown is not None:
        evidence.append(f"max_drawdown={_format_pct(metric.max_drawdown)}")
    if metric.profit_factor is not None:
        evidence.append(f"profit_factor={metric.profit_factor:.2f}")
    evidence.append(f"confidence={metric.confidence:.2f}")
    return evidence


def _classify_metric(metric: RegimeBacktestMetric, *, min_sample_count: int) -> dict[str, Any]:
    """把 regime metric 分类为 applicable / blocked / neutral。"""
    score = _score_metric(metric)
    low_sample = metric.sample_count < min_sample_count or metric.low_sample
    if low_sample:
        decision = "neutral"
        reason = f"样本不足，样本数 {metric.sample_count} 低于阈值 {min_sample_count}"
    elif score >= 0.25:
        decision = "applicable"
        reason = "胜率、收益和回撤综合表现较优"
    elif score <= -0.15:
        decision = "blocked"
        reason = "收益、胜率或回撤表现较差"
    else:
        decision = "neutral"
        reason = "表现接近均衡区间，保留观察"

    return {
        "regime_label": metric.regime_label,
        "decision": decision,
        "score": score,
        "sample_count": metric.sample_count,
        "win_rate": metric.win_rate,
        "avg_return": metric.avg_return,
        "avg_win_return": metric.avg_win_return,
        "avg_loss_return": metric.avg_loss_return,
        "max_drawdown": metric.max_drawdown,
        "profit_factor": metric.profit_factor,
        "confidence": metric.confidence,
        "low_sample": low_sample,
        "reason": reason,
        "evidence": _build_evidence(metric),
    }


def _build_market_conditions(entries: list[dict[str, Any]], *, kind: str) -> dict[str, Any]:
    """把排序后的 regime 条目整理成 market conditions 说明。"""
    if not entries:
        return {
            "summary": "暂无明确条件",
            "regimes": [],
            "basis": [],
        }
    basis = {
        "applicable": ["高胜率", "正收益", "较低回撤"],
        "blocked": ["低胜率", "负收益", "较高回撤"],
    }.get(kind, ["样本证据"])
    return {
        "summary": entries[0]["reason"],
        "regimes": entries[:3],
        "basis": basis,
    }


async def _load_backtest_result_payload(source_backtest_id: str) -> dict[str, Any]:
    """从 Job DB 读取回测结果。"""
    job_result = await JobService().get_job(source_backtest_id)
    if job_result.status != "ok":
        raise FileNotFoundError(source_backtest_id)
    job = job_result.payload.get("job")
    if not isinstance(job, dict):
        raise FileNotFoundError(source_backtest_id)
    result = job.get("result")
    if not isinstance(result, dict):
        raise FileNotFoundError(source_backtest_id)
    payload = result.get("payload")
    if isinstance(payload, dict):
        nested_result = payload.get("result")
        if isinstance(nested_result, dict):
            return nested_result
        return payload
    return result


class RuleApplicabilityService(BaseService):
    """Rule 适用性画像生成与查询服务。"""

    service_name = "rule-applicability"

    def __init__(
        self,
        *,
        session_scope_factory: Callable[[], Any] | None = None,
        repo_factory: Callable[[], RuleApplicabilityRepository] = RuleApplicabilityRepository,
        artifact_root: str | Path | None = None,
    ) -> None:
        self._session_scope_factory = session_scope_factory
        self._repo_factory = repo_factory
        self._artifact_root = Path(artifact_root).expanduser().resolve() if artifact_root is not None else resolve_project_path("data/processed/rule_applicability")

    def _ensure_session_factory(self) -> Callable[[], Any]:
        """确保存在 session_scope 工厂。"""
        if self._session_scope_factory is not None:
            return self._session_scope_factory
        from src.db.session import session_scope

        self._session_scope_factory = session_scope
        return session_scope

    def _artifact_path(self, *, rule_id: str, profile_version: str, source_backtest_id: str) -> Path:
        """返回 profile artifact 路径。"""
        return self._artifact_root / rule_id / profile_version / f"{source_backtest_id}.json"

    def _artifact_ref(self, artifact_path: Path) -> dict[str, Any]:
        """返回 artifact 的安全引用。"""
        try:
            relative = artifact_path.relative_to(self._artifact_root)
        except ValueError:
            relative = artifact_path.name
        return {
            "artifact_type": "rule-applicability-json",
            "artifact_root": str(self._artifact_root.name or "rule_applicability"),
            "relative_path": str(relative),
        }

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

    def _extract_rule_metrics(self, backtest_result: BacktestResult, rule_id: str) -> list[RegimeBacktestMetric]:
        """提取 rule 对应的 regime metrics。"""
        metrics = backtest_result.rule_regime_metrics.get(rule_id)
        if metrics:
            return list(metrics)
        return list(backtest_result.regime_metrics)

    def _build_profile_payload(
        self,
        *,
        rule_id: str,
        source_backtest_id: str,
        backtest_result: BacktestResult,
        profile_version: str,
        min_sample_count: int,
        review_status: str,
        reviewed_by: str | None,
    ) -> dict[str, Any]:
        """把回测结果转成 profile payload。"""
        metrics = self._extract_rule_metrics(backtest_result, rule_id)
        if not metrics:
            raise ValueError(f"rule {rule_id} has no regime metrics in backtest result")

        classified = [_classify_metric(metric, min_sample_count=min_sample_count) for metric in metrics]
        applicable = sorted(
            [item for item in classified if item["decision"] == "applicable"],
            key=lambda item: (item["score"], item["confidence"], item["sample_count"]),
            reverse=True,
        )
        blocked = sorted(
            [item for item in classified if item["decision"] == "blocked"],
            key=lambda item: (item["score"], item["confidence"], item["sample_count"]),
        )
        neutral = sorted(
            [item for item in classified if item["decision"] == "neutral"],
            key=lambda item: (item["score"], item["confidence"], item["sample_count"]),
            reverse=True,
        )

        considered = [item for item in classified if not item["low_sample"]]
        weighted_confidence = 0.0
        total_weight = 0.0
        for item in considered or classified:
            weight = float(item["sample_count"] or 1)
            weighted_confidence += float(item["confidence"]) * weight
            total_weight += weight
        base_confidence = weighted_confidence / total_weight if total_weight else 0.0
        coverage_ratio = len(considered) / max(len(classified), 1)
        confidence = min(1.0, max(0.0, base_confidence * 0.7 + coverage_ratio * 0.3))

        summary = {
            "rule_id": rule_id,
            "profile_version": profile_version,
            "source_backtest_id": source_backtest_id,
            "market_regime_version": backtest_result.regime_version,
            "source_feature_version": backtest_result.source_feature_version,
            "decision_counts": {
                "applicable": len(applicable),
                "blocked": len(blocked),
                "neutral": len(neutral),
            },
            "total_regimes": len(classified),
            "considered_regimes": len(considered),
            "low_sample_regimes": len([item for item in classified if item["low_sample"]]),
            "confidence_basis": "weighted_metric_confidence + coverage_ratio",
            "backtest_result_version": backtest_result.result_version,
        }
        return {
            "rule_id": rule_id,
            "profile_version": profile_version,
            "source_backtest_id": source_backtest_id,
            "source_rule_version": None,
            "market_regime_version": backtest_result.regime_version,
            "source_feature_version": backtest_result.source_feature_version,
            "review_status": review_status,
            "min_sample_count": min_sample_count,
            "confidence": round(confidence, 4),
            "applicable_regimes": applicable,
            "blocked_regimes": blocked,
            "neutral_regimes": neutral,
            "best_market_conditions": _build_market_conditions(applicable or neutral or classified, kind="applicable"),
            "worst_market_conditions": _build_market_conditions(blocked or neutral or classified[::-1], kind="blocked"),
            "summary": summary,
            "reviewed_by": reviewed_by,
        }

    async def build_profile(
        self,
        *,
        rule_id: str,
        source_backtest_id: str,
        profile_version: str = DEFAULT_PROFILE_VERSION,
        min_sample_count: int = DEFAULT_MIN_SAMPLE_COUNT,
        review_status: str = "draft",
        reviewed_by: str | None = None,
        backtest_result: BacktestResult | dict[str, Any] | None = None,
    ) -> ServiceResult:
        """基于单次 Regime-aware Backtest 生成 Rule Applicability Profile。"""
        if min_sample_count < 1:
            return self._error(
                status="error",
                error_type="invalid_min_sample_count",
                message="min_sample_count must be >= 1",
                metadata={"min_sample_count": min_sample_count},
            )
        if review_status not in {"draft", "reviewed", "active", "archived"}:
            return self._error(
                status="error",
                error_type="invalid_review_status",
                message="invalid review status",
                metadata={"review_status": review_status},
            )

        try:
            loaded_result = _coerce_backtest_result(
                backtest_result if backtest_result is not None else await _load_backtest_result_payload(source_backtest_id)
            )
        except FileNotFoundError:
            return self._error(
                status="error",
                error_type="backtest_result_not_found",
                message="backtest result not found",
                detail=source_backtest_id,
                metadata={"source_backtest_id": source_backtest_id},
            )
        except Exception as exc:  # noqa: BLE001
            return self._error(
                status="error",
                error_type="backtest_result_invalid",
                message="backtest result invalid",
                detail=str(exc),
                metadata={"source_backtest_id": source_backtest_id},
            )

        try:
            payload = self._build_profile_payload(
                rule_id=rule_id,
                source_backtest_id=source_backtest_id,
                backtest_result=loaded_result,
                profile_version=profile_version,
                min_sample_count=min_sample_count,
                review_status=review_status,
                reviewed_by=reviewed_by,
            )
        except ValueError as exc:
            return self._error(
                status="error",
                error_type="missing_rule_metrics",
                message=str(exc),
                detail=source_backtest_id,
                metadata={"rule_id": rule_id, "source_backtest_id": source_backtest_id},
            )

        profile = RuleApplicabilityProfile(
            rule_id=payload["rule_id"],
            profile_version=payload["profile_version"],
            source_backtest_id=payload["source_backtest_id"],
            source_rule_version=payload["source_rule_version"],
            market_regime_version=payload["market_regime_version"],
            source_feature_version=payload["source_feature_version"],
            review_status=payload["review_status"],
            min_sample_count=payload["min_sample_count"],
            confidence=payload["confidence"],
            applicable_regimes=payload["applicable_regimes"],
            blocked_regimes=payload["blocked_regimes"],
            neutral_regimes=payload["neutral_regimes"],
            best_market_conditions=payload["best_market_conditions"],
            worst_market_conditions=payload["worst_market_conditions"],
            summary=payload["summary"],
            storage_ref={
                "source_backtest_id": source_backtest_id,
                "profile_version": profile_version,
                "artifact_type": "rule-applicability-json",
            },
            reviewed_by=reviewed_by if review_status != "draft" else None,
            reviewed_at=datetime.now(UTC) if review_status != "draft" else None,
        )

        session_scope = self._ensure_session_factory()
        db_warning = False
        saved = profile
        async with session_scope() as session:
            repo = self._repo_factory()
            try:
                with canonical_write_scope("rule_applicability", self.service_name):
                    saved = await repo.upsert_profile(session, profile)
                await session.commit()
            except Exception as exc:  # noqa: BLE001
                db_warning = True
                payload["summary"]["database_warning"] = str(exc)

        artifact_path = self._artifact_path(rule_id=rule_id, profile_version=profile_version, source_backtest_id=source_backtest_id)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_payload = {
            "profile": saved.to_dict(),
            "backtest_result": {
                "request_trader_id": loaded_result.request_trader_id,
                "request_date_from": loaded_result.request_date_from.isoformat(),
                "request_date_to": loaded_result.request_date_to.isoformat(),
                "benchmark_symbol": loaded_result.benchmark_symbol,
                "regime_version": loaded_result.regime_version,
                "source_feature_version": loaded_result.source_feature_version,
                "result_version": loaded_result.result_version,
            },
            "summary": payload["summary"],
            "warnings": ["database persistence failed"] if db_warning else [],
        }
        artifact_path.write_text(json.dumps(_to_plain(artifact_payload), ensure_ascii=False, indent=2), encoding="utf-8")

        result_status = "partial" if db_warning else "ok"
        return ServiceResult(
            status=result_status,
            message="rule applicability profile written" if not db_warning else "rule applicability profile written with database warning",
            payload={
                "profile": saved.to_dict(),
                "artifact_ref": self._artifact_ref(artifact_path),
                "artifact_path": self._artifact_ref(artifact_path)["relative_path"],
                "warnings": ["database persistence failed"] if db_warning else [],
            },
            warnings=["database persistence failed"] if db_warning else [],
        )

    def _formal_error(self, *, error_type: str, message: str, detail: str | None = None, metadata: dict[str, Any] | None = None) -> ServiceResult:
        return self._error(status="error", error_type=error_type, message=message, detail=detail, metadata=metadata)

    def _formal_profile_metrics(self, result: Any) -> dict[str, Any]:
        sample_counts = _get(result, "sample_state_counts", {}) or {}
        buckets = _get(result, "per_market_state_metrics", []) or []
        overall = _get(result, "overall_metrics", {}) or {}
        eligible = int(sample_counts.get("eligible") or sum(int(_get(item, "eligible_sample_count", 0) or 0) for item in buckets))
        evaluated = int(
            sample_counts.get("evaluated_true")
            or sample_counts.get("evaluated")
            or sum(int(_get(item, "evaluated_sample_count", 0) or 0) for item in buckets)
        )
        sample_count = eligible or evaluated
        coverages = [
            float(_get(item, "coverage"))
            for item in buckets
            if _get(item, "coverage") is not None
        ]
        coverage = coverages[0] if len(coverages) == 1 else (sum(coverages) / len(coverages) if coverages else None)
        total_return = overall.get("total_return")
        if total_return is None:
            returns = [float(_get(item, "total_return")) for item in buckets if _get(item, "total_return") is not None]
            total_return = sum(returns) if returns else None
        win_rate = overall.get("win_rate")
        if win_rate is None:
            win_rates = [float(_get(item, "win_rate")) for item in buckets if _get(item, "win_rate") is not None]
            win_rate = sum(win_rates) / len(win_rates) if win_rates else None
        max_drawdown = overall.get("max_drawdown")
        if max_drawdown is None:
            drawdowns = [float(_get(item, "max_drawdown")) for item in buckets if _get(item, "max_drawdown") is not None]
            max_drawdown = min(drawdowns) if drawdowns else None

        insufficient = sample_count < FORMAL_MIN_SAMPLE_COUNT
        insufficient_coverage = coverage is None or coverage < FORMAL_MIN_COVERAGE
        status = _get(result, "status")
        limitations = list(_get(result, "limitations", []) or [])
        warnings = list(_get(result, "warnings", []) or [])
        if status == "completed_invalid":
            recommendation = "invalid"
            confidence = 0.0
            quality = "invalid"
            insufficient_status = "invalid"
        elif insufficient:
            recommendation = "insufficient_sample"
            confidence = min(0.4, max(0.0, sample_count / FORMAL_MIN_SAMPLE_COUNT * 0.4))
            quality = "partial"
            insufficient_status = "insufficient_sample"
        elif insufficient_coverage:
            recommendation = "limited"
            confidence = min(0.6, max(0.0, float(coverage or 0) * 0.8))
            quality = "partial"
            insufficient_status = "insufficient_coverage"
        elif total_return is None or win_rate is None or max_drawdown is None:
            recommendation = "unavailable"
            confidence = 0.0
            quality = "partial"
            insufficient_status = "unavailable"
        elif float(total_return) > 0 and float(win_rate) >= 0.5:
            recommendation = "recommended"
            confidence = min(1.0, max(0.0, float(coverage or 0) * 0.6 + min(sample_count, 50) / 50 * 0.4))
            quality = "complete"
            insufficient_status = "sufficient"
        elif float(total_return) < 0 and float(win_rate) < 0.45:
            recommendation = "not_recommended"
            confidence = min(1.0, max(0.0, float(coverage or 0) * 0.6 + min(sample_count, 50) / 50 * 0.4))
            quality = "complete"
            insufficient_status = "sufficient"
        else:
            recommendation = "limited"
            confidence = min(0.8, max(0.0, float(coverage or 0) * 0.6 + min(sample_count, 50) / 50 * 0.3))
            quality = "partial"
            insufficient_status = "sufficient"

        return {
            "sample_count": sample_count,
            "eligible_sample_count": eligible,
            "evaluated_sample_count": evaluated,
            "coverage": coverage,
            "return_metric": total_return,
            "win_rate": win_rate,
            "maximum_drawdown": max_drawdown,
            "confidence": round(confidence, 4),
            "recommendation_status": recommendation,
            "quality_status": quality,
            "insufficient_sample_status": insufficient_status,
            "limitations": limitations,
            "warnings": warnings,
            "per_market_state_metrics": _to_plain(buckets),
        }

    async def generate_formal_draft(
        self,
        *,
        run_id: str,
        result_id: str | None = None,
        actor_id: str,
        actor_role: str,
        reason: str | None = None,
        source_surface: str = "/rules/results",
    ) -> ServiceResult:
        """Generate a formal Stage 6 draft only from immutable BacktestRun/BacktestResult."""
        if actor_role not in {"operator", "admin"}:
            return self._formal_error(
                error_type="permission_denied",
                message="生成适用性画像草稿需要 operator 权限。",
                metadata={"actor_role": actor_role},
            )
        try:
            parsed_run_id = UUID(str(run_id))
            parsed_result_id = UUID(str(result_id)) if result_id else None
        except ValueError:
            return self._formal_error(
                error_type="invalid_formal_source",
                message="正式适用性画像只能从正式回测运行和结果生成。",
                detail="run_id/result_id must be immutable Stage 6 UUIDs",
                metadata={"run_id": run_id, "result_id": result_id},
            )

        session_scope = self._ensure_session_factory()
        async with session_scope() as session:
            repo = self._repo_factory()
            run = await repo.get_formal_backtest_run(session, run_id=parsed_run_id)
            result = await repo.get_formal_backtest_result(session, result_id=parsed_result_id, run_id=parsed_run_id)
            if run is None or result is None or str(_get(result, "run_id")) != str(parsed_run_id):
                return self._formal_error(
                    error_type="formal_evidence_not_found",
                    message="没有找到可用于生成画像的正式回测证据。",
                    metadata={"run_id": str(parsed_run_id), "result_id": str(parsed_result_id) if parsed_result_id else None},
                )
            if _get(result, "result_fingerprint") in {None, ""}:
                return self._formal_error(
                    error_type="missing_result_fingerprint",
                    message="正式回测结果缺少结果指纹，不能生成画像。",
                    metadata={"run_id": str(parsed_run_id), "result_id": str(_get(result, "result_id"))},
                )

            current = await repo.find_current_formal_profile(session, run=run)
            applicability_profile_id = _get(current, "applicability_profile_id", None) or uuid4()
            version_no = await repo.next_formal_version_no(session, applicability_profile_id=applicability_profile_id)
            metrics = self._formal_profile_metrics(result)
            profile = RuleApplicabilityProfile(
                rule_id=str(_get(run, "rule_version_id") or _get(run, "rule_family_id")),
                profile_version=FORMAL_PROFILE_VERSION,
                source_backtest_id=str(parsed_run_id),
                review_status="draft",
                min_sample_count=FORMAL_MIN_SAMPLE_COUNT,
                confidence=metrics["confidence"],
                applicable_regimes=[],
                blocked_regimes=[],
                neutral_regimes=[],
                summary={
                    "profile_version_no": version_no,
                    "result_status": _get(result, "status"),
                    "sample_state_counts": _to_plain(_get(result, "sample_state_counts", {}) or {}),
                    "coverage": _to_plain(_get(result, "coverage_json", {}) or {}),
                },
                storage_ref={"formal_source": "backtest_runs/backtest_results"},
                applicability_profile_id=applicability_profile_id,
                rule_version_id=_get(run, "rule_version_id"),
                rule_version_fingerprint=_get(run, "rule_version_fingerprint"),
                rule_version_no=_get(run, "rule_version_no"),
                rule_family_id=_get(run, "rule_family_id"),
                rule_family_fingerprint=_get(run, "rule_family_fingerprint"),
                frozen_rule_version_ids=_get(run, "frozen_rule_version_ids", []) or [],
                frozen_rule_version_fingerprints=_get(run, "frozen_rule_version_fingerprints", []) or [],
                dataset_snapshot_id=_get(run, "dataset_snapshot_id"),
                dataset_fingerprint=_get(run, "dataset_fingerprint"),
                market_state_definition_version=_get(run, "market_state_model_version"),
                market_state_model_version=_get(result, "market_state_model_version") or _get(run, "market_state_model_version"),
                market_state_source_version=_get(result, "market_state_source_version"),
                market_snapshot_ids=_get(run, "market_snapshot_ids", []) or [],
                market_snapshot_fingerprints=_get(run, "market_snapshot_fingerprints", []) or [],
                profile_version_no=version_no,
                source_backtest_run_ids=[str(parsed_run_id)],
                source_backtest_result_ids=[str(_get(result, "result_id"))],
                source_result_fingerprints=[str(_get(result, "result_fingerprint"))],
                sample_count=metrics["sample_count"],
                eligible_sample_count=metrics["eligible_sample_count"],
                evaluated_sample_count=metrics["evaluated_sample_count"],
                coverage=metrics["coverage"],
                return_metric=metrics["return_metric"],
                win_rate=metrics["win_rate"],
                maximum_drawdown=metrics["maximum_drawdown"],
                recommendation_status=metrics["recommendation_status"],
                data_level=_get(result, "effective_level"),
                requested_level=_get(result, "requested_level"),
                effective_level=_get(result, "effective_level"),
                level_policy_version=_get(result, "level_policy_version") or _get(run, "level_policy_version"),
                quality_status=metrics["quality_status"],
                insufficient_sample_status=metrics["insufficient_sample_status"],
                limitations=metrics["limitations"],
                warnings=metrics["warnings"],
                recommendation_policy_version=_get(run, "recommendation_policy_version") or FORMAL_RECOMMENDATION_POLICY_VERSION,
                created_by=actor_id,
                supersedes_profile_id=_get(current, "profile_id", None) if current and _get(current, "review_status") != "draft" else None,
            )
            if metrics["quality_status"] == "complete":
                profile.result_status = RuleApplicabilityResultStatus.ready
                profile.lifecycle_state = FormalLifecycleState.draft
            elif metrics["insufficient_sample_status"] == "insufficient_sample":
                profile.result_status = RuleApplicabilityResultStatus.insufficient_sample
            elif metrics["recommendation_status"] == "invalid":
                profile.result_status = RuleApplicabilityResultStatus.invalid
            else:
                profile.result_status = RuleApplicabilityResultStatus.partial

            with canonical_write_scope("rule_applicability", self.service_name):
                saved = await repo.create_formal_profile(session, profile)
                if current and _get(current, "review_status") == "draft":
                    await repo.supersede_profile(session, profile=current, superseded_by=saved.profile_id, actor_id=actor_id, reason=reason)
                await repo.record_audit_event(
                    session,
                    profile=saved,
                    event={
                        "transition": "draft_created",
                        "actor_id": actor_id,
                        "actor_role": actor_role,
                        "reason": reason,
                        "source_surface": source_surface,
                        "before_state": None,
                        "after_state": {
                            "review_status": saved.review_status,
                            "recommendation_status": saved.recommendation_status,
                            "source_backtest_run_ids": saved.source_backtest_run_ids,
                            "source_backtest_result_ids": saved.source_backtest_result_ids,
                        },
                    },
                )
            await session.commit()

        return ServiceResult(status="ok", message="formal rule applicability draft generated", payload={"profile": saved.to_dict()})

    async def review_formal_profile(
        self,
        *,
        profile_id: str,
        review_status: str,
        actor_id: str,
        actor_role: str,
        reason: str | None = None,
        source_surface: str = "/rules/results",
    ) -> ServiceResult:
        """Review a formal applicability profile without publishing rules or strategies."""
        if actor_role not in {"reviewer", "operator", "admin"}:
            return self._formal_error(error_type="permission_denied", message="审核适用性画像需要 reviewer 或 operator 权限。")
        if review_status not in {"pending_review", "approved", "rejected", "invalidated"}:
            return self._formal_error(
                error_type="invalid_review_status",
                message="审核状态无效。",
                metadata={"review_status": review_status},
            )
        try:
            parsed_profile_id = UUID(str(profile_id))
        except ValueError:
            return self._formal_error(error_type="invalid_profile_id", message="画像编号无效。", metadata={"profile_id": profile_id})

        lifecycle_map = {
            "pending_review": FormalLifecycleState.in_review,
            "approved": FormalLifecycleState.approved,
            "rejected": FormalLifecycleState.rejected,
            "invalidated": FormalLifecycleState.archived,
        }
        session_scope = self._ensure_session_factory()
        async with session_scope() as session:
            repo = self._repo_factory()
            row = await repo.get_by_id(session, parsed_profile_id)
            if row is None:
                return self._formal_error(error_type="profile_not_found", message="未找到适用性画像。", metadata={"profile_id": profile_id})
            before = {"review_status": row.review_status, "reviewed_by": row.reviewed_by}
            row.review_status = review_status
            row.lifecycle_state = lifecycle_map[review_status]
            row.reviewed_by = actor_id
            row.reviewed_at = datetime.now(UTC)
            row.review_reason = reason
            with canonical_write_scope("rule_applicability", self.service_name):
                await repo.record_audit_event(
                    session,
                    profile=row,
                    event={
                        "transition": review_status,
                        "actor_id": actor_id,
                        "actor_role": actor_role,
                        "reason": reason,
                        "source_surface": source_surface,
                        "before_state": before,
                        "after_state": {"review_status": review_status, "reviewed_by": actor_id},
                    },
                )
                await session.flush()
            await session.commit()
        return ServiceResult(status="ok", message="formal rule applicability profile reviewed", payload={"profile": row.to_dict()})

    async def list_profiles(
        self,
        *,
        rule_id: str | None = None,
        review_status: str | None = None,
        profile_version: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ServiceResult:
        """列出 Rule Applicability Profile。"""
        if limit < 1 or offset < 0:
            return self._error(
                status="error",
                error_type="invalid_query",
                message="invalid pagination",
                detail="limit must be >= 1 and offset must be >= 0",
                metadata={"limit": limit, "offset": offset},
            )

        session_scope = self._ensure_session_factory()
        async with session_scope() as session:
            repo = self._repo_factory()
            total = await repo.count_profiles(session, rule_id=rule_id, review_status=review_status, profile_version=profile_version)
            rows = await repo.list_profiles(
                session,
                rule_id=rule_id,
                review_status=review_status,
                profile_version=profile_version,
                limit=limit,
                offset=offset,
            )

        items = [row.to_dict() for row in rows]
        return ServiceResult(
            status="ok",
            message="rule applicability profiles listed",
            payload={
                "count": len(items),
                "total": total,
                "skip": offset,
                "limit": limit,
                "items": items,
            },
        )

    async def get_profile(self, profile_id: str) -> ServiceResult:
        """按 profile_id 读取 profile。"""
        session_scope = self._ensure_session_factory()
        async with session_scope() as session:
            repo = self._repo_factory()
            row = await repo.get_by_id(session, profile_id)

        if row is None:
            return self._error(
                status="partial",
                error_type="profile_not_found",
                message="rule applicability profile not found",
                detail=profile_id,
                metadata={"profile_id": profile_id},
            )
        return ServiceResult(status="ok", message="rule applicability profile loaded", payload={"profile": row.to_dict()})

    async def review_profile(
        self,
        *,
        profile_id: str,
        review_status: str,
        reviewed_by: str = "web",
    ) -> ServiceResult:
        """更新 profile 审核状态。"""
        if review_status not in {"draft", "reviewed", "active", "archived"}:
            return self._error(
                status="error",
                error_type="invalid_review_status",
                message="invalid review status",
                metadata={"review_status": review_status},
            )

        session_scope = self._ensure_session_factory()
        async with session_scope() as session:
            repo = self._repo_factory()
            row = await repo.get_by_id(session, profile_id)
            if row is None:
                return self._error(
                    status="partial",
                    error_type="profile_not_found",
                    message="rule applicability profile not found",
                    detail=profile_id,
                    metadata={"profile_id": profile_id},
                )
            row.review_status = review_status
            row.reviewed_by = reviewed_by
            row.reviewed_at = datetime.now(UTC)
            with canonical_write_scope("rule_applicability", self.service_name):
                await session.flush()
            await session.commit()
        return ServiceResult(
            status="ok",
            message="rule applicability profile reviewed",
            payload={"profile_id": profile_id, "review_status": review_status, "reviewed_by": reviewed_by},
        )
