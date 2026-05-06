"""NTL-S7-010: TradeCalendar fallback 测试"""
import pytest
from datetime import date
from pathlib import Path
import tempfile
import json


class TestTradeCalendarFileFallback:
    """本地文件 fallback 测试"""

    def test_load_from_file_success_when_data_sufficient_and_current(self):
        """本地文件数据充足且当前年份 <= 最大年份时，直接使用本地文件"""
        from src.backtest.engine import TradeCalendar

        current_year = date.today().year
        # 生成超过 100 天的充足数据
        dates = [f"{current_year}-01-{i:02d}" for i in range(1, 32)]
        dates.extend([f"{current_year}-02-{i:02d}" for i in range(1, 29)])
        dates.extend([f"{current_year}-03-{i:02d}" for i in range(1, 32)])
        dates.extend([f"{current_year}-04-{i:02d}" for i in range(1, 31)])

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"trade_dates": dates, "_last_updated": "2026-04-29"}, f)
            f.flush()
            path = f.name

        try:
            # 重置类状态（包括 _loaded）
            TradeCalendar._loaded = False
            TradeCalendar._trade_dates = None
            TradeCalendar._source = "none"
            TradeCalendar._last_loaded_at = None

            result = TradeCalendar.load_from_file(path)
            assert result is True
            assert TradeCalendar._source == "file"
            assert len(TradeCalendar._trade_dates) >= 100
        finally:
            Path(path).unlink()

    def test_load_from_file_triggers_refresh_when_new_year(self, monkeypatch):
        """当前年份 > 本地最大年份时，自动从 akshare 刷新"""
        from src.backtest.engine import TradeCalendar

        # 生成本地文件只有 2024 年数据（明显旧于当前）
        old_dates = [f"2024-01-{i:02d}" for i in range(1, 60)]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"trade_dates": old_dates}, f)
            f.flush()
            path = f.name

        try:
            def _fake_load_from_akshare():
                TradeCalendar._trade_dates = {
                    f"{date.today().year}-04-{i:02d}" for i in range(1, 121)
                }
                TradeCalendar._loaded = True
                TradeCalendar._source = "akshare"
                TradeCalendar._last_loaded_at = "2026-05-06T00:00:00+08:00"
                return True

            monkeypatch.setattr(TradeCalendar, "load_from_akshare", classmethod(lambda cls: _fake_load_from_akshare()))
            TradeCalendar._loaded = False
            TradeCalendar._trade_dates = None
            TradeCalendar._source = "none"

            result = TradeCalendar.load_from_file(path)
            assert result is True
            # 应该从 akshare 刷新了数据
            assert len(TradeCalendar._trade_dates) >= 100
        finally:
            Path(path).unlink()

    def test_load_from_file_not_found_triggers_akshare(self, monkeypatch):
        """文件不存在时自动从 akshare 获取"""
        from src.backtest.engine import TradeCalendar

        def _fake_load_from_akshare():
            TradeCalendar._trade_dates = {
                f"{date.today().year}-04-{i:02d}" for i in range(1, 121)
            }
            TradeCalendar._loaded = True
            TradeCalendar._source = "akshare"
            TradeCalendar._last_loaded_at = "2026-05-06T00:00:00+08:00"
            return True

        monkeypatch.setattr(TradeCalendar, "load_from_akshare", classmethod(lambda cls: _fake_load_from_akshare()))

        TradeCalendar._loaded = False
        TradeCalendar._trade_dates = None
        TradeCalendar._source = "none"

        with tempfile.TemporaryDirectory() as tmpdir:
            nonexistent_path = Path(tmpdir) / "nonexistent" / "calendar.json"

            result = TradeCalendar.load_from_file(str(nonexistent_path))
            assert result is True
            assert TradeCalendar._trade_dates is not None
            assert len(TradeCalendar._trade_dates) >= 100

    def test_load_from_file_invalid_json_triggers_akshare(self, monkeypatch):
        """无效 JSON 时自动从 akshare 获取"""
        from src.backtest.engine import TradeCalendar

        def _fake_load_from_akshare():
            TradeCalendar._trade_dates = {
                f"{date.today().year}-04-{i:02d}" for i in range(1, 121)
            }
            TradeCalendar._loaded = True
            TradeCalendar._source = "akshare"
            TradeCalendar._last_loaded_at = "2026-05-06T00:00:00+08:00"
            return True

        monkeypatch.setattr(TradeCalendar, "load_from_akshare", classmethod(lambda cls: _fake_load_from_akshare()))

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json")
            f.flush()
            path = f.name

        try:
            TradeCalendar._loaded = False
            TradeCalendar._trade_dates = None
            TradeCalendar._source = "none"

            result = TradeCalendar.load_from_file(path)
            assert result is True
            assert TradeCalendar._trade_dates is not None
        finally:
            Path(path).unlink()


