"""市场候选池数据结构定义。

职责：
- 定义 HotTopic、TopicConstituent、StrongSymbol 等原子数据结构
- 定义 HotTopicsPayload、TopicConstituentsPayload、StrongSymbolsPayload 等聚合结构
- 为 builder/selector/service 提供统一的类型契约
- 与 ORM 模型完全解耦，仅约束内存数据结构
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


# ============================
# 热点主题（Hot Topics）
# ============================

@dataclass(frozen=True)
class HotTopic:
    """单个热点主题。"""

    kind: str                          # e.g. "concept", "industry", "concept_fengkou"
    topic_id: str                      # 板块/概念 ID
    topic_name: str                    # 板块/概念名称
    score: float | None = None         # 综合得分
    increase_pct: float | None = None  # 涨跌幅 %
    speed_pct: float | None = None    # 涨速 %
    turnover: float | None = None      # 成交额（万元）
    net_inflow: float | None = None    # 净流入（万元）


@dataclass(frozen=True)
class HotTopicsPayload:
    """热点主题聚合 payload。"""

    trade_date: str                    # ISO 格式日期
    slot: str                          # 时段标识，如 "09-25"
    topics: list[HotTopic] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    fetched_at: datetime | None = None


# ============================
# 题材成分（Topic Constituents）
# ============================

@dataclass(frozen=True)
class TopicConstituent:
    """单个题材成分。"""

    kind: str                          # e.g. "stock_sector_v2", "theme_detail", "limit_up_reason", "limit_up_info", "lhb_list"
    topic_id: str | None = None       # 题材 ID（部分 kind 有）
    topic_name: str | None = None    # 题材名称
    symbol: str | None = None        # 股票代码（部分 kind 有）
    name: str | None = None           # 名称
    # kind 特定字段
    topic_change_pct: float | None = None
    leader_symbol: str | None = None
    leader_name: str | None = None
    leader_change_pct: float | None = None
    board_num: int | None = None      # 涨停板数量
    net_buy: float | None = None     # 龙虎榜净买入
    brief_intro: str | None = None   # 主题简介


@dataclass(frozen=True)
class TopicConstituentsPayload:
    """题材成分聚合 payload。"""

    trade_date: str
    slot: str
    constituents: list[TopicConstituent] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    fetched_at: datetime | None = None


# ============================
# 强势标的（Strong Symbols）
# ============================

@dataclass(frozen=True)
class StrongSymbol:
    """单个强势标的。"""

    kind: str                          # e.g. "strong_fengkou", "interval_stats_stock", "morning_bidding_list"
    symbol: str | None = None         # 股票代码
    name: str | None = None           # 名称
    strength_score: float | None = None  # 强势得分
    change_pct: float | None = None   # 涨跌幅 %
    turnover: float | None = None     # 成交额
    turnover_ratio: float | None = None  # 换手率 %
    return_pct: float | None = None   # 区间的收益率 %
    net_inflow: float | None = None   # 净流入
    main_force_buy: float | None = None
    main_force_sell: float | None = None
    rt_change_pct: float | None = None  # 竞价涨幅 %
    bid_net: float | None = None      # 竞价净买额
    bid_turnover: float | None = None  # 竞价成交额
    topic_tags: str | None = None    # 题材标签


@dataclass(frozen=True)
class StrongSymbolsPayload:
    """强势标的聚合 payload。"""

    trade_date: str
    slot: str
    symbols: list[StrongSymbol] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    fetched_at: datetime | None = None


# ============================
# 候选池聚合（Market Universe）
# ============================

@dataclass(frozen=True)
class MarketUniverse:
    """候选池顶层聚合结构。

    包含热点、题材成分、强势标的三类数据快照，
    可按需组合供 TraderAgent 或 StrategyAgent 消费。
    """

    trade_date: str
    slot: str
    hot_topics: HotTopicsPayload | None = None
    topic_constituents: TopicConstituentsPayload | None = None
    strong_symbols: StrongSymbolsPayload | None = None
    fetched_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
