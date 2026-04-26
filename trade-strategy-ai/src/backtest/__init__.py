"""回测模块（NTL-S6-001~013）。

职责：
- 提供离线回测 schema 与数据模型
- 复用 Stage 5 统一评分口径
- 支持快照只读重放与规则验真
"""

from src.backtest.schemas import (
    BacktestRequest,
    BacktestResult,
    BacktestSummary,
    BacktestTradeRecord,
    RuleValidationResult,
)

__all__ = [
    "BacktestRequest",
    "BacktestResult",
    "BacktestSummary",
    "BacktestTradeRecord",
    "RuleValidationResult",
]
