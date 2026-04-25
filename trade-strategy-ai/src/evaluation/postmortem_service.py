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


from typing import TYPE_CHECKING, Any, Protocol

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


class LLMNotesClient(Protocol):
    """LLM 复盘笔记生成客户端接口。"""

    def is_enabled(self) -> bool:
        """判断当前客户端是否可用。"""
        ...

    async def complete_json_with_retry(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """生成 JSON 输出。"""
        ...


class PostmortemService:
    """盘后复盘 service。

    Args:
        llm_validator: LLM 校验器（可选，不提供则只做自动归因）
        llm_notes_client: LLM 笔记生成客户端（可选，未配置则回退结构化摘要）
        enable_llm_notes: 是否生成复盘笔记（优先返回结构化中文摘要，后续可替换为 LLM 输出）
    """

    def __init__(
        self,
        llm_validator: LLMValidator | None = None,
        llm_notes_client: LLMNotesClient | None = None,
        enable_llm_notes: bool = False,
    ):
        self.llm_validator = llm_validator
        self.llm_notes_client = llm_notes_client
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
        if not evidence_pack.market_data.bars:
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

    def _build_postmortem_notes(
        self,
        *,
        evidence_pack: EvidencePack,
        final_attribution: FailureAttribution,
        attribution_source: str,
        mfe: float,
        mae: float,
        return_pct: float,
        rules_hit: list[str],
        exit_triggered: str | None,
        exit_date: str | None,
    ) -> str:
        """生成可读的复盘摘要。

        当前先输出结构化中文摘要，保证在没有外部 LLM 的情况下也能落地；
        后续若接入 LLM，可直接替换这层实现。
        """
        symbol = evidence_pack.trade_idea.symbol if evidence_pack.trade_idea else "unknown"
        bars = evidence_pack.market_data.bars
        root_causes = "、".join(final_attribution.root_causes) if final_attribution.root_causes else "暂无明确根因"
        rules_text = "、".join(rules_hit) if rules_hit else "无"
        outcome = "盈利" if return_pct >= 0 else "亏损"

        if not bars:
            data_text = "市场 bars 缺失，已使用降级结果。"
        elif exit_triggered:
            data_text = f"已触发 {exit_triggered}，出场日期 {exit_date}。"
        else:
            data_text = f"未触发止盈/止损，使用最后一根 bar 的收盘价作为 exit。"

        return (
            f"{symbol} 于 {evidence_pack.trade_date} 的复盘：{outcome} {return_pct:.2%}，"
            f"MFE {mfe:.2%}，MAE {mae:.2%}，bars={len(bars)}。"
            f"归因来源 {attribution_source}，主要根因：{root_causes}。"
            f"规则命中：{rules_text}。{data_text}"
        )

    def _build_llm_notes_prompt(
        self,
        *,
        evidence_pack: EvidencePack,
        final_attribution: FailureAttribution,
        attribution_source: str,
        mfe: float,
        mae: float,
        return_pct: float,
        rules_hit: list[str],
        exit_triggered: str | None,
        exit_date: str | None,
    ) -> str:
        """构造 LLM 复盘笔记 prompt。"""
        symbol = evidence_pack.trade_idea.symbol if evidence_pack.trade_idea else "unknown"
        bars = evidence_pack.market_data.bars
        bars_str = json.dumps(bars, ensure_ascii=False, default=str) if bars else "[]"
        root_causes = "、".join(final_attribution.root_causes) if final_attribution.root_causes else "无明确根因"
        rules_text = "、".join(rules_hit) if rules_hit else "无"
        exit_text = exit_triggered or "none"
        exit_date_text = exit_date or "none"
        trade_side = evidence_pack.trade_idea.side if evidence_pack.trade_idea and evidence_pack.trade_idea.side else "unknown"
        entry_value = evidence_pack.trade_idea.entry.price if evidence_pack.trade_idea and evidence_pack.trade_idea.entry else None
        target_price = evidence_pack.market_data.target_price
        stop_loss_price = evidence_pack.market_data.stop_loss_price

        template = _load_prompt("prompts/llm_postmortem_notes.md")
        result = template.replace("{symbol}", str(symbol))
        result = result.replace("{trade_date}", str(evidence_pack.trade_date))
        result = result.replace("{side}", str(trade_side))
        result = result.replace("{entry_price}", str(entry_value if entry_value is not None else "N/A"))
        result = result.replace("{target_price}", str(target_price if target_price is not None else "N/A"))
        result = result.replace("{stop_loss_price}", str(stop_loss_price if stop_loss_price is not None else "N/A"))
        result = result.replace("{bars}", bars_str)
        result = result.replace("{root_causes}", root_causes)
        result = result.replace("{attribution_source}", attribution_source)
        result = result.replace("{mfe}", f"{mfe:.6f}")
        result = result.replace("{mae}", f"{mae:.6f}")
        result = result.replace("{return_pct}", f"{return_pct:.6f}")
        result = result.replace("{rules_hit}", rules_text)
        result = result.replace("{exit_triggered}", exit_text)
        result = result.replace("{exit_date}", exit_date_text)
        return result

    async def _generate_postmortem_notes(
        self,
        *,
        evidence_pack: EvidencePack,
        final_attribution: FailureAttribution,
        attribution_source: str,
        mfe: float,
        mae: float,
        return_pct: float,
        rules_hit: list[str],
        exit_triggered: str | None,
        exit_date: str | None,
    ) -> tuple[str | None, str]:
        """优先使用 LLM 生成复盘笔记，失败时回退到结构化摘要。

        Returns:
            (notes, source)
        """
        client = self.llm_notes_client
        if client is None:
            from src.llm.client import LLMClient, from_env_and_config

            cfg = from_env_and_config(
                provider=None,
                model=None,
                url=None,
                api_key=None,
            )
            client = LLMClient(cfg)

        if not client.is_enabled():
            return None, "fallback"

        system_prompt = _load_prompt("prompts/llm_postmortem_notes.md")
        user_prompt = self._build_llm_notes_prompt(
            evidence_pack=evidence_pack,
            final_attribution=final_attribution,
            attribution_source=attribution_source,
            mfe=mfe,
            mae=mae,
            return_pct=return_pct,
            rules_hit=rules_hit,
            exit_triggered=exit_triggered,
            exit_date=exit_date,
        )

        try:
            response = await client.complete_json_with_retry(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        except Exception:
            return None, "fallback"

        notes = response.get("notes") or response.get("summary") or response.get("content")
        if isinstance(notes, list):
            notes = "；".join(str(item) for item in notes if item)
        if not isinstance(notes, str) or not notes.strip():
            return None, "fallback"
        return notes.strip(), "llm"

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
        bars: list[dict] = evidence_pack.market_data.bars
        entry_price: float = evidence_pack.market_data.entry_price or 0.0
        target_price = evidence_pack.market_data.target_price
        stop_loss_price = evidence_pack.market_data.stop_loss_price

        symbol = evidence_pack.trade_idea.symbol if evidence_pack.trade_idea else ""
        mfe, mae, return_pct, exit_triggered, exit_date, halted_dates, eval_date = compute_mfe_mae_return(
            bars=bars,
            entry_price=entry_price,
            entry_date=evidence_pack.trade_date,
            target_price=target_price,
            stop_loss_price=stop_loss_price,
            symbol=symbol,
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

        # Step 4: 生成复盘笔记（优先 LLM，失败时回退结构化摘要）
        notes = None
        notes_source = "none"
        if self.enable_llm_notes:
            notes, notes_source = await self._generate_postmortem_notes(
                evidence_pack=evidence_pack,
                final_attribution=final_attribution,
                attribution_source=source,
                mfe=mfe,
                mae=mae,
                return_pct=return_pct,
                rules_hit=rules_hit,
                exit_triggered=exit_triggered,
                exit_date=exit_date,
            )
            if notes is None:
                notes = self._build_postmortem_notes(
                    evidence_pack=evidence_pack,
                    final_attribution=final_attribution,
                    attribution_source=source,
                    mfe=mfe,
                    mae=mae,
                    return_pct=return_pct,
                    rules_hit=rules_hit,
                    exit_triggered=exit_triggered,
                    exit_date=exit_date,
                )
                notes_source = "fallback"

        # 构建 extra（包含 NTL-S5-010 新增字段）
        # 停牌场景：exit_date 为 None 表示未实际出场，eval_date 为评估截止日
        result_extra: dict[str, object] = {
            **extra,
            "rules_hit": rules_hit,
            "exit_triggered": exit_triggered,
            "exit_date": exit_date,
            "eval_date": eval_date,
            "is_final": exit_triggered is not None,
            "notes_source": notes_source,
            "halted_dates": halted_dates,
            "halted_count": len(halted_dates),
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
        """从 prompts/llm_attribution.md 加载模板并填充变量。"""
        bars = market_data.get("bars", [])
        bars_str = json.dumps(bars, ensure_ascii=False, default=str) if bars else "无市场数据"

        entry = trade_idea.get("entry", {})
        if isinstance(entry, dict):
            entry_str = json.dumps(entry, ensure_ascii=False, default=str)
        else:
            entry_str = str(entry)

        # 加载模板并替换占位符
        template = _load_prompt("prompts/llm_attribution.md")
        result = template.replace("{symbol}", str(trade_idea.get("symbol", "N/A")))
        result = result.replace("{side}", str(trade_idea.get("side", "N/A")))
        result = result.replace("{entry}", entry_str)
        target_val = trade_idea.get("target_price", trade_idea.get("target", "N/A"))
        stop_loss_val = trade_idea.get("stop_loss_price", trade_idea.get("stop_loss", "N/A"))
        result = result.replace("{target}", str(target_val))
        result = result.replace("{stop_loss}", str(stop_loss_val))
        result = result.replace("{bars}", bars_str)
        result = result.replace("{auto_reason}", str(auto_attribution.get("reason", "N/A")))
        result = result.replace("{auto_confidence}", str(auto_attribution.get("confidence", 0.0)))
        return result