class TestTradeCalendarEnsureLoaded:
    """ensure_loaded 优先级测试"""

    def test_ensure_loaded_prefers_file_over_akshare(self, monkeypatch):
        """本地文件优先于 akshare（数据够新时）"""
        from src.backtest import engine as backtest_engine
        from src.backtest.engine import TradeCalendar

        current_year = date.today().year
        dates = [f"{current_year}-04-{(i % 28) + 1:02d}" for i in range(150)]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"trade_dates": dates}, f)
            f.flush()
            path = f.name

        try:
            monkeypatch.setattr(backtest_engine, "_DEFAULT_CALENDAR_FILE", path)
            monkeypatch.setattr(TradeCalendar, "load_from_akshare", classmethod(lambda cls: False))
            TradeCalendar._loaded = False
            TradeCalendar._trade_dates = None
            TradeCalendar._source = "none"

            result = TradeCalendar.ensure_loaded()
            assert result is True
            assert TradeCalendar._source == "file"
        finally:
            Path(path).unlink()

    def test_ensure_loaded_falls_back_to_holidays(self):
        """当本地文件不存在且 akshare 失败时，fallback 到 holidays"""
        from src.backtest.engine import TradeCalendar

        TradeCalendar._loaded = False
        TradeCalendar._trade_dates = None
        TradeCalendar._source = "none"

        TradeCalendar.set_holidays({"2026-01-01"})

        result = TradeCalendar.ensure_loaded()
        assert result is True
        assert TradeCalendar._source in ("file", "holidays", "akshare")


class TestTradeCalendarStale:
    """Staleness 检测测试"""

    def test_is_stale_returns_false_for_file_source(self):
        """本地文件来源不视为 stale"""
        from src.backtest.engine import TradeCalendar

        TradeCalendar._loaded = True
        TradeCalendar._source = "file"
        TradeCalendar._last_loaded_at = None

        assert TradeCalendar.is_stale() is False

    def test_is_stale_returns_true_when_too_old(self):
        """akshare 数据超过 7 天视为 stale"""
        from src.backtest.engine import TradeCalendar
        from datetime import datetime, timezone, timedelta

        TradeCalendar._loaded = True
        TradeCalendar._source = "akshare"
        old_time = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        TradeCalendar._last_loaded_at = old_time

        assert TradeCalendar.is_stale() is True

    def test_is_stale_returns_false_when_recent(self):
        """akshare 数据 7 天内视为有效"""
        from src.backtest.engine import TradeCalendar
        from datetime import datetime, timezone, timedelta

        TradeCalendar._loaded = True
        TradeCalendar._source = "akshare"
        recent_time = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        TradeCalendar._last_loaded_at = recent_time

        assert TradeCalendar.is_stale() is False


class TestTradeCalendarSource:
    """数据来源检测"""

    def test_source_returns_current_source(self):
        """source 方法返回当前数据来源"""
        from src.backtest.engine import TradeCalendar

        TradeCalendar._source = "file"
        assert TradeCalendar.source() == "file"

        TradeCalendar._source = "akshare"
        assert TradeCalendar.source() == "akshare"

        TradeCalendar._source = "none"
        assert TradeCalendar.source() == "none"


class TestIsTradeDateWithFallback:
    """is_trade_date fallback 行为"""

    def test_is_trade_date_uses_file_when_data_current(self):
        """本地文件数据够新时直接使用"""
        from src.backtest.engine import TradeCalendar

        current_year = date.today().year
        dates = [f"{current_year}-04-{i:02d}" for i in range(1, 31)]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"trade_dates": dates}, f)
            f.flush()
            path = f.name

        try:
            TradeCalendar._loaded = False
            TradeCalendar._trade_dates = None
            TradeCalendar._source = "none"

            # 当前年份的数据在文件里
            target_date = date(current_year, 4, 15)
            result = TradeCalendar.is_trade_date(target_date)
            assert result is True
        finally:
            Path(path).unlink()
