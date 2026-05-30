"""Strategy Config 单元测试 - P4-026"""
import pytest
from pathlib import Path
import tempfile
import os
from src.strategy.config import (
    FeatureEngineConfig,
    RuleEvaluatorConfig,
    SignalSynthesizerConfig,
    StrategyConfig,
    get_strategy_config,
    load_strategy_config,
)


def test_default_config():
    """测试默认配置"""
    config = StrategyConfig()

    assert config.feature_engine.mode == "realtime"
    assert config.feature_engine.compute_batch is True
    assert config.rule_evaluator.dsl_executor == {}
    assert config.signal_synthesizer.mode == "priority"


def test_feature_engine_config():
    """测试特征引擎配置"""
    config = FeatureEngineConfig(mode="polars", compute_batch=False)

    assert config.mode == "polars"
    assert config.compute_batch is False


def test_rule_evaluator_config():
    """测试规则评估器配置"""
    config = RuleEvaluatorConfig(dsl_executor={"timeout": 30})

    assert config.dsl_executor["timeout"] == 30


def test_signal_synthesizer_config():
    """测试信号合成器配置"""
    config = SignalSynthesizerConfig(
        mode="weighted_score",
        weights={"entry": 1.0, "exit": 1.5},
        priorities=["entry", "exit"],
    )

    assert config.mode == "weighted_score"
    assert config.weights["entry"] == 1.0
    assert config.weights["exit"] == 1.5
    assert config.priorities == ["entry", "exit"]


def test_load_strategy_config_from_yaml():
    """测试从 YAML 加载配置"""
    yaml_content = """
strategy:
  feature_engine:
    mode: "polars"
    compute_batch: true
  rule_evaluator:
    dsl_executor:
      timeout: 60
  signal_synthesizer:
    mode: "voting"
    weights:
      entry: 2.0
      exit: 1.0
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        temp_path = f.name

    try:
        config = load_strategy_config(temp_path)
        assert config.feature_engine.mode == "polars"
        assert config.feature_engine.compute_batch is True
        assert config.rule_evaluator.dsl_executor["timeout"] == 60
        assert config.signal_synthesizer.mode == "voting"
        assert config.signal_synthesizer.weights["entry"] == 2.0
    finally:
        os.unlink(temp_path)


def test_load_strategy_config_nonexistent():
    """测试加载不存在的配置文件返回默认配置"""
    config = load_strategy_config("/nonexistent/path/config.yaml")

    assert config.feature_engine.mode == "realtime"
    assert config.signal_synthesizer.mode == "priority"


def test_strategy_config_nested_defaults():
    """测试嵌套配置使用默认值"""
    config = StrategyConfig()

    # 子配置应有默认值
    assert config.feature_engine.mode == "realtime"
    assert config.signal_synthesizer.weights == {}


def test_get_strategy_config_reads_app_yaml():
    """测试默认策略配置从 app.yaml 读取"""
    config = get_strategy_config()

    assert config.feature_engine.mode == "realtime"
    assert config.rule_evaluator.dsl_executor["mode"] == "all"
    assert config.signal_synthesizer.weights["risk"] == 2.0
