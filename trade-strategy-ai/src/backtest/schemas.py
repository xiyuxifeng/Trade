"""NTL-S6-001: 回测 schema 定义

包含：
- BacktestRequest（Pydantic BaseModel，带字段校验）
- BacktestTradeRecord / BacktestSummary / BacktestResult（dataclass）
- RuleValidationResult（dataclass）
- MarketContextSnapshot（TypedDict）：市场上下文快照类型约束
- RuleSnapshot（TypedDict）：规则快照类型约束
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Pydantic 请求模型（C2：支持自动校验和 JSON 序列化）
# ---------------------------------------------------------------------------
class BacktestRequest(BaseModel):
    """回测请求参数（Pydantic BaseModel，支持字段校验）。

    属性：
        trader_id: 交易员 ID
        date_from: 回测开始日期
        date_to: 回测结束日期
        strategy_version_id: 特定策略版本 ID（None 时按 trader_id + trade_date 自动读取历史 released 版本）
        symbols: 限定标的列表（空列表表示全部标的）
        mode: 运行模式
            - "full": 完整回测（重放 + 评分）
            - "replay": 仅重放策略版本
            - "rule_validation": 仅规则验真
        use_snapshot_only: 是否仅使用快照数据（禁止实时 provider 调用）
        scoring_profile: 评分配置名（默认 stage5）
    """

    model_config = {"frozen": True}

    trader_id: str
    date_from: date
    date_to: date
    strategy_version_id: str | None = None
    symbols: list[str] = Field(default_factory=list)
    mode: Literal["full", "replay", "rule_validation"] = "full"
    use_snapshot_only: bool = True
    scoring_profile: str = "stage5"

    @model_validator(mode="after")
    def check_date_order(self) -> "BacktestRequest":
        """校验 date_from <= date_to"""
        if self.date_from > self.date_to:
            raise ValueError("date_from 必须小于或等于 date_to")
        return self


# ---------------------------------------------------------------------------
# TypedDict：上游数据结构约束（C1 / C3）
# ---------------------------------------------------------------------------
class MarketContextSnapshot(TypedDict, total=False):
    """市场上下文快照（由 SnapshotLoader.load_market_context 返回）。

    属性说明见 snapshot_loader.py；此 TypedDict 为下游模块提供类型约束。
    """

    trade_date: str  # YYYY-MM-DD
    bars_by_symbol: dict[str, list[dict[str, Any]]]
    indicators_by_symbol: dict[str, dict[str, Any]]
    market_universe: Any
    topic_snapshot: Any
    source_refs: list[str]
    compatibility_fallback: bool
    listing_dates: dict[str, str]  # symbol -> YYYY-MM-DD，用于新股判断


class RuleSnapshot(TypedDict, total=False):
    """单条规则快照（StrategyVersion.rules_snapshot 中的元素）。

    C3: 将松散的 list[dict] 约束为包含必要字段的 TypedDict。
    """

    rule_id: str
    condition: str
    text: str
    rule_text: str
    action: str
    confidence: float
    weight: float
    required_fields: list[str]


# ---------------------------------------------------------------------------
# dataclass：回测核心数据结构
# ---------------------------------------------------------------------------
@dataclass
class BacktestTradeRecord:
    """回测交易记录。

    属性：
        trade_date: 交易日期
        trader_id: 交易员 ID
        strategy_version_id: 策略版本 ID
        symbol: 标的代码
        entry_price: 入场价
        exit_price: 出场价
        entry_date: 入场日期（YYYY-MM-DD）
        exit_date: 出场日期（YYYY-MM-DD）
        return_pct: 收益率（比例口径，0.01=1%）
        mfe: 最大有利偏移（Max Favorable Excursion）
        mae: 最大不利偏移（Max Adverse Excursion）
        volume: 交易量（股）
        is_valid_lot_size: 买入交易量是否符合 100 股整数倍
            - True: 符合 A 股最小交易单位
            - False: 不符合（如 150 股）
            - None: 未校验或卖出操作
        status: 交易状态
            - "open": 持仓中
            - "closed": 已平仓
            - "skipped": 跳过（无版本/无快照）
            - "invalid": 无效（缺价等）
        skip_reason: 跳过原因（status=skipped 时填写）
        evidence_refs: 证据引用列表
    """

    trade_date: date
    trader_id: str
    strategy_version_id: str
    symbol: str
    status: Literal["open", "closed", "skipped", "invalid"]
    entry_price: float | None = None
    exit_price: float | None = None
    entry_date: str | None = None
    exit_date: str | None = None
    return_pct: float | None = None
    mfe: float | None = None
    mae: float | None = None
    volume: int | None = None
    is_valid_lot_size: bool | None = None
    skip_reason: str | None = None
    evidence_refs: list[str] = field(default_factory=list)


@dataclass
class BacktestSummary:
    """回测汇总统计。

    属性：
        total_days: 覆盖天数
        total_trades: 总交易笔数
        valid_trades: 有效交易笔数（closed + open）
        skipped_trades: 跳过笔数
        win_rate: 胜率（有效交易中盈利笔数占比）
        avg_return_pct: 平均收益率
    """

    total_days: int
    total_trades: int
    valid_trades: int
    skipped_trades: int
    win_rate: float | None = None
    avg_return_pct: float | None = None


@dataclass
class BacktestResult:
    """回测结果聚合。

    属性：
        request_trader_id: 请求方 trader_id
        request_date_from: 请求开始日期
        request_date_to: 请求结束日期
        records: 交易记录列表
        summary: 汇总统计
    """

    request_trader_id: str
    request_date_from: date
    request_date_to: date
    records: list[BacktestTradeRecord] = field(default_factory=list)
    summary: BacktestSummary | None = None
    result_version: str = "1.0"  # S7-009: 用于区分新旧格式


@dataclass
class RuleValidationResult:
    """单条规则验真结果。

    属性：
        trader_id: 交易员 ID
        strategy_version_id: 策略版本 ID
        rule_id: 规则 ID
        rule_text: 规则文本
        programmable: 是否可程序化验证
        validation_status: 验真状态
            - "validated": 已验真
            - "unsupported_rule": 规则不可程序化
            - "missing_field": 缺少必要字段
            - "missing_snapshot": 快照缺失
            - "invalid_rule": 规则本身无效
        hit_count: 命中次数
        sample_count: 样本总数
        hit_rate: 命中率
        posterior_return_mean: 命中后验收益均值
        posterior_return_median: 命中后验收益中位数
        notes: 说明列表
    """

    trader_id: str
    strategy_version_id: str
    rule_id: str
    rule_text: str
    programmable: bool
    validation_status: Literal[
        "validated",
        "unsupported_rule",
        "missing_field",
        "missing_snapshot",
        "invalid_rule",
    ]
    hit_count: int = 0
    sample_count: int = 0
    hit_rate: float | None = None
    posterior_return_mean: float | None = None
    posterior_return_median: float | None = None
    notes: list[str] = field(default_factory=list)
    result_version: str = "1.0"  # S7-009: 用于区分新旧格式
