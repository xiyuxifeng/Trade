"""
DSL Executor 单元测试 — P4-017。
"""

from __future__ import annotations

from src.persona.dsl import CMP
from src.persona.dsl_compiler import compile_rule
from src.persona.dsl_executor import (
    DSLExecutor,
    ExecutionHooks,
    ExecutionMode,
    ExecutionSummary,
    RuleEvent,
    RuleRegistry,
    RuleState,
    create_executor,
)


class TestRuleRegistry:
    """RuleRegistry 测试。"""

    def test_register_and_get(self):
        registry = RuleRegistry()
        rule = compile_rule(CMP("regime", "eq", "bullish"), rule_id="r1")

        registry.register(rule, priority=1)
        assert registry.get("r1") == rule

    def test_priority_order(self):
        registry = RuleRegistry()
        r1 = compile_rule(CMP("x", "eq", 1), rule_id="r1")
        r2 = compile_rule(CMP("x", "eq", 2), rule_id="r2")
        r3 = compile_rule(CMP("x", "eq", 3), rule_id="r3")

        registry.register(r3, priority=1)
        registry.register(r1, priority=3)
        registry.register(r2, priority=2)

        all_rules = registry.get_all()
        assert [r.rule_id for r in all_rules] == ["r1", "r2", "r3"]

    def test_enable_disable(self):
        registry = RuleRegistry()
        rule = compile_rule(CMP("x", "eq", 1), rule_id="r1")
        registry.register(rule, enabled=False)

        assert registry.get_enabled() == []
        registry.enable("r1")
        assert len(registry.get_enabled()) == 1
        registry.disable("r1")
        assert registry.get_enabled() == []

    def test_suspend(self):
        registry = RuleRegistry()
        rule = compile_rule(CMP("x", "eq", 1), rule_id="r1")
        registry.register(rule)

        registry.suspend("r1")
        assert registry.get_state("r1") == RuleState.SUSPENDED
        assert registry.get_enabled() == []

    def test_unregister(self):
        registry = RuleRegistry()
        rule = compile_rule(CMP("x", "eq", 1), rule_id="r1")
        registry.register(rule)

        registry.unregister("r1")
        assert registry.get("r1") is None


class TestDSLExecutor:
    """DSLExecutor 测试。"""

    def test_execute_all_rules(self):
        registry = RuleRegistry()
        executor = DSLExecutor(registry)

        r1 = compile_rule(CMP("regime", "eq", "bullish"), rule_id="r1")
        r2 = compile_rule(CMP("close", "gt", 100), rule_id="r2")
        registry.register(r1)
        registry.register(r2)

        summary = executor.execute(
            state={"regime": "bullish"},
            bar={"close": 105},
        )

        assert summary.total == 2
        assert summary.matched == 2
        assert summary.failed == 0

    def test_execute_with_no_match(self):
        registry = RuleRegistry()
        executor = DSLExecutor(registry)

        rule = compile_rule(CMP("regime", "eq", "bullish"), rule_id="r1")
        registry.register(rule)

        summary = executor.execute(state={"regime": "bearish"}, bar={})

        assert summary.total == 1
        assert summary.matched == 0
        assert summary.failed == 1

    def test_execute_first_short_circuit(self):
        registry = RuleRegistry()
        executor = DSLExecutor(registry)

        r1 = compile_rule(CMP("x", "eq", 1), rule_id="r1")
        r2 = compile_rule(CMP("x", "eq", 2), rule_id="r2")
        r3 = compile_rule(CMP("x", "eq", 3), rule_id="r3")
        registry.register(r1, priority=3)
        registry.register(r2, priority=2)
        registry.register(r3, priority=1)

        # r1 应该先执行（最高优先级）且匹配
        event = executor.execute_first(
            state={},
            bar={"x": 1},
        )

        assert event is not None
        assert event.rule.rule_id == "r1"
        assert event.matched is True

    def test_execute_first_no_match(self):
        registry = RuleRegistry()
        executor = DSLExecutor(registry)

        r1 = compile_rule(CMP("x", "eq", 1), rule_id="r1")
        r2 = compile_rule(CMP("x", "eq", 2), rule_id="r2")
        registry.register(r1)
        registry.register(r2)

        event = executor.execute_first(state={}, bar={"x": 99})

        assert event is None

    def test_filter_matching(self):
        registry = RuleRegistry()
        executor = DSLExecutor(registry)

        r1 = compile_rule(CMP("regime", "eq", "bullish"), rule_id="r1")
        r2 = compile_rule(CMP("close", "gt", 100), rule_id="r2")
        registry.register(r1)
        registry.register(r2)

        matched = executor.filter_matching(
            state={"regime": "bullish"},
            bar={"close": 50},
        )

        assert len(matched) == 1
        assert matched[0].rule_id == "r1"

    def test_filter_matching_by_type(self):
        registry = RuleRegistry()
        executor = DSLExecutor(registry)

        r1 = compile_rule(CMP("regime", "eq", "bullish"), rule_id="r1")
        registry.register(r1)

        matched = executor.filter_matching(
            state={"regime": "bullish"},
            bar={},
            rule_type="entry",  # r1 is "filter" type
        )

        assert len(matched) == 0

    def test_execute_rule_ids_filter(self):
        registry = RuleRegistry()
        executor = DSLExecutor(registry)

        r1 = compile_rule(CMP("x", "eq", 1), rule_id="r1")
        r2 = compile_rule(CMP("x", "eq", 2), rule_id="r2")
        registry.register(r1)
        registry.register(r2)

        summary = executor.execute(
            state={},
            bar={"x": 1},
            rule_ids=["r1"],  # 只执行 r1
        )

        assert summary.total == 1
        assert summary.matched == 1

    def test_execute_rule_directly(self):
        registry = RuleRegistry()
        executor = DSLExecutor(registry)

        rule = compile_rule(CMP("x", "eq", 1), rule_id="r1")
        registry.register(rule)

        event = executor.execute_rule("r1", state={}, bar={"x": 1})

        assert event.matched is True
        event = executor.execute_rule("r1", state={}, bar={"x": 2})
        assert event.matched is False


