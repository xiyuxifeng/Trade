"""回测模块（NTL-S6-001~013）。

职责：
- 提供离线回测 schema 与数据模型
- 复用 Stage 5 统一评分口径
- 支持快照只读重放与规则验真
"""

from src.backtest.engine import BacktestEngine, validate_rule_hits, validate_rules_for_trader
from src.backtest.execution import classify_rules_snapshot_gap, replay_candidates
from src.backtest.reporting import (
    render_backtest_json,
    render_backtest_markdown,
    render_rule_validation_markdown,
)
from src.backtest.reproducibility import fingerprint_result
from src.backtest.rule_registry import RuleMeta, classify_rule
from src.backtest.schemas import (
    BacktestRequest,
    BacktestResult,
    BacktestSummary,
    BacktestTradeRecord,
    RuleValidationResult,
)
from src.backtest.scoring import score_backtest_trade
from src.backtest.snapshot_loader import SnapshotLoader

__all__ = [
    # schemas
    "BacktestRequest",
    "BacktestResult",
    "BacktestSummary",
    "BacktestTradeRecord",
    "RuleValidationResult",
    # engine
    "BacktestEngine",
    "validate_rule_hits",
    "validate_rules_for_trader",
    # execution
    "replay_candidates",
    "classify_rules_snapshot_gap",
    # scoring
    "score_backtest_trade",
    # snapshot
    "SnapshotLoader",
    # reporting
    "render_backtest_markdown",
    "render_backtest_json",
    "render_rule_validation_markdown",
    # rule_registry
    "RuleMeta",
    "classify_rule",
    # reproducibility
    "fingerprint_result",
]
