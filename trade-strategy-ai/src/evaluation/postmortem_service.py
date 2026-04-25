"""盘后复盘 service（NTL-S5-003）。

职责：
- 对单笔交易生成结构化复盘结果
- 支持自动归因 + LLM 校验混合模式
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ValidationDecision(StrEnum):
    """LLM 校验决策。"""
    CONFIRM = "confirm"      # 自动归因正确
    CORRECT = "correct"     # LLM 修正了自动归因
    REJECT = "reject"       # LLM 拒绝归因


@dataclass
class LLMValidationResult:
    """LLM 校验结果。"""
    decision: ValidationDecision
    corrected_categories: list[str] = field(default_factory=list)
    reasoning: str = ""


from uuid import UUID
from src.evaluation.failure_taxonomy import FailureAttribution


@dataclass
class PostmortemResult:
    """单笔交易的结构化复盘结果。"""
    idea_id: UUID | None
    trade_date: str

    # 归因结果
    failure_attribution: FailureAttribution
    attribution_source: str  # "auto" | "llm_confirmed" | "llm_corrected" | "llm_rejected"

    # LLM 生成的自然语言复盘（可为 None）
    postmortem_notes: str | None = None

    # 评分指标（NTL-S5-010 实现，当前占位）
    mfe: float | None = None      # Maximum Favorable Excursion
    mae: float | None = None      # Maximum Adverse Excursion
    return_pct: float | None = None

    # 扩展字段
    extra: dict[str, object] = field(default_factory=dict)
