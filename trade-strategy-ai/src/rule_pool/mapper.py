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
    # 量能相关
    ("放量", "volume_ratio_above"): {"op": "gt", "field": "volume_ratio", "value": 1.5},
    ("缩量", "volume_ratio_below"): {"op": "lt", "field": "volume_ratio", "value": 0.7},
    ("巨量", "volume_ratio_above"): {"op": "gt", "field": "volume_ratio", "value": 3.0},
    # 价格相关
    ("突破", "close_above"): None,  # 需要更多上下文
    ("跌破", "close_below"): None,
    # 指标相关
    ("金叉", "cross_above"): None,
    ("死叉", "cross_below"): None,
    ("超卖", "rsi_below"): {"op": "lt", "field": "rsi6", "value": 30},
    ("超买", "rsi_above"): {"op": "gt", "field": "rsi6", "value": 70},
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

    # 放量相关
    if "放量" in raw_text:
        suggestions.append({
            "pattern": "放量",
            "confidence": 0.9,
            "suggestion": {"op": "gt", "field": "volume_ratio", "value": 1.5},
            "requires_context": False,
        })

    # 缩量相关
    if "缩量" in raw_text:
        suggestions.append({
            "pattern": "缩量",
            "confidence": 0.9,
            "suggestion": {"op": "lt", "field": "volume_ratio", "value": 0.7},
            "requires_context": False,
        })

    # 巨量相关
    if "巨量" in raw_text:
        suggestions.append({
            "pattern": "巨量",
            "confidence": 0.85,
            "suggestion": {"op": "gt", "field": "volume_ratio", "value": 3.0},
            "requires_context": False,
        })

    # 金叉相关
    if "金叉" in raw_text:
        suggestions.append({
            "pattern": "金叉",
            "confidence": 0.8,
            "suggestion": {"op": "cross_above"},
            "requires_context": True,
        })

    # 死叉相关
    if "死叉" in raw_text:
        suggestions.append({
            "pattern": "死叉",
            "confidence": 0.8,
            "suggestion": {"op": "cross_below"},
            "requires_context": True,
        })

    # 超卖相关
    if "超卖" in raw_text:
        suggestions.append({
            "pattern": "超卖",
            "confidence": 0.9,
            "suggestion": {"op": "lt", "field": "rsi6", "value": 30},
            "requires_context": False,
        })

    # 超买相关
    if "超买" in raw_text:
        suggestions.append({
            "pattern": "超买",
            "confidence": 0.9,
            "suggestion": {"op": "gt", "field": "rsi6", "value": 70},
            "requires_context": False,
        })

    # 突破相关
    if "突破" in raw_text:
        suggestions.append({
            "pattern": "突破",
            "confidence": 0.6,
            "suggestion": {"op": "gt"},
            "requires_context": True,
        })

    # 跌破相关
    if "跌破" in raw_text:
        suggestions.append({
            "pattern": "跌破",
            "confidence": 0.6,
            "suggestion": {"op": "lt"},
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

    # RSI 相关
    if "rsi" in raw_lower:
        if "超卖" in raw_text or "低于30" in raw_text:
            suggestions.append({
                "pattern": "RSI超卖",
                "confidence": 0.9,
                "suggestion": {"op": "lt", "field": "rsi6", "value": 30},
                "requires_context": False,
            })
        if "超买" in raw_text or "高于70" in raw_text:
            suggestions.append({
                "pattern": "RSI超买",
                "confidence": 0.9,
                "suggestion": {"op": "gt", "field": "rsi6", "value": 70},
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