"""NTL-S6-001: 回测 schema 定义"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal


@dataclass(frozen=True)
class BacktestRequest:
    """回测请求参数。

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

    trader_id: str
    date_from: date
    date_to: date
    strategy_version_id: str | None = None
    symbols: list[str] = field(default_factory=list)
    mode: Literal["full", "replay", "rule_validation"] = "full"
    use_snapshot_only: bool = True
    scoring_profile: str = "stage5"


@dataclass(frozen=True)
class BacktestTradeRecord:
    """回测交易记录。

    属性：
        trade_date: 交易日期
        trader_id: 交易员 ID
        strategy_version_id: 策略版本 ID
        symbol: 标的代码
        entry_price: 入场价
        exit_price: 出场价
        entry_date: 入场日期
        exit_date: 出场日期
        return_pct: 收益率（比例口径，0.01=1%）
        mfe: 最大有利偏移（Max Favorable Excursion）
        mae: 最大不利偏移（Max Adverse Excursion）
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
    entry_date: date | None = None
    exit_date: date | None = None
    return_pct: float | None = None
    mfe: float | None = None
    mae: float | None = None
    skip_reason: str | None = None
    evidence_refs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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
