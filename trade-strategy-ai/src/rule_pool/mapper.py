"""rule_pool.mapper - DSL 映射工具

将提取层(ExtractionLayer)的 raw_condition 映射为执行层(execution layer)的 mapped_condition
"""

from typing import Any

# 标准操作符
OPERATORS = ["and", "or", "not", "gt", "lt", "eq", "gte", "lte", "in", "not_in", "cross_above", "cross_below", "cmp"]

# 标准字段库
STANDARD_FIELDS = [
    "close", "open", "high", "low", "volume",
    "ma5", "ma10", "ma20", "ma60", "ma120", "ma250",
    "ema5", "ema10", "ema20", "ema60",
    "macd", "macd_signal", "macd_hist",
    "rsi6", "rsi12", "rsi24",
    "bollinger_upper", "bollinger_middle", "bollinger_lower",
    "kdj_k", "kdj_d", "kdj_j",
    "volume_ratio", "turnover_rate",
]

# 常用映射规则
MAPPING_RULES = {
    # ========== 量能相关 ==========
    ("放量", "volume_ratio_above"): {"op": "gt", "field": "volume_ratio", "value": 1.5},
    ("缩量", "volume_ratio_below"): {"op": "lt", "field": "volume_ratio", "value": 0.7},
    ("巨量", "volume_ratio_above"): {"op": "gt", "field": "volume_ratio", "value": 3.0},
    ("地量", "volume_ratio_below"): {"op": "lt", "field": "volume_ratio", "value": 0.3},
    # ========== 价格相关 ==========
    ("突破", "close_above"): None,  # 需要更多上下文
    ("跌破", "close_below"): None,
    ("创新高", "close_above_ma"): None,  # 需要指定参考均线
    ("创新低", "close_below_ma"): None,
    ("涨停", "close_pct_above"): {"op": "gte", "field": "close_pct_change", "value": 9.8},
    ("跌停", "close_pct_below"): {"op": "lte", "field": "close_pct_change", "value": -9.8},
    # ========== MACD 相关 ==========
    ("macd金叉", "macd_cross_above_signal"): {"op": "cross_above", "field": "macd", "other_field": "macd_signal"},
    ("macd死叉", "macd_cross_below_signal"): {"op": "cross_below", "field": "macd", "other_field": "macd_signal"},
    ("macd柱翻红", "macd_hist_above"): {"op": "gt", "field": "macd_hist", "value": 0},
    ("macd柱翻绿", "macd_hist_below"): {"op": "lt", "field": "macd_hist", "value": 0},
    # ========== KDJ 相关 ==========
    ("kdj金叉", "kdj_cross_above"): {"op": "cross_above", "field": "kdj_k", "other_field": "kdj_d"},
    ("kdj死叉", "kdj_cross_below"): {"op": "cross_below", "field": "kdj_k", "other_field": "kdj_d"},
    ("kdj超买", "kdj_above"): {"op": "gt", "field": "kdj_k", "value": 80},
    ("kdj超卖", "kdj_below"): {"op": "lt", "field": "kdj_k", "value": 20},
    # ========== 指标相关 ==========
    ("金叉", "cross_above"): None,
    ("死叉", "cross_below"): None,
    ("超卖", "rsi_below"): {"op": "lt", "field": "rsi6", "value": 30},
    ("超买", "rsi_above"): {"op": "gt", "field": "rsi6", "value": 70},
    # ========== 均线系统 ==========
    ("ma多头排列", "ma_bullish_aligned"): {"op": "and", "conditions": [
        {"op": "gt", "field": "ma5", "value_field": "ma10"},
        {"op": "gt", "field": "ma10", "value_field": "ma20"},
        {"op": "gt", "field": "ma20", "value_field": "ma60"},
    ]},
    ("ma空头排列", "ma_bearish_aligned"): {"op": "and", "conditions": [
        {"op": "lt", "field": "ma5", "value_field": "ma10"},
        {"op": "lt", "field": "ma10", "value_field": "ma20"},
        {"op": "lt", "field": "ma20", "value_field": "ma60"},
    ]},
    # ========== 布林带 ==========
    ("bollinger上轨", "close_above_bollinger_upper"): {"op": "gt", "field": "close", "value_field": "bollinger_upper"},
    ("bollinger中轨", "close_above_bollinger_middle"): {"op": "gt", "field": "close", "value_field": "bollinger_middle"},
    ("bollinger下轨", "close_below_bollinger_lower"): {"op": "lt", "field": "close", "value_field": "bollinger_lower"},
    # ========== 量价关系 ==========
    ("价涨量增", "price_up_volume_up"): {"op": "and", "conditions": [
        {"op": "gt", "field": "close_pct_change", "value": 0},
        {"op": "gt", "field": "volume_ratio", "value": 1.2},
    ]},
    ("价跌量缩", "price_down_volume_down"): {"op": "and", "conditions": [
        {"op": "lt", "field": "close_pct_change", "value": 0},
        {"op": "lt", "field": "volume_ratio", "value": 0.8},
    ]},
    # ========== 换手率 ==========
    ("高换手", "turnover_high"): {"op": "gt", "field": "turnover_rate", "value": 10},
    ("低换手", "turnover_low"): {"op": "lt", "field": "turnover_rate", "value": 1},
}


