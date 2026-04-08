"""
Lark DSL Parser — P4-015。

使用 Lark parser generator 实现 DSL 解析器。

语法（类函数调用风格）：
  - cmp(field, op, value) - 比较表达式
  - AND(expr, expr, ...) - 逻辑与
  - OR(expr, expr, ...) - 逻辑或
  - NOT(expr) - 逻辑非
  - TRUE / FALSE - 常量

示例：
  - cmp(regime, eq, trend_up)
  - AND(cmp(regime, eq, trend_up), cmp(volatility, in, [low, mid]))
  - NOT(cmp(regime, eq, bearish))
"""

from __future__ import annotations

from typing import Any

from lark import Lark, Transformer, Token, Tree

from src.persona.dsl import ConditionExpr


# ---------------------------------------------------------------------------
# Lark Grammar
# ---------------------------------------------------------------------------

DSL_GRAMMAR = r"""
    // 主表达式
    expr: and_expr
        | or_expr
        | not_expr
        | cmp_expr
        | TRUE
        | FALSE

    // 逻辑运算符（函数调用风格）
    and_expr: AND LPAREN expr (COMMA expr)* RPAREN
    or_expr: OR LPAREN expr (COMMA expr)* RPAREN
    not_expr: NOT LPAREN expr RPAREN

    // 比较表达式
    cmp_expr: CMP LPAREN cmp_args RPAREN

    cmp_args: field COMMA cmp_op COMMA value

    field: FIELD

    cmp_op: CMP_OP

    value: NUMBER
          | STRING
          | BOOLEAN
          | array
          | FIELD

    array: LBRACKET [value (COMMA value)*] RBRACKET

    // 终结符
    AND: "AND"
    OR: "OR"
    NOT: "NOT"
    CMP: "cmp"
    CMP_OP: "eq" | "ne" | "gt" | "ge" | "lt" | "le" | "in" | "not_in"
    TRUE: "TRUE"
    FALSE: "FALSE"
    LPAREN: "("
    RPAREN: ")"
    LBRACKET: "["
    RBRACKET: "]"
    COMMA: ","
    BOOLEAN: "true" | "false"
    FIELD: /[a-zA-Z_][a-zA-Z0-9_.]*/
    NUMBER: /-?\d+(\.\d+)?/
    STRING: /"[^"]*"|'[^']*'/

    %import common.WS
    %ignore WS
"""


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class DSLParser:
    """DSL 解析器 - 使用 Lark。

    将 DSL 字符串解析为 ConditionExpr。

    用法：
        parser = DSLParser()
        expr = parser.parse("AND(cmp(regime, eq, trend_up), cmp(volatility, in, [low, mid]))")
    """

    def __init__(self) -> None:
        self._parser = Lark(DSL_GRAMMAR, start="expr", parser="lalr")

    def parse(self, text: str) -> ConditionExpr:
        """解析 DSL 字符串为 ConditionExpr。

        Args:
            text: DSL 表达式字符串

        Returns:
            ConditionExpr 对象

        Raises:
            ValueError: 解析失败
        """
        try:
            tree = self._parser.parse(text)
            return _TreeToExpr().transform(tree)
        except Exception as e:
            raise ValueError(f"Failed to parse DSL: {text!r}") from e

    def parse_many(self, texts: list[str]) -> list[ConditionExpr]:
        """批量解析 DSL 字符串。

        Args:
            texts: DSL 表达式字符串列表

        Returns:
            ConditionExpr 对象列表
        """
        return [self.parse(text) for text in texts]


# ---------------------------------------------------------------------------
# Tree to AST Transformer
# ---------------------------------------------------------------------------

