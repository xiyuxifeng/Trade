"""回测与规则池包导入回归测试。"""

from __future__ import annotations

import importlib


def test_rule_pool_schemas_can_import_without_circular_dependency():
    """规则池 schema 导入不应因为 backtest 包入口而触发循环依赖。"""
    module = importlib.import_module("src.rule_pool.schemas")

    assert hasattr(module, "ReviewStatus")
    assert hasattr(module, "RuleBacktestResult")