def suggest_mapping(raw_text: str) -> list[dict[str, Any]]:
    """根据原始文本建议可能的映射

    Args:
        raw_text: 原始条件文本

    Returns:
        可能的映射建议列表，每个元素包含:
            - pattern: 匹配的模式
            - confidence: 置信度 (0-1)
            - suggestion: 建议的映射配置
            - requires_context: 是否需要更多上下文
    """
    suggestions = []
    raw_lower = raw_text.lower()

    # ========== 量能相关 ==========
    if "放量" in raw_text:
        suggestions.append({
            "pattern": "放量",
            "confidence": 0.9,
            "suggestion": {"op": "gt", "field": "volume_ratio", "value": 1.5},
            "requires_context": False,
        })

    if "缩量" in raw_text:
        suggestions.append({
            "pattern": "缩量",
            "confidence": 0.9,
            "suggestion": {"op": "lt", "field": "volume_ratio", "value": 0.7},
            "requires_context": False,
        })

    if "巨量" in raw_text:
        suggestions.append({
            "pattern": "巨量",
            "confidence": 0.85,
            "suggestion": {"op": "gt", "field": "volume_ratio", "value": 3.0},
            "requires_context": False,
        })

    if "地量" in raw_text:
        suggestions.append({
            "pattern": "地量",
            "confidence": 0.85,
            "suggestion": {"op": "lt", "field": "volume_ratio", "value": 0.3},
            "requires_context": False,
        })

    # ========== 价格突破相关 ==========
    if "突破" in raw_text:
        suggestions.append({
            "pattern": "突破",
            "confidence": 0.6,
            "suggestion": {"op": "gt"},
            "requires_context": True,
        })

    if "跌破" in raw_text:
        suggestions.append({
            "pattern": "跌破",
            "confidence": 0.6,
            "suggestion": {"op": "lt"},
            "requires_context": True,
        })

    if "创新高" in raw_text:
        suggestions.append({
            "pattern": "创新高",
            "confidence": 0.7,
            "suggestion": {"op": "gt", "field": "close", "requires_context": True},
            "requires_context": True,
        })

    if "创新低" in raw_text:
        suggestions.append({
            "pattern": "创新低",
            "confidence": 0.7,
            "suggestion": {"op": "lt", "field": "close", "requires_context": True},
            "requires_context": True,
        })

    if "涨停" in raw_text:
        suggestions.append({
            "pattern": "涨停",
            "confidence": 0.8,
            "suggestion": {"op": "gte", "field": "close_pct_change", "value": 9.8},
            "requires_context": False,
        })

    if "跌停" in raw_text:
        suggestions.append({
            "pattern": "跌停",
            "confidence": 0.8,
            "suggestion": {"op": "lte", "field": "close_pct_change", "value": -9.8},
            "requires_context": False,
        })

    # ========== MACD 相关 ==========
    if "macd金叉" in raw_lower or "macd金叉" in raw_text:
        suggestions.append({
            "pattern": "MACD金叉",
            "confidence": 0.9,
            "suggestion": {"op": "cross_above", "field": "macd", "other_field": "macd_signal"},
            "requires_context": False,
        })
    elif "macd" in raw_lower and "金叉" in raw_text:
        suggestions.append({
            "pattern": "MACD金叉",
            "confidence": 0.9,
            "suggestion": {"op": "cross_above", "field": "macd", "other_field": "macd_signal"},
            "requires_context": False,
        })

    if "macd死叉" in raw_lower or "macd死叉" in raw_text:
        suggestions.append({
            "pattern": "MACD死叉",
            "confidence": 0.9,
            "suggestion": {"op": "cross_below", "field": "macd", "other_field": "macd_signal"},
            "requires_context": False,
        })
    elif "macd" in raw_lower and "死叉" in raw_text:
        suggestions.append({
            "pattern": "MACD死叉",
            "confidence": 0.9,
            "suggestion": {"op": "cross_below", "field": "macd", "other_field": "macd_signal"},
            "requires_context": False,
        })

    if "macd" in raw_lower and ("翻红" in raw_text or "转正" in raw_text or "红柱" in raw_text):
        suggestions.append({
            "pattern": "MACD柱翻红",
            "confidence": 0.85,
            "suggestion": {"op": "gt", "field": "macd_hist", "value": 0},
            "requires_context": False,
        })

    if "macd" in raw_lower and ("翻绿" in raw_text or "转负" in raw_text or "绿柱" in raw_text):
        suggestions.append({
            "pattern": "MACD柱翻绿",
            "confidence": 0.85,
            "suggestion": {"op": "lt", "field": "macd_hist", "value": 0},
            "requires_context": False,
        })

    # ========== KDJ 相关 ==========
    if "kdj" in raw_lower and "金叉" in raw_text:
        suggestions.append({
            "pattern": "KDJ金叉",
            "confidence": 0.85,
            "suggestion": {"op": "cross_above", "field": "kdj_k", "other_field": "kdj_d"},
            "requires_context": False,
        })

    if "kdj" in raw_lower and "死叉" in raw_text:
        suggestions.append({
            "pattern": "KDJ死叉",
            "confidence": 0.85,
            "suggestion": {"op": "cross_below", "field": "kdj_k", "other_field": "kdj_d"},
            "requires_context": False,
        })

    if "kdj" in raw_lower and ("超买" in raw_text or "高于80" in raw_text):
        suggestions.append({
            "pattern": "KDJ超买",
            "confidence": 0.85,
            "suggestion": {"op": "gt", "field": "kdj_k", "value": 80},
            "requires_context": False,
        })

    if "kdj" in raw_lower and ("超卖" in raw_text or "低于20" in raw_text):
        suggestions.append({
            "pattern": "KDJ超卖",
            "confidence": 0.85,
            "suggestion": {"op": "lt", "field": "kdj_k", "value": 20},
            "requires_context": False,
        })

    # ========== 均线相关 ==========
    if "金叉" in raw_text:
        suggestions.append({
            "pattern": "金叉",
            "confidence": 0.8,
            "suggestion": {"op": "cross_above"},
            "requires_context": True,
        })

    if "死叉" in raw_text:
        suggestions.append({
            "pattern": "死叉",
            "confidence": 0.8,
            "suggestion": {"op": "cross_below"},
            "requires_context": True,
        })

    # MA 均线交叉检测
    for ma_key in ["ma5", "ma10", "ma20", "ma60", "ma120", "ma250"]:
        if f"{ma_key}金叉" in raw_lower or f"{ma_key}向上突破" in raw_lower:
            suggestions.append({
                "pattern": f"{ma_key}金叉",
                "confidence": 0.85,
                "suggestion": {"op": "cross_above", "field": ma_key},
                "requires_context": True,
            })
        if f"{ma_key}死叉" in raw_lower or f"{ma_key}向下突破" in raw_lower:
            suggestions.append({
                "pattern": f"{ma_key}死叉",
                "confidence": 0.85,
                "suggestion": {"op": "cross_below", "field": ma_key},
                "requires_context": True,
            })

    # 均线多头排列
    if "多头排列" in raw_text or "ma多头" in raw_text:
        suggestions.append({
            "pattern": "MA多头排列",
            "confidence": 0.8,
            "suggestion": {"op": "and", "conditions": [
                {"op": "gt", "field": "ma5", "value_field": "ma10"},
                {"op": "gt", "field": "ma10", "value_field": "ma20"},
                {"op": "gt", "field": "ma20", "value_field": "ma60"},
            ]},
            "requires_context": False,
        })

    # 均线空头排列
    if "空头排列" in raw_text or "ma空头" in raw_text:
        suggestions.append({
            "pattern": "MA空头排列",
            "confidence": 0.8,
            "suggestion": {"op": "and", "conditions": [
                {"op": "lt", "field": "ma5", "value_field": "ma10"},
                {"op": "lt", "field": "ma10", "value_field": "ma20"},
                {"op": "lt", "field": "ma20", "value_field": "ma60"},
            ]},
            "requires_context": False,
        })

    # 均线粘连/发散
    if "均线粘连" in raw_text or "均线粘合" in raw_text or "均线收敛" in raw_text:
        suggestions.append({
            "pattern": "均线粘连",
            "confidence": 0.7,
            "suggestion": {"op": "and", "requires_context": True},
            "requires_context": True,
        })
    if "均线发散" in raw_text:
        suggestions.append({
            "pattern": "均线发散",
            "confidence": 0.7,
            "suggestion": {"op": "and", "requires_context": True},
            "requires_context": True,
        })

    # ========== RSI 相关 ==========
    if "超卖" in raw_text or "低于30" in raw_text:
        suggestions.append({
            "pattern": "超卖" if "rsi" not in raw_lower else "RSI超卖",
            "confidence": 0.9,
            "suggestion": {"op": "lt", "field": "rsi6", "value": 30},
            "requires_context": False,
        })
    if "超买" in raw_text or "高于70" in raw_text:
        suggestions.append({
            "pattern": "超买" if "rsi" not in raw_lower else "RSI超买",
            "confidence": 0.9,
            "suggestion": {"op": "gt", "field": "rsi6", "value": 70},
            "requires_context": False,
        })

    # ========== 布林带相关 ==========
    if "布林" in raw_text or "boll" in raw_lower:
        if "上轨" in raw_text or "上沿" in raw_text:
            suggestions.append({
                "pattern": "布林上轨",
                "confidence": 0.85,
                "suggestion": {"op": "gt", "field": "close", "value_field": "bollinger_upper"},
                "requires_context": False,
            })
        if "中轨" in raw_text or "中沿" in raw_text:
            suggestions.append({
                "pattern": "布林中轨",
                "confidence": 0.8,
                "suggestion": {"op": "gt", "field": "close", "value_field": "bollinger_middle"},
                "requires_context": False,
            })
        if "下轨" in raw_text or "下沿" in raw_text:
            suggestions.append({
                "pattern": "布林下轨",
                "confidence": 0.85,
                "suggestion": {"op": "lt", "field": "close", "value_field": "bollinger_lower"},
                "requires_context": False,
            })
        if "收口" in raw_text or "收缩" in raw_text or "变窄" in raw_text:
            suggestions.append({
                "pattern": "布林收口",
                "confidence": 0.7,
                "suggestion": {"op": "and", "requires_context": True},
                "requires_context": True,
            })
        if "张口" in raw_text or "扩张" in raw_text or "变宽" in raw_text:
            suggestions.append({
                "pattern": "布林张口",
                "confidence": 0.7,
                "suggestion": {"op": "and", "requires_context": True},
                "requires_context": True,
            })

    # ========== 量价关系 ==========
    if "价涨量增" in raw_text or ("量增" in raw_text and "价涨" in raw_text):
        suggestions.append({
            "pattern": "价涨量增",
            "confidence": 0.8,
            "suggestion": {"op": "and", "conditions": [
                {"op": "gt", "field": "close_pct_change", "value": 0},
                {"op": "gt", "field": "volume_ratio", "value": 1.2},
            ]},
            "requires_context": False,
        })

    if "价跌量缩" in raw_text or ("量缩" in raw_text and "价跌" in raw_text):
        suggestions.append({
            "pattern": "价跌量缩",
            "confidence": 0.8,
            "suggestion": {"op": "and", "conditions": [
                {"op": "lt", "field": "close_pct_change", "value": 0},
                {"op": "lt", "field": "volume_ratio", "value": 0.8},
            ]},
            "requires_context": False,
        })

    if "量价背离" in raw_text:
        suggestions.append({
            "pattern": "量价背离",
            "confidence": 0.6,
            "suggestion": {"op": "and", "requires_context": True},
            "requires_context": True,
        })

    # ========== 换手率 ==========
    if "高换手" in raw_text or "换手率高" in raw_text:
        suggestions.append({
            "pattern": "高换手",
            "confidence": 0.8,
            "suggestion": {"op": "gt", "field": "turnover_rate", "value": 10},
            "requires_context": False,
        })

    if "低换手" in raw_text or "换手率低" in raw_text:
        suggestions.append({
            "pattern": "低换手",
            "confidence": 0.8,
            "suggestion": {"op": "lt", "field": "turnover_rate", "value": 1},
            "requires_context": False,
        })

    return suggestions