class _TreeToExpr(Transformer):
    """将 Lark AST 转换为 ConditionExpr。"""

    def expr(self, children: list) -> ConditionExpr:
        """处理 expr 规则 - 直接返回子节点中的 ConditionExpr。"""
        for c in children:
            if isinstance(c, ConditionExpr):
                return c
        # 如果没有 ConditionExpr 子节点，返回 true
        return ConditionExpr(op="true")

    def and_expr(self, children: list) -> ConditionExpr:
        args = [c for c in children if isinstance(c, ConditionExpr)]
        return ConditionExpr(op="and", args=args)

    def or_expr(self, children: list) -> ConditionExpr:
        args = [c for c in children if isinstance(c, ConditionExpr)]
        return ConditionExpr(op="or", args=args)

    def not_expr(self, children: list) -> ConditionExpr:
        for c in children:
            if isinstance(c, ConditionExpr):
                return ConditionExpr(op="not", args=[c])
        return ConditionExpr(op="not", args=[])

    def cmp_expr(self, children: list) -> ConditionExpr:
        """处理 cmp_expr 表达式。

        children 经过 Transformer 深度优先处理后：
        - Token 保持为 Token
        - cmp_args.children 中的 field/cmp_op/value 已被各自的方法转换

        children 格式: [CMP_token, LPAREN_token, cmp_args_tree, RPAREN_token]
        cmp_args.children 格式: [field_tree, COMMA_token, cmp_op_tree, COMMA_token, value_tree]
        """
        cmp_args_tree = None
        for c in children:
            if isinstance(c, Tree) and c.data == "cmp_args":
                cmp_args_tree = c
                break

        if cmp_args_tree is None:
            return ConditionExpr(op="cmp", field=None, cmp=None, value=None)

        return self._build_cmp_expr(cmp_args_tree)

    def _build_cmp_expr(self, cmp_args_tree: Tree) -> ConditionExpr:
        """从 cmp_args Tree 中提取 field, cmp_op, value。

        注意：cmp_args.children 中的 Tree 节点已经被各自的 Transformer 方法处理过，
        即 field 方法返回字符串 "regime"，而不是 Tree("field", [Token(...)])

        所以这里不能按 Tree.data 来判断，而是按 children 索引来处理。
        """
        # cmp_args.children: [field_result, COMMA, cmp_op_result, COMMA, value_result]
        # field_result 可能是字符串或 Tree（如果 field 方法返回的不是叶子值）
        # cmp_op_result 是字符串
        # value_result 是字符串、数字、布尔或列表
        children = cmp_args_tree.children

        field_val = None
        cmp_val = None
        value_val = None

        # 遍历 children，跳过 COMMA token
        non_comma_children = [c for c in children if not (isinstance(c, Token) and c.type == "COMMA")]

        # non_comma_children 应该包含 [field_result, cmp_op_result, value_result]
        if len(non_comma_children) >= 1:
            field_val = non_comma_children[0]
        if len(non_comma_children) >= 2:
            cmp_val = non_comma_children[1]
        if len(non_comma_children) >= 3:
            value_val = non_comma_children[2]

        return ConditionExpr(
            op="cmp",
            field=field_val,
            cmp=cmp_val,
            value=value_val,
        )

    def value(self, children: list) -> Any:
        """处理 value 规则。"""
        if not children:
            return None
        child = children[0]
        if isinstance(child, Token):
            if child.type == "NUMBER":
                try:
                    return int(child.value)
                except ValueError:
                    return float(child.value)
            elif child.type == "STRING":
                return child.value.strip('"').strip("'")
            elif child.type == "BOOLEAN":
                return child.value == "true"
            elif child.type == "FIELD":
                # 处理 FIELD 类型的值，包括 "true"/"false" 字符串
                if child.value == "true":
                    return True
                elif child.value == "false":
                    return False
                return child.value
        return child

    def field(self, children: list) -> str:
        """处理 field 规则 - 返回字段名。"""
        if not children:
            return None
        child = children[0]
        if isinstance(child, Token) and child.type == "FIELD":
            return child.value
        return child

    def cmp_op(self, children: list) -> str:
        """处理 cmp_op 规则 - 返回比较操作符。"""
        if not children:
            return None
        child = children[0]
        if isinstance(child, Token) and child.type == "CMP_OP":
            return child.value
        return child

    def array(self, children: list) -> list:
        return [c for c in children if c is not None and not isinstance(c, Token)]

    def TRUE(self, _children: list) -> ConditionExpr:
        return ConditionExpr(op="true")

    def FALSE(self, _children: list) -> ConditionExpr:
        return ConditionExpr(op="false")


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------

_parser_instance: DSLParser | None = None


def get_parser() -> DSLParser:
    """获取全局 Parser 实例（单例）。"""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = DSLParser()
    return _parser_instance


def parse_dsl(text: str) -> ConditionExpr:
    """快捷函数：解析 DSL 字符串。

    Args:
        text: DSL 表达式字符串

    Returns:
        ConditionExpr 对象
    """
    return get_parser().parse(text)


def parse_dsl_many(texts: list[str]) -> list[ConditionExpr]:
    """快捷函数：批量解析 DSL 字符串。

    Args:
        texts: DSL 表达式字符串列表

    Returns:
        ConditionExpr 对象列表
    """
    return get_parser().parse_many(texts)
