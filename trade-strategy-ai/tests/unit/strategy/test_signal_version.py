"""SignalVersioning 单元测试"""
import json
import os
import shutil
import tarfile
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from src.strategy.signal_version import SignalVersioning
from src.strategy.types import Signal, SignalSide, SignalContext


@pytest.fixture
def temp_dir():
    """创建临时目录，测试后清理。"""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp, ignore_errors=True)


def _make_signal(signal_id: str, ts: datetime | None = None) -> Signal:
    if ts is None:
        ts = datetime.now()
    return Signal(
        signal_id=signal_id,
        symbol="TEST",
        side=SignalSide.BUY,
        confidence=0.8,
        timestamp=ts,
        triggered_rules=["rule1"],
        synthesis_mode=None,
    )


def _make_context(ts: datetime | None = None) -> SignalContext:
    if ts is None:
        ts = datetime.now()
    return SignalContext(
        features_snapshot={"rsi": 70},
        market_state={"regime": "trend_up"},
        rules_snapshot=[],
        timestamp=ts,
    )


def test_record_and_get(temp_dir):
    """测试记录和获取（新版日期分目录）。"""
    versioning = SignalVersioning(storage_path=temp_dir)

    ts = datetime(2026, 4, 28, 10, 0, 0)
    signal = _make_signal("idea_test001", ts)
    context = _make_context(ts)

    version_id = versioning.record(signal, context)
    assert version_id == "idea_test001"

    # 验证文件路径
    expected_path = temp_dir / "2026-04-28" / "idea_test001.json"
    assert expected_path.exists()

    # 验证读取
    result = versioning.get_version("idea_test001")
    assert result is not None
    assert result.signal.signal_id == "idea_test001"
    assert result.signal.symbol == "TEST"


def test_get_version_not_found(temp_dir):
    """测试不存在的 signal_id 返回 None。"""
    versioning = SignalVersioning(storage_path=temp_dir)
    result = versioning.get_version("not_exist")
    assert result is None


def test_list_versions(temp_dir):
    """测试列出版本（按日期分目录）。"""
    versioning = SignalVersioning(storage_path=temp_dir)

    ts1 = datetime(2026, 4, 28, 10, 0, 0)
    ts2 = datetime(2026, 4, 29, 10, 0, 0)

    versioning.record(_make_signal("idea_day1", ts1), _make_context(ts1))
    versioning.record(_make_signal("idea_day2", ts2), _make_context(ts2))

    versions = versioning.list_versions(symbol="TEST", limit=10)
    assert len(versions) == 2


def test_archive_old_signals(temp_dir):
    """测试归档：超过 retention_days 的目录被压缩为 tar.gz。"""
    versioning = SignalVersioning(storage_path=temp_dir, retention_days=10)

    # 创建 12 天前的信号（超过 retention_days=10）
    old_ts = datetime.now() - timedelta(days=12)
    versioning.record(
        _make_signal("idea_old001", old_ts),
        _make_context(old_ts),
    )
    versioning.record(
        _make_signal("idea_old002", old_ts),
        _make_context(old_ts),
    )

    old_date_str = old_ts.strftime("%Y-%m-%d")
    day_dir = temp_dir / old_date_str
    assert day_dir.exists()
    assert len(list(day_dir.glob("*.json"))) == 2

    # 执行归档
    archived = versioning.archive_old_signals()
    assert len(archived) == 1

    # 原始目录应被删除
    assert not day_dir.exists()

    # 归档文件应存在
    archive_file = temp_dir / "archive" / f"{old_date_str}.tar.gz"
    assert archive_file.exists()

    # 从归档读取仍可获取
    result = versioning.get_version("idea_old001")
    assert result is not None
    assert result.signal.signal_id == "idea_old001"


