"""策略配置加载"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel


class FeatureEngineConfig(BaseModel):
    """特征引擎配置"""
    mode: str = "realtime"
    compute_batch: bool = True


class RuleEvaluatorConfig(BaseModel):
    """规则评估器配置"""
    dsl_executor: dict[str, Any] = {}


class SignalSynthesizerConfig(BaseModel):
    """信号合成器配置"""
    mode: str = "priority"
    weights: dict[str, float] = {}
    priorities: list[str] = []


class StrategyConfig(BaseModel):
    """策略配置"""
    feature_engine: FeatureEngineConfig = FeatureEngineConfig()
    rule_evaluator: RuleEvaluatorConfig = RuleEvaluatorConfig()
    signal_synthesizer: SignalSynthesizerConfig = SignalSynthesizerConfig()


@lru_cache
def get_strategy_config() -> StrategyConfig:
    """获取策略配置（单例）

    从 config/strategy.yaml 加载配置
    """
    config_path = Path("config/strategy.yaml")
    if config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
        # 提取 strategy 节点
        return StrategyConfig(**data.get("strategy", {}))
    return StrategyConfig()


def load_strategy_config(config_path: str | Path) -> StrategyConfig:
    """从指定路径加载策略配置"""
    path = Path(config_path)
    if path.exists():
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        # 提取 strategy 节点
        return StrategyConfig(**data.get("strategy", {}))
    return StrategyConfig()
