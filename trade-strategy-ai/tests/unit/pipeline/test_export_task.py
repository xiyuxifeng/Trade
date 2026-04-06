from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import tempfile

import pytest

from src.pipeline.tasks.export_task import (
    ExportStats,
    _ensure_export_state_table,
    _get_watermark,
    _set_watermark,
    WATERMARK_KEY,
)


class TestWatermarkFunctions:
    def test_ensure_export_state_table_creates_table(self, tmp_path: Path) -> None:
        import duckdb
        db_path = tmp_path / "test.duckdb"
        conn = duckdb.connect(str(db_path))
        try:
            _ensure_export_state_table(conn)
            result = conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_name = 'export_state'"
            ).fetchone()
            assert result is not None
        finally:
            conn.close()

    def test_get_watermark_returns_none_when_empty(self, tmp_path: Path) -> None:
        import duckdb
        db_path = tmp_path / "test.duckdb"
        conn = duckdb.connect(str(db_path))
        _ensure_export_state_table(conn)
        try:
            watermark = _get_watermark(conn)
            assert watermark is None
        finally:
            conn.close()

    def test_set_and_get_watermark(self, tmp_path: Path) -> None:
        import duckdb
        db_path = tmp_path / "test.duckdb"
        conn = duckdb.connect(str(db_path))
        _ensure_export_state_table(conn)
        try:
            ts = datetime(2026, 4, 6, 10, 0, 0, tzinfo=timezone.utc)
            _set_watermark(conn, ts)
            retrieved = _get_watermark(conn)
            assert retrieved is not None
            assert retrieved.year == 2026
            assert retrieved.month == 4
            assert retrieved.day == 6
        finally:
            conn.close()

    def test_watermark_key_is_correct(self) -> None:
        assert WATERMARK_KEY == "articles_crawled_at"


class TestExportStatsWatermarks:
    def test_export_stats_default_watermarks_none(self) -> None:
        stats = ExportStats()
        assert stats.watermark_before is None
        assert stats.watermark_after is None

    def test_export_stats_watermarks_settable(self) -> None:
        ts = datetime(2026, 4, 6, 10, 0, 0, tzinfo=timezone.utc)
        stats = ExportStats(watermark_before=ts, watermark_after=ts)
        assert stats.watermark_before == ts
        assert stats.watermark_after == ts