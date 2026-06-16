from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace


def _write_json(path: Path, data: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def test_optimize_service_filters_advices_and_builds_candidate(tmp_path: Path) -> None:
    """OptimizeService 应支持筛选、建议和候选版本生成。"""
    from src.backtest.schemas import BacktestResult, BacktestSummary
    from src.backtest.schemas import RuleValidationResult
    from src.services.optimize_service import OptimizeService

    backtest_results = {
        "trader_a": BacktestResult(
            request_trader_id="trader_a",
            request_date_from=date(2026, 4, 1),
            request_date_to=date(2026, 4, 10),
            records=[],
            summary=BacktestSummary(
                total_days=10,
                total_trades=20,
                valid_trades=12,
                skipped_trades=8,
                win_rate=0.6,
                avg_return_pct=0.04,
            ),
        )
    }
    validations = {
        "trader_a": [
                RuleValidationResult(
                    trader_id="trader_a",
                    strategy_version_id="sv-001",
                    rule_id="rule-001",
                    rule_text="rsi < 30",
                    programmable=True,
                    validation_status="validated",
                    hit_count=2,
                    sample_count=5,
                    hit_rate=0.2,
                    posterior_return_mean=0.02,
                    posterior_return_median=0.015,
                )
            ]
        }

    parent_path = _write_json(
        tmp_path / "parent.json",
        {
            "version_id": "parent-001",
            "trader_id": "trader_a",
            "strategy_date": "2026-04-01",
            "status": "released",
                "version_type": "manual",
            "parent_version_id": None,
            "rules_snapshot": [
                {"rule_id": "rule-001", "action": {"stop_loss": 10}},
                {"rule_id": "rule-002", "action": {"stop_loss": 8}},
            ],
            "recommendations": [],
            "notes": "",
        },
    )
    adjustments_path = _write_json(
        tmp_path / "adjustments.json",
        [
            {
                "trader_id": "trader_a",
                "rule_id": "rule-001",
                "rule_text": "rsi < 30",
                "current_status": "hit_rate_too_low_and_return_negative",
                "suggestion": "建议删除该规则",
                "confidence": 0.8,
                "hit_rate": 0.4,
                "posterior_return_mean": -0.02,
                "posterior_return_median": -0.01,
            }
        ],
    )

    service = OptimizeService()
    filtered = service.filter_active_traders(backtest_results=backtest_results, rule_validations=validations)
    advised = service.advise_rule_validations(validations["trader_a"])
    candidate = asyncio.run(
        service.create_candidate(
            parent_path=parent_path,
            adjustments_path=adjustments_path,
        )
    )

    assert filtered.payload["results"][0]["trader_id"] == "trader_a"
    assert advised.payload["adjustments"][0]["rule_id"] == "rule-001"
    assert candidate.payload["version"]["version_type"] == "candidate"
    assert candidate.payload["summary"]["deleted_rules"] == ["rule-001"]


def test_optimize_service_db_candidate_flow(tmp_path: Path) -> None:
    """OptimizeService 应支持 DB 候选版本创建。"""
    from src.services.optimize_service import OptimizeService

    @dataclass
    class _FakeReleasedVersion:
        version_id: str = "released-001"

    @dataclass
    class _FakeCandidate:
        version_id: str = "candidate-001"
        trader_id: str = "trader_a"
        strategy_date: date = date(2026, 4, 1)
        status: str = "draft"
        version_type: str = "candidate"
        parent_version_id: str = "released-001"
        rules_snapshot: list[dict] | None = None
        notes: str = ""

    class _FakeStrategyService:
        def __init__(self) -> None:
            self.calls: list[tuple[str, object]] = []

        async def get_current_released_version(self, session, trader_id: str, strategy_date: date):
            self.calls.append(("get_current_released_version", trader_id))
            return _FakeReleasedVersion()

        async def create_candidate_version(self, session, trader_id: str, strategy_date: date, parent_version_id: str, adjustments, recommendations):
            self.calls.append(("create_candidate_version", trader_id))
            return _FakeCandidate(rules_snapshot=[{"rule_id": "rule-001"}])

    def _session_scope_factory():
        return _FakeSession()

    class _FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def commit(self):
            return None

    adjustments_path = _write_json(
        tmp_path / "adjustments.json",
        {
            "adjustments": [
                {
                    "trader_id": "trader_a",
                    "rule_id": "rule-001",
                    "rule_text": "rsi < 30",
                    "current_status": "hit_rate_too_low_and_return_negative",
                    "suggestion": "建议删除该规则",
                    "confidence": 0.8,
                    "hit_rate": 0.4,
                    "posterior_return_mean": -0.02,
                    "posterior_return_median": -0.01,
                }
            ]
        },
    )

    service = OptimizeService(
        strategy_service_factory=_FakeStrategyService,
        session_scope_factory=_session_scope_factory,
    )
    result = asyncio.run(
        service.create_candidate(
            trader_id="trader_a",
            strategy_date=date(2026, 4, 1),
            adjustments_path=adjustments_path,
            use_db=True,
        )
    )

    assert result.status == "ok"
    assert result.payload["candidate"]["version_id"] == "candidate-001"
    assert result.payload["candidate"]["version_type"] == "candidate"


def test_optimize_service_reviews_candidate_version(tmp_path: Path) -> None:
    """OptimizeService 应能把候选审核回写到策略库。"""
    from src.services.optimize_service import OptimizeService
    from src.strategy_library.schemas import StrategyRecommendation, StrategyVersion, StrategyVersionStatus, StrategyVersionType

    class _FakeStrategyService:
        def __init__(self) -> None:
            self.saved: list[StrategyVersion] = []

        async def get_version(self, session, version_id: str):
            del session, version_id
            return StrategyVersion(
                version_id="trader_a_2026-04-01_candidate_12345678",
                trader_id="trader_a",
                strategy_date=date(2026, 4, 1),
                status=StrategyVersionStatus.draft,
                version_type=StrategyVersionType.candidate,
                parent_version_id="released-001",
                recommendations=[StrategyRecommendation(symbol="000001.SZ", decision="buy", confidence=0.8)],
                source_article_ids=["article-1"],
                evidence_refs=["evidence-1"],
                notes="seed notes",
                released_at=None,
                rules_snapshot=[{"rule_id": "rule-001"}],
            )

        async def save_version(self, session, version: StrategyVersion):
            del session
            self.saved.append(version)

    class _FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def commit(self):
            return None

    service = OptimizeService(
        strategy_service_factory=_FakeStrategyService,
        session_scope_factory=lambda: _FakeSession(),
    )
    result = asyncio.run(
        service.review_candidate(
            candidate_version_id="trader_a_2026-04-01_candidate_12345678",
            decision="approve",
            reviewed_by="web",
            force=True,
        )
    )

    assert result.status == "ok"
    assert result.payload["review_status"] == "released"
    assert result.payload["candidate"]["status"] == "released"
    assert "reviewed_by=web" in result.payload["candidate"]["notes"]


def test_rule_pool_service_lists_rules_and_rejects_legacy_review_writes() -> None:
    """RulePoolService 查询保留，但 legacy 审核写入必须拒绝。"""
    from src.services.rule_pool_service import RulePoolService

    class _FakeRule:
        def __init__(self, rule_id: str, review_status: str = "pending", mapped: bool = True) -> None:
            self.rule_id = rule_id
            self.rule_type = "entry"
            self.source_type = "standalone"
            self.instrument_focus = "mixed"
            self.extraction_layer = {"mapped_condition": {"op": "gt"} if mapped else None}
            self.mapping_status = "mapped" if mapped else "unmapped"
            self.mapped_by = "mapper"
            self.mapped_at = datetime(2026, 4, 1)
            self.initial_confidence = 0.8
            self.validated_confidence = 0.7
            self.review_status = review_status
            self.reviewed_by = None
            self.reviewed_at = None
            self.backtest_triggered_at = None
            self.backtest_result = {"hit_rate": 0.4}
            self.backtest_hits = 2
            self.backtest_misses = 3
            self.backtest_samples = 5
            self.used_in_prediction = False
            self.prediction_count = 0
            self.last_used_at = None

    class _FakeRepo:
        def __init__(self) -> None:
            self.review_calls: list[tuple[str, str, str, bool]] = []

        async def get_rules_by_status(self, review_status=None, mapping_status=None, limit: int = 100):
            return [_FakeRule("rule-001"), _FakeRule("rule-002", mapped=False)]

        async def get_rule_by_id(self, rule_id: str):
            if rule_id == "missing":
                return None
            return _FakeRule(rule_id)

        async def update_review(self, rule_id: str, review_status, reviewed_by: str, force: bool = False):
            self.review_calls.append((rule_id, review_status.value, reviewed_by, force))
            return True

    class _FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

    repo = _FakeRepo()
    service = RulePoolService(
        repo_factory=lambda session: repo,
        session_scope_factory=lambda: _FakeSession(),
    )

    listed = asyncio.run(service.list_rules(limit=10))
    shown = asyncio.run(service.show_rule("rule-001"))
    reviewed = asyncio.run(service.review_rule("rule-001", decision="approve", force=True, reviewed_by="web_user"))
    batch = asyncio.run(service.review_batch(decision="reject", status="pending", limit=2, force=False, reviewed_by="web_user"))

    assert len(listed.payload["rules"]) == 2
    assert shown.payload["rule"]["rule_id"] == "rule-001"
    assert reviewed.status == "error"
    assert reviewed.payload["status"] == "compatibility_only"
    assert batch.status == "error"
    assert batch.payload["status"] == "compatibility_only"
    assert repo.review_calls == []