def validate_mapped_condition(condition: dict[str, Any]) -> tuple[bool, str]:
    """验证映射后的条件是否合法

    Args:
        condition: 映射后的条件字典

    Returns:
        (是否合法, 错误信息)
    """
    if not isinstance(condition, dict):
        return False, "条件必须是字典类型"

    # 检查 op 字段
    if "op" not in condition:
        return False, "条件缺少 'op' 字段"

    op = condition["op"]
    if op not in OPERATORS:
        return False, f"不支持的操作符: {op}，支持的列表: {OPERATORS}"

    # 检查逻辑操作符 (and/or/not)
    if op in ["and", "or"]:
        if "conditions" not in condition:
            return False, f"逻辑操作符 '{op}' 需要 'conditions' 字段"
        if not isinstance(condition["conditions"], list):
            return False, f"'conditions' 必须是列表类型"
        if len(condition["conditions"]) < 2:
            return False, f"逻辑操作符 '{op}' 至少需要2个子条件"
        # 递归验证子条件
        for i, sub_cond in enumerate(condition["conditions"]):
            valid, msg = validate_mapped_condition(sub_cond)
            if not valid:
                return False, f"子条件[{i}]验证失败: {msg}"
        return True, ""

    # 检查 not 操作符
    if op == "not":
        if "condition" not in condition:
            return False, "'not' 操作符需要 'condition' 字段"
        return validate_mapped_condition(condition["condition"])

    # 检查比较操作符 (gt, lt, eq, gte, lte, in, not_in, cross_above, cross_below, cmp)
    if op in ["gt", "lt", "eq", "gte", "lte", "cmp"]:
        if "field" not in condition:
            return False, f"比较操作符 '{op}' 需要 'field' 字段"
        field = condition["field"]
        if field not in STANDARD_FIELDS:
            # 允许动态字段，但给出警告
            pass
        if "value" not in condition:
            return False, f"比较操作符 '{op}' 需要 'value' 字段"
        return True, ""

    # 检查 in / not_in 操作符
    if op in ["in", "not_in"]:
        if "field" not in condition:
            return False, f"'{op}' 操作符需要 'field' 字段"
        if "values" not in condition:
            return False, f"'{op}' 操作符需要 'values' 字段 (列表)"
        if not isinstance(condition["values"], list):
            return False, f"'values' 必须是列表类型"
        return True, ""

    return True, ""


