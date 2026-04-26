"""Evaluation 模块：盘后评估、学习闭环与 ranking。

职责：
- 生成 Evidence Pack（交易想法 + 上下文 + 市场快照）
- 失败归因分类
- 盘后复盘服务
- 策略 ranking
"""

from src.evaluation.evidence_pack import EvidencePack, MarketDataSnapshot
from src.evaluation.failure_taxonomy import (
    FailureRootCause,
    FailureStage,
    FailureRuleType,
    FailureAttribution,
    parse_failure_categories,
)
from src.evaluation.postmortem_service import (
    ValidationDecision,
    LLMValidationResult,
    PostmortemResult,
    PostmortemService,
    LLMValidator,
)
from src.evaluation.ranking_service import RankingEntry, RankingService
from src.evaluation.metrics_calculator import TradeConstraint, compute_mfe_mae_return

__all__ = [
    "EvidencePack",
    "FailureRootCause",
    "FailureStage",
    "FailureRuleType",
    "FailureAttribution",
    "parse_failure_categories",
    "ValidationDecision",
    "LLMValidationResult",
    "PostmortemResult",
    "PostmortemService",
    "LLMValidator",
    "RankingEntry",
    "RankingService",
    # 共享评分口径（NTL-S6-007）
    "TradeConstraint",
    "compute_mfe_mae_return",
]
