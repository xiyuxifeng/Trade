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
