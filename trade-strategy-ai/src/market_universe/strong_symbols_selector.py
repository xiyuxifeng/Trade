"""强势池选择器。

职责：
- 将 StrongSymbolsProvider 的标准化输出转换为 StrongSymbolsPayload
- 实例化 StrongSymbol dataclass
- 对 symbols 去重
"""
from __future__ import annotations

from datetime import datetime

from src.market_universe.schemas import StrongSymbol, StrongSymbolsPayload


class StrongSymbolsSelector:
    """将 provider 输出构建为 StrongSymbolsPayload。"""

    def build(self, provider_payload: dict) -> StrongSymbolsPayload:
        """从 provider 标准化输出构建 StrongSymbolsPayload。

        Args:
            provider_payload: KaipanProvider.fetch_strong_symbols() 返回的 dict，
                包含 symbols list、trade_date、slot、sources。
                当 FallbackProvider 返回 partial=True 时，
                从 partial_payloads 中合并多个 symbols 列表。

        Returns:
            StrongSymbolsPayload dataclass 实例。
        """
        # NTL-S4-TD002: 处理 FallbackProvider 返回的 partial 结果
        if provider_payload.get("partial"):
            partial_payloads = provider_payload.get("partial_payloads", [])
            raw_symbols = []
            trade_date = ""
            slot = ""
            sources = []
            for p in partial_payloads:
                raw_symbols.extend(p.get("symbols", []))
                trade_date = trade_date or p.get("trade_date", "")
                slot = slot or p.get("slot", "")
                sources.extend(p.get("sources", []))
        else:
            raw_symbols = provider_payload.get("symbols", [])
            trade_date = provider_payload.get("trade_date", "")
            slot = provider_payload.get("slot", "")
            sources = provider_payload.get("sources", [])

        # 实例化 StrongSymbol，去重（按 kind + symbol）
        seen: set[tuple[str, str | None]] = set()
        symbols: list[StrongSymbol] = []

        for item in raw_symbols:
            kind = item.get("kind", "")
            symbol = item.get("symbol")
            key = (kind, symbol)
            if key in seen:
                continue
            seen.add(key)

            strong_symbol = StrongSymbol(
                kind=kind,
                symbol=symbol,
                name=item.get("name"),
                strength_score=item.get("strength_score"),
                change_pct=item.get("change_pct"),
                turnover=item.get("turnover"),
                turnover_ratio=item.get("turnover_ratio"),
                return_pct=item.get("return_pct"),
                net_inflow=item.get("net_inflow"),
                main_force_buy=item.get("main_force_buy"),
                main_force_sell=item.get("main_force_sell"),
                rt_change_pct=item.get("rt_change_pct"),
                bid_net=item.get("bid_net"),
                bid_turnover=item.get("bid_turnover"),
                topic_tags=item.get("topic_tags"),
            )
            symbols.append(strong_symbol)

        return StrongSymbolsPayload(
            trade_date=trade_date,
            slot=slot,
            symbols=symbols,
            sources=list(sources),
            fetched_at=datetime.now(),
        )