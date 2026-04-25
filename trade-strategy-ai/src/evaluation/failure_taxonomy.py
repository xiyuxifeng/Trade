"""失败归因分类定义（NTL-S5-002）。

职责：
- 定义失败归因的标准化标签体系（根因 + 交易阶段 + 规则类型）
- 提供标签解析函数
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FailureRootCause(StrEnum):
    """失败根因标签（必选，至少 1 个）。

    用于描述交易失败的根本原因。
    """
    RULE_PRECONDITION_FAILED = "rule_precondition_failed"
    SIGNAL_QUALITY_LOW = "signal_quality_low"
    ENTRY_TIMING_POOR = "entry_timing_poor"
    EXIT_TIMING_POOR = "exit_timing_poor"
    POSITION_SIZE_MISMATCH = "position_size_mismatch"
    MARKET_MISMATCH = "market_mismatch"
    EXTERNAL_EVENT = "external_event"
    SYMBOL_SELECTION_SUBOPTIMAL = "symbol_selection_suboptimal"
    DATA_QUALITY_ISSUE = "data_quality_issue"


class FailureStage(StrEnum):
    """失败发生的交易阶段（可选，最多 1 个）。

    用于标注失败发生在交易的哪个阶段。
    """
    ENTRY = "stage:entry"
    EXIT = "stage:exit"
    HOLDING = "stage:holding"


class FailureRuleType(StrEnum):
    """涉及的规则类型（可选，最多 1 个）。

    用于标注失败涉及哪类策略规则。
    """
    ENTRY = "rule_type:entry"
    EXIT = "rule_type:exit"
    FILTER = "rule_type:filter"
    SIZING = "rule_type:sizing"
