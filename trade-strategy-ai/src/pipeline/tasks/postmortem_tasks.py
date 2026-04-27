"""postmortem_analysis 任务处理器：NTL-S5-008。

职责：
- 对未通过评估的 idea 执行自动归因
- 将归因结果写入 TraderMemory（类型：postmortem）
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from src.common.config import AppConfig
from src.evaluation.evidence_pack import EvidencePack, MarketDataSnapshot
from src.evaluation.postmortem_service import PostmortemService
from src.common.logger import get_logger
from src.common.utils import read_json
from src.schemas.contracts import DataRequest, DataResponseStatus, DailyReport, TradeIdea
from src.trader_memory.schemas import TraderMemoryFilter, TraderMemoryItem, TraderMemoryType
from src.trader_memory.service import TraderMemoryStore, default_memory_path
from src.llm.client import LLMClient, from_env_and_config

logger = get_logger(__name__)


def _find_evidence_pack_id(idea_id_str: str, config: AppConfig) -> str | None:
    """从 evidence_packs 索引中查找对应 idea_id 的 pack_id。

    优先读取 evidence_pack_index.json（O(1)），不存在时降级为目录遍历。

    Returns:
        pack_id 字符串或 None
    """
    pack_dir = Path(".") / config.storage.output_dir / "evidence_packs"
    if not pack_dir.exists():
        return None

    # 优先读取索引文件（O(1)）
    index_path = pack_dir / "evidence_pack_index.json"
    if index_path.exists():
        try:
            index = read_json(index_path) or {}
            pack_id = index.get(idea_id_str)
            if pack_id:
                return pack_id
        except Exception:
            pass

    # 降级：目录遍历（兼容旧数据）
    for pack_file in pack_dir.glob("*.json"):
        if pack_file.name == "evidence_pack_index.json":
            continue
        try:
            data = read_json(pack_file)
            if data.get("idea_id") == idea_id_str:
                return pack_file.stem
        except Exception:
            continue
    return None


def _evidence_pack_path(pack_id: str, config: AppConfig) -> Path:
    """获取 EvidencePack JSON 文件路径。"""
    return Path(".") / config.storage.output_dir / "evidence_packs" / f"{pack_id}.json"


def _build_llm_notes_client(config: AppConfig):
    """根据配置构建 LLM 笔记客户端，配置缺失时返回 None。"""
    llm_cfg = getattr(config, "llm", None)
    provider = getattr(llm_cfg, "provider", None)
    model = getattr(llm_cfg, "model", None)
    url = getattr(llm_cfg, "url", None)
    api_key = getattr(llm_cfg, "api_key", None)

    if not (
        isinstance(provider, str) and provider.strip()
        and (
            isinstance(model, str) and model.strip()
            or isinstance(model, list) and any(isinstance(m, str) and m.strip() for m in model)
        )
        and isinstance(url, str) and url.strip()
        and isinstance(api_key, str) and api_key.strip()
    ):
        return None

    llm_client = LLMClient(
        from_env_and_config(
            provider=provider,
            model=model if isinstance(model, (str, list)) else None,
            url=url,
            api_key=api_key,
        )
    )
    return llm_client if llm_client.is_enabled() else None


async def handle_postmortem_analysis(
    details: dict[str, Any],
    *,
    config: AppConfig,
) -> None:
    """对单笔交易执行自动归因并写回 TraderMemory。

    Details 参数：
        idea_id: UUID string — TradeIdea.idea_id
        trade_date: YYYY-MM-DD — 交易日
        trader_id: str — 用于 TraderMemory
        symbol: str — 用于参考
    """
    idea_id_str: str | None = details.get("idea_id")
    trade_date_str: str | None = details.get("trade_date")
    trader_id: str | None = details.get("trader_id")
    symbol: str | None = details.get("symbol")

    if not idea_id_str or not trade_date_str:
        logger.warning(
            "Postmortem跳过: idea_id或trade_date缺失, details=%s",
            details,
        )
        return

    # 加载 DailyReport
    report_path = _daily_report_path(trade_date_str, config)
    if not report_path.exists():
        logger.warning(
            "Postmortem跳过: DailyReport不存在, path=%s",
            report_path,
        )
        return

    report_data = read_json(report_path)
    daily_report = DailyReport.model_validate(report_data)

    # 找到对应 TradeIdea
    trade_idea: TradeIdea | None = None
    for idea in daily_report.ideas:
        if str(idea.idea_id) == idea_id_str:
            trade_idea = idea
            break

    if trade_idea is None:
        logger.warning(
            "Postmortem跳过: 未找到idea, idea_id=%s",
            idea_id_str,
        )
        return

    # 获取当前价格（NTL-S5-009 完成前：用 last_price 代替完整行情）
    last_prices = await _fetch_last_prices([symbol or trade_idea.symbol], config)

    # NTL-S5-009: 从持久化的 JSON 文件加载 EvidencePack
    pack_id = _find_evidence_pack_id(idea_id_str, config)
    if pack_id:
        pack_path = _evidence_pack_path(pack_id, config)
        if pack_path.exists():
            pack_data = read_json(pack_path)
            evidence_pack = EvidencePack.from_dict(pack_data)
        else:
            # fallback：降级到最小实现（保留容错）
            fallback_price = last_prices.get(symbol or trade_idea.symbol)
            fallback_bars = []
            if fallback_price is not None:
                fallback_bars = [{
                    "date": str(trade_idea.as_of_date),
                    "open": fallback_price,
                    "high": fallback_price,
                    "low": fallback_price,
                    "close": fallback_price,
                }]
            evidence_pack = EvidencePack(
                idea_id=trade_idea.idea_id,
                trade_date=str(trade_idea.as_of_date),
                trade_idea=trade_idea,
                signal_context=None,
                market_data=MarketDataSnapshot(
                    last_price=fallback_price,
                    bars=fallback_bars,
                    entry_price=float(trade_idea.entry.price) if trade_idea.entry and trade_idea.entry.price else 0.0,
                    target_price=trade_idea.target_price,
                    stop_loss_price=trade_idea.stop_loss_price,
                ),
                strategy_version_id=trade_idea.strategy_version_id,
                strategy_version_snapshot=[],
            )
    else:
        # fallback：降级到最小实现
        fallback_price = last_prices.get(symbol or trade_idea.symbol)
        fallback_bars = []
        if fallback_price is not None:
            fallback_bars = [{
                "date": str(trade_idea.as_of_date),
                "open": fallback_price,
                "high": fallback_price,
                "low": fallback_price,
                "close": fallback_price,
            }]
        evidence_pack = EvidencePack(
            idea_id=trade_idea.idea_id,
            trade_date=str(trade_idea.as_of_date),
            trade_idea=trade_idea,
            signal_context=None,
            market_data=MarketDataSnapshot(
                last_price=fallback_price,
                bars=fallback_bars,
                entry_price=float(trade_idea.entry.price) if trade_idea.entry and trade_idea.entry.price else 0.0,
                target_price=trade_idea.target_price,
                stop_loss_price=trade_idea.stop_loss_price,
            ),
            strategy_version_id=trade_idea.strategy_version_id,
            strategy_version_snapshot=[],
        )

    # 执行自动归因
    service = PostmortemService(
        enable_llm_notes=True,
        llm_notes_client=_build_llm_notes_client(config),
    )
    result = await service.generate(evidence_pack)

    # 构建 postmortem_data（NTL-S5-012）
    postmortem_data = {
        "root_causes": result.failure_attribution.root_causes,
        "stage": result.failure_attribution.stage,
        "rule_type": result.failure_attribution.rule_type,
        "attribution_source": result.attribution_source,
        "mfe": result.mfe,
        "mae": result.mae,
        "return_pct": result.return_pct,
        "postmortem_notes": result.postmortem_notes,
    }

    # NTL-S5-012: 尝试找到对应的 failure_case 并原地更新
    memory_path = default_memory_path(base_dir=Path("."), config=config)
    store = TraderMemoryStore(path=memory_path)

    # 从 details 提取 auto_attribution（NTL-S5-012 新增）
    auto_attribution = details.get("auto_attribution") or {}

    f = TraderMemoryFilter(
        trader_id=trader_id or trade_idea.trader_id,
        memory_types=[TraderMemoryType.failure_case],
        symbol=trade_idea.symbol,
        date_from=trade_idea.as_of_date,
        date_to=trade_idea.as_of_date,
        include_archived=False,
    )
    failure_cases = store.list_filtered(f)

    if failure_cases:
        # 原地更新已有的 failure_case 条目（NTL-S5-012）
        failure_case = failure_cases[0]
        updated = failure_case.model_copy(deep=True)
        updated.postmortem_data = postmortem_data
        updated.content = (
            f"attribution={result.failure_attribution.root_causes}, "
            f"source={result.attribution_source}, notes={result.postmortem_notes or 'n/a'}"
        )
        updated.extra = failure_case.extra or {}
        updated.extra["auto_original"] = auto_attribution
        store.update(failure_case.memory_id, updated)
        logger.info(
            "Postmortem已更新failure_case: idea_id=%s, attribution=%s",
            idea_id_str,
            result.failure_attribution.root_causes,
        )
    else:
        # Fallback: append 新条目（兼容边界情况）
        memory = TraderMemoryItem(
            trader_id=trader_id or trade_idea.trader_id,
            memory_type=TraderMemoryType.postmortem,
            as_of_date=trade_idea.as_of_date,
            symbol=trade_idea.symbol,
            title=f"Postmortem: {trade_idea.symbol} on {trade_idea.as_of_date}",
            content=(
                f"attribution={result.failure_attribution.root_causes}, "
                f"source={result.attribution_source}, notes={result.postmortem_notes or 'n/a'}"
            ),
            source="postmortem_task",
            source_ref=str(trade_idea.idea_id),
            tags=["postmortem", trade_idea.trader_id, trade_idea.symbol],
            topic_source=None,
            raw_topic_ids={},
            importance=0.9,
            postmortem_data=postmortem_data,
            extra={"auto_original": auto_attribution},
        )
        store.append(memory)
        logger.info(
            "Postmortem已写入memory: idea_id=%s, attribution=%s, mfe=%.2f, mae=%.2f",
            idea_id_str,
            result.failure_attribution.root_causes,
            result.mfe,
            result.mae,
        )


def _daily_report_path(trade_date_str: str, config: AppConfig) -> Path:
    """获取 DailyReport 文件路径。

    路径规则：{config.storage.output_dir}/daily_report_{trade_date}.json
    """
    output_dir = Path(".") / config.storage.output_dir
    return output_dir / f"daily_report_{trade_date_str}.json"


async def _fetch_last_prices(symbols: list[str], config: AppConfig) -> dict[str, float]:
    """通过 DataAgent 获取当前价格。"""
    from src.agents.data_agent.agent import DataAgent

    if not symbols:
        return {}

    agent = DataAgent(config=config)
    req = DataRequest(trader_id="postmortem", symbols=symbols, fields=["last_price"])
    resp = await agent.handle(req)

    if resp.status == DataResponseStatus.ok:
        return resp.payload.get("last_price", {})
    return {}
