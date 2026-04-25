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
from src.evaluation.evidence_pack import EvidencePack
from src.evaluation.postmortem_service import PostmortemService
from src.common.utils import read_json
from src.schemas.contracts import DataRequest, DataResponseStatus, DailyReport, TradeIdea
from src.trader_memory.schemas import TraderMemoryItem, TraderMemoryType
from src.trader_memory.service import TraderMemoryStore, default_memory_path


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
        print(f"[postmortem] idea_id 或 trade_date 缺失，跳过: {details}")
        return

    # 加载 DailyReport
    report_path = _daily_report_path(trade_date_str, config)
    if not report_path.exists():
        print(f"[postmortem] DailyReport 不存在: {report_path}，跳过")
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
        print(f"[postmortem] 未找到 idea_id={idea_id_str}，跳过")
        return

    # 获取当前价格（NTL-S5-009 完成前：用 last_price 代替完整行情）
    last_prices = await _fetch_last_prices([symbol or trade_idea.symbol], config)

    # 构造 EvidencePack（NTL-S5-009 完成前：最小实现）
    evidence_pack = EvidencePack(
        idea_id=trade_idea.idea_id,
        trade_date=str(trade_idea.as_of_date),
        trade_idea=trade_idea,
        signal_context=None,  # NTL-S5-009 后从 signal_versioning 加载
        market_data={"last_price": last_prices.get(symbol or trade_idea.symbol)},
        strategy_version_id=trade_idea.strategy_version_id,
        strategy_version_snapshot=[],  # NTL-S5-009 后填充 rules_snapshot
    )

    # 执行自动归因
    service = PostmortemService()
    result = await service.generate(evidence_pack)

    # 写入 TraderMemory
    memory = TraderMemoryItem(
        trader_id=trader_id or trade_idea.trader_id,
        memory_type=TraderMemoryType.postmortem,
        as_of_date=trade_idea.as_of_date,
        symbol=trade_idea.symbol,
        title=f"Postmortem: {trade_idea.symbol} on {trade_idea.as_of_date}",
        content=f"attribution={result.failure_attribution.root_causes}, source={result.attribution_source}",
        source="postmortem_task",
        source_ref=str(trade_idea.idea_id),
        tags=["postmortem", trade_idea.trader_id, trade_idea.symbol],
        topic_source=None,
        raw_topic_ids={},
        importance=0.9,
        postmortem_data={
            "root_causes": result.failure_attribution.root_causes,
            "stage": result.failure_attribution.stage,
            "rule_type": result.failure_attribution.rule_type,
            "attribution_source": result.attribution_source,
            "mfe": result.mfe,
            "mae": result.mae,
            "return_pct": result.return_pct,
        },
    )

    # 写入 TraderMemoryStore
    memory_path = default_memory_path(base_dir=Path("."), config=config)
    store = TraderMemoryStore(path=memory_path)
    store.append(memory)

    print(f"[postmortem] 已写入 memory for idea_id={idea_id_str}, attribution={result.failure_attribution.root_causes}")


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
