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


from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from src.evaluation.evidence_pack import EvidencePack


class LLMValidator(Protocol):
    """LLM 校验器接口。"""
    async def validate(
        self,
        evidence_pack: EvidencePack,
        auto_attribution: FailureAttribution,
    ) -> LLMValidationResult:
        """校验自动归因结果。"""
        ...


class PostmortemService:
    """盘后复盘 service。

    Args:
        llm_validator: LLM 校验器（可选，不提供则只做自动归因）
        enable_llm_notes: 是否生成 LLM 复盘笔记（需要 llm_validator）
    """

    def __init__(
        self,
        llm_validator: LLMValidator | None = None,
        enable_llm_notes: bool = False,
    ):
        self.llm_validator = llm_validator
        self.enable_llm_notes = enable_llm_notes

    def _auto_attribution(self, evidence_pack: EvidencePack) -> FailureAttribution:
        """基于 EvidencePack 数据做自动归因。

        目前实现：
        - data_quality_issue：market_data 为空或异常

        完整归因逻辑在 NTL-S5-010 后完善。
        """
        root_causes: list[str] = []

        # 数据质量问题
        if not evidence_pack.market_data:
            root_causes.append("data_quality_issue")

        return FailureAttribution(root_causes=root_causes)
