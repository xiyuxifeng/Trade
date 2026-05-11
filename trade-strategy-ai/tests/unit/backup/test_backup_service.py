from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.backup.service import backup_project_state, restore_project_state
from src.models import ArticleMetadata, BlogArticle, OHLCVBar, TradeLog


async def _create_sqlite_schema(engine) -> None:
    async with engine.begin() as conn:
        await conn.exec_driver_sql(
            """
            CREATE TABLE blog_articles (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                source_article_id TEXT,
                source_url TEXT NOT NULL,
                title TEXT NOT NULL,
                author_name TEXT,
                author_id TEXT,
                published_at TEXT,
                crawled_at TEXT NOT NULL,
                content_text TEXT NOT NULL,
                content_html TEXT,
                summary TEXT,
                tags JSON NOT NULL DEFAULT '[]',
                content_hash TEXT,
                view_count INTEGER NOT NULL DEFAULT 0,
                like_count INTEGER NOT NULL DEFAULT 0,
                bookmark_count INTEGER NOT NULL DEFAULT 0,
                comment_count INTEGER NOT NULL DEFAULT 0,
                comments_payload JSON NOT NULL DEFAULT '[]',
                raw_payload JSON NOT NULL DEFAULT '{}',
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        await conn.exec_driver_sql(
            """
            CREATE TABLE article_metadata (
                id TEXT PRIMARY KEY,
                article_id TEXT NOT NULL UNIQUE,
                schema_version TEXT NOT NULL,
                processed_at TEXT,
                extracted_concepts JSON NOT NULL DEFAULT '[]',
                trading_symbols JSON NOT NULL DEFAULT '[]',
                strategy_rules JSON NOT NULL DEFAULT '[]',
                preconditions JSON NOT NULL DEFAULT '[]',
                comment_insights JSON NOT NULL DEFAULT '[]',
                raw_llm_output JSON NOT NULL DEFAULT '{}',
                sentiment_score NUMERIC,
                confidence_score NUMERIC,
                provider TEXT,
                model TEXT,
                article_type TEXT,
                extraction_version TEXT,
                standalone_rule_ids JSON,
                derived_rule_ids JSON,
                trade_sample_ids JSON,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        await conn.exec_driver_sql(
            """
            CREATE TABLE ohlcv_bars (
                id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                open NUMERIC NOT NULL,
                high NUMERIC NOT NULL,
                low NUMERIC NOT NULL,
                close NUMERIC NOT NULL,
                volume NUMERIC NOT NULL,
                turnover NUMERIC,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        await conn.exec_driver_sql(
            """
            CREATE TABLE trade_logs (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                external_id TEXT,
                account_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                market TEXT NOT NULL,
                side TEXT NOT NULL,
                position_side TEXT NOT NULL,
                order_type TEXT,
                executed_at TEXT NOT NULL,
                quantity NUMERIC NOT NULL,
                price NUMERIC NOT NULL,
                amount NUMERIC NOT NULL,
                fee NUMERIC NOT NULL,
                currency TEXT NOT NULL,
                strategy_tag TEXT,
                rationale TEXT,
                article_id TEXT,
                raw_payload JSON NOT NULL DEFAULT '{}',
                created_at TEXT,
                updated_at TEXT
            )
            """
        )


@pytest.mark.asyncio
async def test_backup_and_restore_roundtrip(tmp_path: Path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    await _create_sqlite_schema(engine)
    audit_record = AsyncMock(return_value=SimpleNamespace(id="audit-1"))
    audit_service = SimpleNamespace(record=audit_record)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        article = BlogArticle(
            source="tgb",
            source_url="https://example.com/a/1",
            title="Example article title",
            author_name="Author",
            author_id="10461311",
            crawled_at=datetime.now(UTC),
            content_text="A" * 200,
            content_html="<p>A</p>",
            content_hash="hash-1",
            raw_payload={"trader_id": "trader_a"},
        )
        session.add(article)
        await session.flush()
        session.add(
            ArticleMetadata(
                article_id=article.id,
                version="v1",
                processed_at=datetime.now(UTC),
                extracted_concepts=[{"name": "trend"}],
                trading_symbols=["000001.SZ"],
                strategy_rules=[{"name": "rule"}],
                preconditions=[{"name": "pre"}],
                comment_insights=[],
                raw_llm_output={},
                sentiment_score=Decimal("0.100"),
                confidence_score=Decimal("0.900"),
            )
        )
        session.add(
            OHLCVBar(
                symbol="000001.SZ",
                trade_date=datetime.now(UTC).date(),
                open=10.0,
                high=10.5,
                low=9.8,
                close=10.2,
                volume=1000.0,
                turnover=10200.0,
            )
        )
        session.add(
            TradeLog(
                source="seed_data",
                account_id="acct-1",
                symbol="000001.SZ",
                market="CN",
                side="buy",
                position_side="long",
                executed_at=datetime.now(UTC),
                quantity=Decimal("100"),
                price=Decimal("10"),
                amount=Decimal("1000"),
                fee=Decimal("0"),
                currency="CNY",
                raw_payload={"trader_id": "trader_a"},
            )
        )
        await session.commit()

    processed_dir = tmp_path / "data" / "processed" / "phase0"
    processed_dir.mkdir(parents=True, exist_ok=True)
    (processed_dir / "sample.txt").write_text("hello", encoding="utf-8")
    artifacts_dir = tmp_path / "data" / "artifacts" / "run-1"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / "report.json").write_text("{\"status\": \"ok\"}", encoding="utf-8")

    backup_dir = tmp_path / "backup"
    backup_stats = await backup_project_state(
        base_dir=tmp_path,
        backup_dir=backup_dir,
        engine=engine,
        audit_service=audit_service,
    )
    assert backup_stats.processed_copied is True
    assert (backup_dir / "manifest.json").exists()
    assert (backup_dir / "db" / "blog_articles.json").exists()
    assert (backup_dir / "processed" / "phase0" / "sample.txt").exists()
    assert (backup_dir / "artifacts" / "run-1" / "report.json").exists()
    audit_record.assert_awaited_once()
    assert audit_record.call_args.kwargs["event_type"] == "backup_project_state"

    async with engine.begin() as conn:
        for table in reversed([BlogArticle.__table__, ArticleMetadata.__table__, OHLCVBar.__table__, TradeLog.__table__]):
            await conn.execute(delete(table))

    restored = await restore_project_state(
        base_dir=tmp_path,
        backup_dir=backup_dir,
        engine=engine,
        force=True,
        audit_service=audit_service,
    )
    assert restored.processed_restored is True
    assert restored.row_counts["blog_articles"] == 1
    assert restored.row_counts["article_metadata"] == 1
    assert restored.row_counts["ohlcv_bars"] == 1
    assert restored.row_counts["trade_logs"] == 1

    async with engine.connect() as conn:
        article_count = await conn.scalar(select(func.count()).select_from(BlogArticle))
        metadata_count = await conn.scalar(select(func.count()).select_from(ArticleMetadata))
        market_count = await conn.scalar(select(func.count()).select_from(OHLCVBar))
        trade_count = await conn.scalar(select(func.count()).select_from(TradeLog))

    assert article_count == 1
    assert metadata_count == 1
    assert market_count == 1
    assert trade_count == 1
    assert (processed_dir / "sample.txt").read_text(encoding="utf-8") == "hello"
    assert (artifacts_dir / "report.json").read_text(encoding="utf-8") == "{\"status\": \"ok\"}"
    assert audit_record.await_count == 2
    assert audit_record.call_args.kwargs["event_type"] == "restore_project_state"