def build_and_condition(*conditions: dict[str, Any]) -> dict[str, Any]:
    """构建 AND 条件

    Args:
        *conditions: 多个条件字典

    Returns:
        AND 条件字典
    """
    filtered = [c for c in conditions if c]  # 过滤 None 和空条件
    if len(filtered) == 0:
        return {}
    if len(filtered) == 1:
        return filtered[0]
    return {
        "op": "and",
        "conditions": list(filtered),
    }


def build_or_condition(*conditions: dict[str, Any]) -> dict[str, Any]:
    """构建 OR 条件

    Args:
        *conditions: 多个条件字典

    Returns:
        OR 条件字典
    """
    filtered = [c for c in conditions if c]  # 过滤 None 和空条件
    if len(filtered) == 0:
        return {}
    if len(filtered) == 1:
        return filtered[0]
    return {
        "op": "or",
        "conditions": list(filtered),
    }


def build_cmp_condition(field: str, cmp_op: str, value: Any) -> dict[str, Any]:
    """构建比较条件

    Args:
        field: 字段名
        cmp_op: 比较操作符 (gt, lt, eq, gte, lte)
        value: 比较值

    Returns:
        比较条件字典
    """
    if cmp_op not in OPERATORS:
        raise ValueError(f"不支持的操作符: {cmp_op}，支持的列表: {OPERATORS}")
    return {
        "op": cmp_op,
        "field": field,
        "value": value,
    }


def build_cross_condition(field: str, cross_op: str, other_field: str | None = None) -> dict[str, Any]:
    """构建交叉条件（金叉/死叉）

    Args:
        field: 主字段
        cross_op: 交叉操作符 (cross_above, cross_below)
        other_field: 交叉的另一个字段，None 时自动推断

    Returns:
        交叉条件字典
    """
    if cross_op not in ["cross_above", "cross_below"]:
        raise ValueError(f"不支持的交叉操作符: {cross_op}")

    result = {"op": cross_op, "field": field}
    if other_field:
        result["other_field"] = other_field
    return result


def build_in_condition(field: str, values: list[Any], not_in: bool = False) -> dict[str, Any]:
    """构建 IN / NOT_IN 条件

    Args:
        field: 字段名
        values: 值列表
        not_in: True 时为 NOT_IN，False 时为 IN

    Returns:
        IN/NOT_IN 条件字典
    """
    return {
        "op": "not_in" if not_in else "in",
        "field": field,
        "values": list(values),
    }


def build_not_condition(condition: dict[str, Any]) -> dict[str, Any]:
    """构建 NOT 条件

    Args:
        condition: 要取反的条件

    Returns:
        NOT 条件字典
    """
    return {
        "op": "not",
        "condition": condition,
    }