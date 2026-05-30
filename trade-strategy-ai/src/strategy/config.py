"""策略配置加载"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from src.common.config import load_app_config
from src.common.paths import resolve_project_path


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

    优先从 config/app.yaml 读取 strategy section；兼容独立 strategy.yaml。
    """
    config_path = resolve_project_path("config/app.yaml")
    loaded = load_app_config(config_path)
    return StrategyConfig.model_validate(loaded.config.strategy or {})


def load_strategy_config(config_path: str | Path) -> StrategyConfig:
    """从指定路径加载策略配置"""
    path = resolve_project_path(config_path)
    if not path.exists():
        return StrategyConfig()

    loaded = load_app_config(path)
    return StrategyConfig.model_validate(loaded.config.strategy or {})
