"""Risk Config 单元测试。"""

from __future__ import annotations

import os
import tempfile

from src.risk.config import RiskConfig, get_risk_config, load_risk_config


def test_default_risk_config() -> None:
    """测试默认风控配置。"""
    config = RiskConfig()

    assert config.position_manager.mode == "fixed_ratio"
    assert config.stop_loss.mode == "volatility"
    assert config.take_profit.mode == "scaling"
    assert config.simulated_account.enabled is True


def test_load_risk_config_from_yaml() -> None:
    """测试从 YAML 加载风控配置。"""
    yaml_content = """
risk:
  position_manager:
    mode: "fixed_amount"
    fixed_amount: 20000
  stop_loss:
    mode: "fixed"
    fixed_pct: 0.08
  take_profit:
    mode: "fixed"
    fixed_pct: 0.12
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        temp_path = f.name

    try:
        config = load_risk_config(temp_path)
        assert config.position_manager.mode == "fixed_amount"
        assert config.position_manager.fixed_amount == 20000
        assert config.stop_loss.mode == "fixed"
        assert config.stop_loss.fixed_pct == 0.08
        assert config.take_profit.mode == "fixed"
        assert config.take_profit.fixed_pct == 0.12
    finally:
        os.unlink(temp_path)


def test_get_risk_config_reads_app_yaml() -> None:
    """测试默认风控配置从 app.yaml 读取。"""
    config = get_risk_config()

    assert config.position_manager.fixed_ratio_pct == 0.05
    assert config.take_profit.scaling_levels[0].target_pct == 0.05
    assert config.portfolio.max_leverage == 1.0