def test_get_from_archive_stream_read(temp_dir):
    """测试从 tar.gz 流读取信号（不落临时文件）。"""
    versioning = SignalVersioning(storage_path=temp_dir, retention_days=5)

    # 手动创建归档文件（模拟已压缩状态）
    old_ts = datetime(2026, 4, 20, 10, 0, 0)
    old_date_str = "2026-04-20"

    # 直接创建 tar.gz（不通过 record）
    archive_dir = temp_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_file = archive_dir / f"{old_date_str}.tar.gz"

    signal_data = {
        "signal": {
            "signal_id": f"idea_{old_date_str}_from_archive",
            "symbol": "TEST",
            "side": "BUY",
            "confidence": 0.8,
            "timestamp": old_ts.isoformat(),
            "triggered_rules": [],
            "synthesis_mode": None,
            "entry_price": None,
            "position_size": None,
            "version": "v1",
            "strategy_version_id": None,
            "metadata": {},
        },
        "context": {
            "features_snapshot": {},
            "market_state": {},
            "rules_snapshot": [],
            "timestamp": old_ts.isoformat(),
            "strategy_version_id": None,
            "market_universe_snapshot": {},
            "topic_source_ids": [],
        },
    }

    with tarfile.open(archive_file, "w:gz") as tf:
        signal_id = f"idea_{old_date_str}_from_archive"
        import io
        data_bytes = json.dumps(signal_data, default=str).encode("utf-8")
        info = tarfile.TarInfo(name=f"{signal_id}.json")
        info.size = len(data_bytes)
        tf.addfile(info, io.BytesIO(data_bytes))

    # 验证流读取
    result = versioning.get_version(signal_id)
    assert result is not None
    assert result.signal.signal_id == signal_id
    assert result.signal.symbol == "TEST"


def test_legacy_format_compat(temp_dir):
    """测试兼容旧格式：data/signals/{signal_id}.json（无日期目录）。"""
    versioning = SignalVersioning(storage_path=temp_dir)

    # 手动创建旧格式文件
    legacy_path = temp_dir / "legacy_signal.json"
    legacy_data = {
        "signal": {
            "signal_id": "legacy_signal",
            "symbol": "OLD",
            "side": "SELL",
            "confidence": 0.5,
            "timestamp": datetime.now().isoformat(),
            "triggered_rules": [],
            "synthesis_mode": None,
            "entry_price": None,
            "position_size": None,
            "version": "v1",
            "strategy_version_id": None,
            "metadata": {},
        },
        "context": {
            "features_snapshot": {},
            "market_state": {},
            "rules_snapshot": [],
            "timestamp": datetime.now().isoformat(),
            "strategy_version_id": None,
            "market_universe_snapshot": {},
            "topic_source_ids": [],
        },
    }
    legacy_path.write_text(json.dumps(legacy_data), encoding="utf-8")

    # 验证可读取
    result = versioning.get_version("legacy_signal")
    assert result is not None
    assert result.signal.signal_id == "legacy_signal"
    assert result.signal.symbol == "OLD"


def test_is_valid_date():
    """测试日期格式校验。"""
    assert SignalVersioning._is_valid_date("2026-04-30")
    assert SignalVersioning._is_valid_date("2026-01-01")
    assert not SignalVersioning._is_valid_date("2026-4-30")
    assert not SignalVersioning._is_valid_date("04-30-2026")
    assert not SignalVersioning._is_valid_date("not-a-date")


def test_try_parse_date_from_signal_id():
    """测试从 signal_id 解析日期。"""
    # 新格式：idea_2026-04-25_a1b2c3d4
    date_str = SignalVersioning._try_parse_date_from_signal_id("idea_2026-04-25_a1b2c3d4")
    assert date_str == "2026-04-25"

    # 无日期格式
    date_str = SignalVersioning._try_parse_date_from_signal_id("idea_a1b2c3d4")
    assert date_str is None

    # YYYYMMDD 格式
    date_str = SignalVersioning._try_parse_date_from_signal_id("idea_20260425_a1b2c3d4")
    assert date_str == "2026-04-25"
