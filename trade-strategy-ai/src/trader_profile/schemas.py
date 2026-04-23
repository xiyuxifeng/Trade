"""TraderProfile 类型扩展：策略偏好、风险风格、主题偏好、仓位倾向"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


# === 策略偏好相关枚举和模型 ===

class StrategyTimeframe(StrEnum):
    """策略时间框架"""
    INTRADAY = "intraday"      # 日内
    SWING = "swing"            # 波段
    POSITION = "position"      # 持仓（长线）


class StrategyPreference(BaseModel):
    """策略偏好"""
    timeframe: StrategyTimeframe | None = None                    # 时间框架
    entry_type: str | None = None                                  # 入场类型（如 breakout / mean_reversion / trend）
    position_style: str | None = None                              # 持仓风格（如 momentum / value / arbitrage）
    max_positions: int | None = None                                # 最大持仓数
    avg_holding_period: float | None = None                         # 平均持仓周期（天数）


class RiskStyle(StrEnum):
    """风险风格"""
    CONSERVATIVE = "conservative"    # 保守
    BALANCED = "balanced"            # 平衡
    AGGRESSIVE = "aggressive"        # 激进


class PositionBias(BaseModel):
    """仓位倾向"""
    directional: str = "neutral"                                  # long / short / neutral
    max_position_pct: float | None = None                         # 最大仓位占比（%）
    avg_position_pct: float | None = None                         # 平均仓位占比（%）


class ThemeStat(BaseModel):
    """主题偏好统计"""
    theme: str                                                    # 主题名称
    mentions: int = 0                                             # 提及次数


# === 原有类型保留 ===

class SymbolStat(BaseModel):
    """Lightweight symbol frequency stat used to build a trader profile."""

    symbol: str
    mentions: int = 0


class TraderProfile(BaseModel):
    """交易员画像（扩展版）。

    聚合文章元数据、风格聚类和策略偏好，支持策略版本构建器消费。
    """

    trader_id: str
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # === 原有字段（保留，向后兼容）===
    top_symbols: list[SymbolStat] = Field(default_factory=list)
    style_cluster_ids: list[str] = Field(default_factory=list)
    concept_tags: list[str] = Field(default_factory=list)
    evidence: dict[str, int] = Field(default_factory=dict)

    # === 扩展字段（支持策略版本构建）===
    strategy_preference: StrategyPreference | None = None         # 策略偏好
    risk_style: RiskStyle | None = None                            # 风险风格
    theme_preference: list[ThemeStat] = Field(default_factory=list)  # 主题偏好
    position_bias: PositionBias | None = None                      # 仓位倾向


class TraderProfilesFile(BaseModel):
    """Versioned on-disk container for all trader profiles."""

    schema_version: str = "v2"                                      # 升级为 v2
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    profiles_by_trader: dict[str, TraderProfile] = Field(default_factory=dict)