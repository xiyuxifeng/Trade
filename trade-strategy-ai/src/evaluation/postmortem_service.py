"""盘后复盘 service（NTL-S5-003）。

职责：
- 对单笔交易生成结构化复盘结果
- 支持自动归因 + LLM 校验混合模式
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


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
from src.evaluation.metrics_calculator import compute_mfe_mae_return, _extract_rules_hit


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


def _load_prompt(relative_path: str) -> str:
    """从 prompts 目录加载 prompt 文件。

    路径相对于项目根目录。
    """
    # 项目根目录：src/evaluation/../../ = 项目根
    root = Path(__file__).parent.parent.parent
    return (root / relative_path).read_text(encoding="utf-8").strip()


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

    def _auto_attribution(
        self,
        evidence_pack: EvidencePack,
        rules_hit: list[str],
        return_pct: float,
    ) -> FailureAttribution:
        """基于 EvidencePack 数据做自动归因（NTL-S5-010 增强）。

        归因逻辑：
        - 数据质量：无 market_data 或 bars 为空
        - 亏损归因（return_pct < 0）：
            - rules_hit 非空 → RULE_PRECONDITION_FAILED（规则前置条件可能未满足）
            - rules_hit 为空 → ENTRY_TIMING_POOR（入场时机差，无规则依据）
        """
        root_causes: list[str] = []

        # 数据质量问题
        if not evidence_pack.market_data or not evidence_pack.market_data.get("bars"):
            root_causes.append("data_quality_issue")

        # 亏损归因
        if return_pct < 0:
            if not rules_hit:
                root_causes.append("entry_timing_poor")
            else:
                root_causes.append("rule_precondition_failed")

        return FailureAttribution(root_causes=root_causes)

    def _apply_validation(
        self,
        auto: FailureAttribution,
        validation: LLMValidationResult,
    ) -> tuple[FailureAttribution, str, dict[str, object]]:
        """应用 LLM 校验结果。

        Returns:
            (final_attribution, source, extra)
        """
        extra: dict[str, object] = {}

        if validation.decision == ValidationDecision.CONFIRM:
            return auto, "llm_confirmed", extra

        elif validation.decision == ValidationDecision.CORRECT:
            corrected = FailureAttribution(root_causes=validation.corrected_categories)
            extra["auto_original"] = auto
            return corrected, "llm_corrected", extra

        else:  # REJECT
            extra["auto_original"] = auto
            return FailureAttribution(root_causes=[]), "llm_rejected", extra

    async def generate(
        self,
        evidence_pack: EvidencePack,
    ) -> PostmortemResult:
        """对单笔交易生成复盘结果。

        Args:
            evidence_pack: 交易证据包

        Returns:
            PostmortemResult: 结构化复盘结果
        """
        # Step 1: 计算 MFE / MAE / return_pct（NTL-S5-010）
        bars: list[dict] = evidence_pack.market_data.get("bars", [])
        entry_price: float = evidence_pack.market_data.get("entry_price", 0.0)
        target_price = evidence_pack.market_data.get("target_price")
        stop_loss_price = evidence_pack.market_data.get("stop_loss_price")

        mfe, mae, return_pct, exit_triggered, exit_date = compute_mfe_mae_return(
            bars=bars,
            entry_price=entry_price,
            entry_date=evidence_pack.trade_date,
            target_price=target_price,
            stop_loss_price=stop_loss_price,
        )

        # 提取 rules_hit
        rules_hit: list[str] = []
        if (
            evidence_pack.signal_context
            and evidence_pack.signal_context.rules_snapshot
        ):
            rules_hit = _extract_rules_hit(evidence_pack.signal_context.rules_snapshot)

        # Step 2: 自动归因（基于 return_pct 和 rules_hit）
        auto_attribution = self._auto_attribution(
            evidence_pack,
            rules_hit=rules_hit,
            return_pct=return_pct,
        )

        # Step 3: LLM 校验（可选）
        source = "auto"
        extra: dict[str, object] = {}
        final_attribution = auto_attribution

        if self.llm_validator is not None:
            validation = await self.llm_validator.validate(evidence_pack, auto_attribution)
            final_attribution, source, extra = self._apply_validation(auto_attribution, validation)

        # Step 4: LLM 笔记生成（当前未实现，占位）
        notes = None
        # if self.enable_llm_notes and self.llm_validator is not None:
        #     notes = await self._generate_notes(evidence_pack, final_attribution)

        # 构建 extra（包含 NTL-S5-010 新增字段）
        result_extra: dict[str, object] = {
            **extra,
            "rules_hit": rules_hit,
            "exit_triggered": exit_triggered,
            "exit_date": exit_date,
            "is_final": exit_triggered is not None,
        }

        return PostmortemResult(
            idea_id=evidence_pack.idea_id,
            trade_date=evidence_pack.trade_date,
            failure_attribution=final_attribution,
            attribution_source=source,
            postmortem_notes=notes,
            mfe=mfe,
            mae=mae,
            return_pct=return_pct,
            extra=result_extra,
        )

    # -------------------------------------------------------------------------
    # NTL-S5-012: LLM 归因
    # -------------------------------------------------------------------------

    async def llm_attribution(
        self,
        trade_idea: dict,
        market_data: dict,
        auto_attribution: dict,
        llm_client=None,
    ) -> dict:
        """对 failure_case 进行 LLM 归因分析（NTL-S5-012）。

        复用 src/llm/client.py 的 LLMClient。

        Args:
            trade_idea: 交易想法 dict
            market_data: 市场数据 dict（包含 bars）
            auto_attribution: 自动归因结果
            llm_client: 可选，LLM 客户端（用于测试注入）

        Returns:
            dict: 包含 attribution_source 和归因详情的 dict
        """
        from src.llm.client import LLMClient, LLMClientConfig, from_env_and_config

        if llm_client is None:
            cfg = from_env_and_config(
                provider=None, model=None, url=None, api_key=None,
            )
            llm_client = LLMClient(cfg)

        if not llm_client.is_enabled():
            # LLM 未配置，降级为 auto
            return {
                "attribution_source": "auto",
                "reason": auto_attribution.get("reason", ""),
                "corrected_reason": None,
                "confidence": 0.0,
            }

        system_prompt = _load_prompt("prompts/llm_attribution.md")
        user_prompt = self._build_llm_user_prompt(trade_idea, market_data, auto_attribution)

        try:
            response = await llm_client.complete_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        except Exception:
            response = None

        # 判断归因结果
        if response is None:
            return {
                "attribution_source": "llm_rejected",
                "reason": auto_attribution.get("reason", ""),
                "corrected_reason": None,
                "confidence": 0.0,
            }

        corrected_reason = response.get("corrected_reason") or response.get("reason", "")
        auto_reason = auto_attribution.get("reason", "")

        if corrected_reason == auto_reason:
            attribution_source = "llm_confirmed"
        else:
            attribution_source = "llm_corrected"

        return {
            "attribution_source": attribution_source,
            "reason": corrected_reason,
            "corrected_reason": corrected_reason if corrected_reason != auto_reason else None,
            "confidence": response.get("confidence", 0.5),
        }

    def _build_llm_user_prompt(
        self,
        trade_idea: dict,
        market_data: dict,
        auto_attribution: dict,
    ) -> str:
        """构造 LLM 归因 Prompt（Option A: 完整上下文）。"""
        bars = market_data.get("bars", [])
        bars_str = json.dumps(bars, ensure_ascii=False, default=str) if bars else "无市场数据"

        return f"""## 交易想法
- 标的: {trade_idea.get('symbol', 'N/A')}
- 方向: {trade_idea.get('side', 'N/A')}
- 入场价格: {trade_idea.get('entry', {})}
- 目标价格: {trade_idea.get('target', 'N/A')}
- 止损价格: {trade_idea.get('stop_loss', 'N/A')}

## 市场数据（1d 日线）
{bars_str}

## 自动归因结果（auto）
- 原因: {auto_attribution.get('reason', 'N/A')}
- 置信度: {auto_attribution.get('confidence', 0.0)}

## 任务
分析上述交易失败的根本原因，给出修正后的归因。如果自动归因准确，确认即可。
如果自动归因有误，给出修正原因。

请以 JSON 格式返回：
{{"reason": "归因原因", "corrected_reason": "修正后原因（如有）", "confidence": 0.0-1.0}}
"""
