from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.strategy_regime_selection import RegimeRuleSelection, StrategyRegimeSelection


def _build_selection_session(tmp_path: Path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'selections.db'}")

    async def _init_schema() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(StrategyRegimeSelection.__table__.create)
            await conn.run_sync(RegimeRuleSelection.__table__.create)

    asyncio.run(_init_schema())

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    @asynccontextmanager
    async def _session_scope():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    return _session_scope, engine


def test_strategy_regime_selection_repository_persists_summary_and_rules(tmp_path: Path) -> None:
    from src.db.repositories import RegimeRuleSelectionRepository, StrategyRegimeSelectionRepository

    session_scope, engine = _build_selection_session(tmp_path)
    selection_repo = StrategyRegimeSelectionRepository()
    rule_repo = RegimeRuleSelectionRepository()

    async def _run() -> None:
        summary = StrategyRegimeSelection(
            selection_id="sel-1",
            strategy_version_id="sv-1",
            snapshot_id="snap-1",
            market_regime_version="market-regime-v3",
            source_feature_version="market-regime-features-v3",
            applicability_profile_version="rule-applicability-v1",
            selected_rule_count=2,
            skipped_rule_count=1,
            blocked_rule_count=1,
            confidence=0.88,
            quality_status="ok",
            selection_reason="test",
            evidence_json=["evidence-1"],
            override_json={"override": True},
            selected_by="web",
            storage_ref={"source": "file"},
            artifact_ref={"artifact_type": "regime-rule-selection-json"},
        )
        rules = [
            RegimeRuleSelection(
                item_id="sel-1:rule-1",
                selection_id="sel-1",
                rule_id="rule-1",
                decision="applicable",
                score=0.91,
                reason="ok",
                evidence_json=["evidence-1"],
                regime_version="market-regime-v3",
                applicability_profile_version="rule-applicability-v1",
                sample_count=12,
                profile_confidence=0.9,
                override_applied=False,
                rule_applicability_profile_id="profile-1",
            ),
            RegimeRuleSelection(
                item_id="sel-1:rule-2",
                selection_id="sel-1",
                rule_id="rule-2",
                decision="blocked",
                score=0.0,
                reason="blocked",
                evidence_json=["evidence-2"],
                regime_version="market-regime-v3",
                applicability_profile_version="rule-applicability-v1",
                sample_count=8,
                profile_confidence=0.82,
                override_applied=False,
                rule_applicability_profile_id="profile-2",
            ),
        ]

        async with session_scope() as session:
            saved = await selection_repo.upsert_selection(session, summary)
            assert saved.selection_id == "sel-1"
            await rule_repo.replace_for_selection(session, selection_id="sel-1", items=rules)

        async with session_scope() as session:
            loaded = await selection_repo.get_by_selection_id(session, "sel-1")
            assert loaded is not None
            assert loaded.selected_rule_count == 2
            listed = await rule_repo.list_by_selection_id(session, "sel-1")
            assert len(listed) == 2
            assert listed[0].rule_id == "rule-1"
            counted = await selection_repo.count_selections(session, strategy_version_id="sv-1", snapshot_id="snap-1")
            assert counted == 1

    asyncio.run(_run())
    asyncio.run(engine.dispose())
