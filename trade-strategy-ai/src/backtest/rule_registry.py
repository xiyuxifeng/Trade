"""NTL-S6-009: LLM 规则白名单

职责：
- 对 LLM 抽出的规则做可程序化分类
- 提取规则所需字段
- 建立 rule_id -> RuleMeta 的映射
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backtest.schemas import RuleSnapshot


# 可程序化指标的字段名（用于提取 required_fields）
PROGRAMMABLE_INDICATORS = {
    "rsi": ["rsi"],
    "macd": ["macd", "macd_signal", "macd_hist"],
    "ma": ["ma5", "ma10", "ma20", "ma60", "ma120", "ma", "ema", "ema5", "ema20"],
    "boll": ["boll_upper", "boll_middle", "boll_lower"],
    "kdj": ["kdj_k", "kdj_d", "kdj_j"],
    "volume": ["volume", "vol", "amount"],
    "price": ["close", "open", "high", "low", "price"],
    "turnover": ["turnover_rate", "换手率"],
    "pe": ["pe", "市盈率"],
    "market_cap": ["market_cap", "市值"],
}

# 已知可程序化指标关键词
INDICATOR_PATTERNS = {
    "rsi": re.compile(r"\brsi\b", re.IGNORECASE),
    "macd": re.compile(r"macd", re.IGNORECASE),
    # MA: 匹配 ma/ema 后面跟数字（ma5, ma20, ema12 等），或单独出现
    # 前面不能是字母/数字（避免 "1ma" / "xma"），后面不能是字母/数字（避免 "market" / "max"）
    # 允许后面跟下划线，使 "ma5_cross" 等复合表达式能被识别
    "ma": re.compile(
        r"(?<![a-zA-Z0-9])ma\d*(?:_[a-zA-Z0-9]+)?(?![a-zA-Z0-9])|(?<![a-zA-Z0-9])ema\d*(?:_[a-zA-Z0-9]+)?(?![a-zA-Z0-9])",
        re.IGNORECASE,
    ),
    "boll": re.compile(r"\bboll\b|\b布林\b", re.IGNORECASE),
    "kdj": re.compile(r"\bkdj\b", re.IGNORECASE),
    # volume: 必须作为独立词出现，不含 ma_volume 等复合词
    "volume": re.compile(r"(?<![a-zA-Z0-9])volume(?![a-zA-Z0-9])|(?<![a-zA-Z0-9])vol(?![a-zA-Z0-9])", re.IGNORECASE),
    "price": re.compile(r"(?<![a-zA-Z])(?:close|open|high|low|收盘|开盘|最高|最低)(?![a-zA-Z])", re.IGNORECASE),
}


@dataclass(frozen=True)
class RuleMeta:
    """规则元数据。

    属性：
        rule_id: 规则 ID
        rule_text: 规则文本
        required_fields: 验证该规则所需的字段列表
        programmatic_level: 可程序化程度
            - "fully_programmable": 可完全程序化
            - "partially_programmable": 部分可程序化
            - "descriptive_only": 纯描述性，不可验证
            - "unsupported": 不支持的规则
    """

    rule_id: str
    rule_text: str
    required_fields: list[str] = field(default_factory=list)
    programmatic_level: str = "unsupported"


def classify_rule(rule: RuleSnapshot) -> RuleMeta:
    """对单条规则进行可程序化分类。

    分类逻辑：
    1. 提取 rule_id（没有则用空字符串）
    2. 提取 rule_text（取 condition 或 text 字段）
    3. 在 rule_text 中搜索已知指标关键词
    4. 若找到指标，返回 "fully_programmable" + 所需字段列表
    5. 若未找到，返回 "unsupported" 或 "descriptive_only"

    Args:
        rule: 规则快照（RuleSnapshot），至少包含 condition/text 之一

    Returns:
        RuleMeta 实例
    """
    rule_id = str(rule.get("rule_id", "") or "")
    rule_text = rule.get("condition") or rule.get("text") or rule.get("rule_text") or ""

    found_fields: list[str] = []
    for indicator_name, pattern in INDICATOR_PATTERNS.items():
        if pattern.search(rule_text):
            found_fields.extend(PROGRAMMABLE_INDICATORS.get(indicator_name, [indicator_name]))

    # 去重
    found_fields = list(dict.fromkeys(found_fields))

    if found_fields:
        programmatic_level = "fully_programmable"
    elif any(keyword in rule_text for keyword in ["关注", "注意", "观察", "考虑"]):
        programmatic_level = "descriptive_only"
    else:
        programmatic_level = "unsupported"

    return RuleMeta(
        rule_id=rule_id,
        rule_text=rule_text,
        required_fields=found_fields,
        programmatic_level=programmatic_level,
    )


class RuleRegistry:
    """规则注册表，支持可执行性过滤。

    S10-006: 支持按可执行性水平过滤规则
    """

    def __init__(self):
        self._rules: dict[str, RuleMeta] = {}

    def register_rule(self, rule_meta: RuleMeta) -> None:
        """注册一条规则"""
        self._rules[rule_meta.rule_id] = rule_meta

    def list_programmable_rules(
        self, min_level: str = "fully_programmable"
    ) -> list[RuleMeta]:
        """列出可执行性 >= min_level 的规则。

        Args:
            min_level: 最低可执行性水平，可选值：
                - "unsupported": 所有规则
                - "descriptive_only": 包含 descriptive_only 及以上
                - "partially_programmable": 包含 partially_programmable 及以上
                - "fully_programmable" (默认): 仅 fully_programmable

        Returns:
            符合条件的 RuleMeta 列表
        """
        level_order = {
            "unsupported": 0,
            "descriptive_only": 1,
            "partially_programmable": 2,
            "fully_programmable": 3,
        }
        min_score = level_order.get(min_level, 0)
        return [
            r for r in self._rules.values()
            if level_order.get(r.programmatic_level, 0) >= min_score
        ]

    def get_rule(self, rule_id: str) -> RuleMeta | None:
        """根据 rule_id 获取规则元数据"""
        return self._rules.get(rule_id)

    def clear(self) -> None:
        """清空所有已注册的规则"""
        self._rules.clear()