class TestExecutionHooks:
    """执行回调钩子测试。"""

    def test_on_match_hook(self):
        registry = RuleRegistry()
        matched_rules = []

        def on_match(rule, accessor):
            matched_rules.append(rule.rule_id)

        hooks = ExecutionHooks(on_match=on_match)
        executor = DSLExecutor(registry, hooks=hooks)

        rule = compile_rule(CMP("x", "eq", 1), rule_id="r1")
        registry.register(rule)

        executor.execute(state={}, bar={"x": 1})

        assert "r1" in matched_rules

    def test_on_no_match_hook(self):
        registry = RuleRegistry()
        no_match_rules = []

        def on_no_match(rule, accessor):
            no_match_rules.append(rule.rule_id)

        hooks = ExecutionHooks(on_no_match=on_no_match)
        executor = DSLExecutor(registry, hooks=hooks)

        rule = compile_rule(CMP("x", "eq", 1), rule_id="r1")
        registry.register(rule)

        executor.execute(state={}, bar={"x": 99})

        assert "r1" in no_match_rules

    def test_on_error_hook(self):
        registry = RuleRegistry()
        errors = []

        def on_error(rule, accessor, exc):
            errors.append(exc)

        hooks = ExecutionHooks(on_error=on_error)
        executor = DSLExecutor(registry, hooks=hooks)

        # 创建一个执行时会出错的规则（通过修改 condition_fn）
        rule = compile_rule(CMP("x", "eq", 1), rule_id="r1")
        rule.condition_fn = lambda acc: 1 / 0  # 故意出错
        registry.register(rule)

        summary = executor.execute(state={}, bar={"x": 1})

        # 应该捕获错误，不抛出异常
        assert len(errors) == 1
        # 规则应该被视为未匹配
        assert summary.matched == 0

    def test_on_execution_start_end_hooks(self):
        registry = RuleRegistry()
        calls = []

        def on_start(rules, state, bar):
            calls.append(("start", len(rules)))

        def on_end(summary):
            calls.append(("end", summary.total))

        hooks = ExecutionHooks(
            on_execution_start=on_start,
            on_execution_end=on_end,
        )
        executor = DSLExecutor(registry, hooks=hooks)

        rule = compile_rule(CMP("x", "eq", 1), rule_id="r1")
        registry.register(rule)

        executor.execute(state={}, bar={"x": 1})

        assert calls == [("start", 1), ("end", 1)]


class TestCreateExecutor:
    """快捷函数测试。"""

    def test_create_executor(self):
        rules = [
            compile_rule(CMP("x", "eq", 1), rule_id="r1"),
            compile_rule(CMP("x", "eq", 2), rule_id="r2"),
        ]

        executor, registry = create_executor(rules)

        assert len(registry.get_all()) == 2
        summary = executor.execute(state={}, bar={"x": 1})
        assert summary.total == 2


class TestMetrics:
    """指标测试。"""

    def test_get_metrics(self):
        registry = RuleRegistry()
        executor = DSLExecutor(registry)

        r1 = compile_rule(CMP("x", "eq", 1), rule_id="r1")
        r2 = compile_rule(CMP("x", "eq", 2), rule_id="r2")
        registry.register(r1)
        registry.register(r2, enabled=False)

        metrics = executor.get_metrics()

        assert metrics["total_rules"] == 2
        assert metrics["enabled_rules"] == 1
        assert metrics["disabled_rules"] == 1
