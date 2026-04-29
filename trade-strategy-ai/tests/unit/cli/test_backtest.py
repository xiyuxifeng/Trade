# tests/unit/cli/test_backtest.py
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.backtest.engine import BacktestEngine


def test_create_engine_with_config(tmp_path):
    """验证配置加载时正确初始化 SnapshotLoader 依赖"""
    from cli.backtest import _create_engine_from_config

    # 创建临时配置文件
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
database:
  url: null
data:
  providers: []
""")

    engine = _create_engine_from_config(str(config_file))
    assert isinstance(engine, BacktestEngine)
    # loader 不应为 None
    assert engine.loader is not None
    # strategy_loader 不应为 None
    assert engine.strategy_loader is not None
