"""评估规则 Skill - 调用 RuleEvaluator"""
from typing import Any

from src.persona.dsl import ActionSpec, ConditionExpr
from src.persona.dsl_compiler import CompiledRule, compile_rule, filter_matching
from src.strategy.types import RuleMatch


def _dict_to_condition_expr(condition: dict[str, Any] | str) -> ConditionExpr:
    """将字典条件转换为 ConditionExpr"""
    if isinstance(condition, dict):
        return ConditionExpr(**condition)
    # 如果是字符串，简单解析 "field < value" 格式
    # 格式: "rsi < 40" 或 "rsi<=40" 等
    import re
    match = re.match(r'(\w+)\s*([<>]=?)\s*(.+)', str(condition))
    if match:
        field, cmp_op, value = match.groups()
        cmp_map = {'<': 'lt', '<=': 'le', '>': 'gt', '>=': 'ge', '==': 'eq', '!=': 'ne'}
        return ConditionExpr(
            op='cmp',
            field=field,
            cmp=cmp_map.get(cmp_op, 'eq'),
            value=float(value.strip()) if '.' in value else int(value.strip())
        )
    # 恒真条件
    return ConditionExpr(op='true')


def _compile_dict_rule(rule_dict: dict[str, Any]) -> CompiledRule:
    """将字典规则编译为 CompiledRule"""
    condition = rule_dict.get('condition', {})
    condition_expr = _dict_to_condition_expr(condition)

    action_dict = rule_dict.get('action', {})
    action = ActionSpec(
        type=action_dict.get('type', 'filter'),
        side=action_dict.get('side'),
        order=action_dict.get('order'),
        price=action_dict.get('price'),
        params=action_dict.get('params', {})
    )

    # 使用 compile_rule 编译条件
    compiled = compile_rule(
        condition_expr,
        rule_id=rule_dict.get('rule_id', 'unknown'),
        name=rule_dict.get('rule_name', rule_dict.get('rule_id', 'unknown'))
    )

    # 更新 action 和 confidence
    compiled.action = action
    if 'confidence' in rule_dict:
        compiled.confidence = rule_dict['confidence']

    return compiled


async def evaluate_rules(
    features: dict[str, float],
    rules: list[dict[str, Any]]
) -> list[RuleMatch]:
    """
    评估规则

    Args:
        features: 特征字典
        rules: 规则列表

    Returns:
        匹配的规则列表 (RuleMatch)
    """
    try:
        # 编译字典规则为 CompiledRule
        compiled_rules = [_compile_dict_rule(r) for r in rules]

        # 使用 filter_matching 评估规则
        matched_rules = filter_matching(
            compiled_rules,
            state={},
            bar=features
        )

        # 转换为 RuleMatch
        return [
            RuleMatch(
                rule_id=rule.rule_id,
                rule_type=rule.rule_type,
                matched=True,
                confidence=rule.confidence if rule.confidence is not None else 0.5,
                action=rule.action
            )
            for rule in matched_rules
        ]
    except Exception as e:
        # 降级：返回空列表
        return []