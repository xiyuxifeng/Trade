"""S7-003: 候选版本构建器单元测试"""

import pytest
from datetime import date

from src.optimization.candidate_builder import (
    build_candidate_version,
    CandidateBuildInput,
    CandidateBuildResult,
)
from src.optimization.strategy_advisor import RuleAdjustment
from src.strategy_library.schemas import (
    StrategyVersionStatus,
    StrategyVersionType,
)


def make_rule(rule_id: str, condition: str = "price > 10", action: dict | None = None) -> dict:
    """生成测试用 rules_snapshot 条目。"""
    return {
        "rule_id": rule_id,
        "condition": condition,
        "action": action or {"type": "buy"},
        "confidence": 0.8,
    }


def make_adj(
    rule_id: str,
    current_status: str,
    suggestion: str = "测试建议",
    confidence: float = 0.8,
) -> RuleAdjustment:
    """生成测试用 RuleAdjustment。"""
    return RuleAdjustment(
        trader_id="T1",
        rule_id=rule_id,
        rule_text=f"规则 {rule_id}",
        current_status=current_status,
        suggestion=suggestion,
        confidence=confidence,
        hit_rate=0.05,
        posterior_return_mean=-0.02,
        posterior_return_median=None,
    )


class TestCandidateBuilder:
    def test_delete_rule(self):
        """hit_rate_too_low_and_return_negative → 从 rules_snapshot 删除该 rule_id"""
        parent_rules = [
            make_rule("R1"),
            make_rule("R2"),
            make_rule("R3"),
        ]
        adj = make_adj("R2", "hit_rate_too_low_and_return_negative")
        input_obj = CandidateBuildInput(
            trader_id="T1",
            strategy_date=date(2026, 4, 28),
            parent_version_id="T1_2026-04-28_released",
            parent_rules_snapshot=parent_rules,
            adjustments=[adj],
        )

        result = build_candidate_version(input_obj)

        # R2 应被删除
        assert len(result.version.rules_snapshot) == 2
        rule_ids = [r["rule_id"] for r in result.version.rules_snapshot]
        assert "R1" in rule_ids
        assert "R3" in rule_ids
        assert "R2" not in rule_ids
        assert result.deleted_rules == ["R2"]

    def test_review_stop_loss(self):
        """high_hit_rate_but_negative_return → 标记 _review_required=True"""
        parent_rules = [make_rule("R1", action={"type": "buy", "stop_loss": 0.05})]
        adj = make_adj("R1", "high_hit_rate_but_negative_return")
        input_obj = CandidateBuildInput(
            trader_id="T1",
            strategy_date=date(2026, 4, 28),
            parent_version_id="T1_2026-04-28_released",
            parent_rules_snapshot=parent_rules,
            adjustments=[adj],
        )

        result = build_candidate_version(input_obj)

        assert len(result.version.rules_snapshot) == 1
        rule = result.version.rules_snapshot[0]
        assert rule["action"].get("_review_required") is True
        assert rule["action"].get("_review_reason") == adj.suggestion
        assert result.modified_rules == ["R1"]

    def test_upgrade_rule(self):
        """missed_opportunity → 标记 programmable=True"""
        parent_rules = [make_rule("R1")]
        adj = make_adj("R1", "missed_opportunity")
        input_obj = CandidateBuildInput(
            trader_id="T1",
            strategy_date=date(2026, 4, 28),
            parent_version_id="T1_2026-04-28_released",
            parent_rules_snapshot=parent_rules,
            adjustments=[adj],
        )

        result = build_candidate_version(input_obj)

        rule = result.version.rules_snapshot[0]
        assert rule.get("programmable") is True
        assert rule.get("_upgrade_note") == adj.suggestion
        assert result.modified_rules == ["R1"]

    def test_missing_snapshot(self):
        """missing_snapshot → 保留原规则，附加 note"""
        parent_rules = [make_rule("R1")]
        adj = make_adj("R1", "missing_snapshot")
        input_obj = CandidateBuildInput(
            trader_id="T1",
            strategy_date=date(2026, 4, 28),
            parent_version_id="T1_2026-04-28_released",
            parent_rules_snapshot=parent_rules,
            adjustments=[adj],
        )

        result = build_candidate_version(input_obj)

        rule = result.version.rules_snapshot[0]
        assert rule["rule_id"] == "R1"
        notes = rule.get("_notes", [])
        assert any("check_snapshot" in n for n in notes)
        assert result.kept_rules == ["R1"]

    def test_programmable_but_rarely_hit_becomes_delete(self):
        """programmable_but_rarely_hit → 映射为 delete_rule（已删除）"""
        parent_rules = [make_rule("R1"), make_rule("R2")]
        adj = make_adj("R1", "programmable_but_rarely_hit")
        input_obj = CandidateBuildInput(
            trader_id="T1",
            strategy_date=date(2026, 4, 28),
            parent_version_id="T1_2026-04-28_released",
            parent_rules_snapshot=parent_rules,
            adjustments=[adj],
        )

        result = build_candidate_version(input_obj)

        rule_ids = [r["rule_id"] for r in result.version.rules_snapshot]
        assert "R1" not in rule_ids
        assert "R2" in rule_ids
        assert result.deleted_rules == ["R1"]

    def test_unmatched_rule_kept(self):
        """无对应 adjustment 的规则应保留"""
        parent_rules = [make_rule("R1"), make_rule("R2"), make_rule("R3")]
        adj = make_adj("R1", "hit_rate_too_low_and_return_negative")
        input_obj = CandidateBuildInput(
            trader_id="T1",
            strategy_date=date(2026, 4, 28),
            parent_version_id="T1_2026-04-28_released",
            parent_rules_snapshot=parent_rules,
            adjustments=[adj],
        )

        result = build_candidate_version(input_obj)

        assert len(result.version.rules_snapshot) == 2
        assert set(result.kept_rules) == {"R2", "R3"}

    def test_candidate_version_fields(self):
        """候选版本字段正确"""
        parent_rules = [make_rule("R1")]
        adj = make_adj("R1", "missed_opportunity")
        input_obj = CandidateBuildInput(
            trader_id="T1",
            strategy_date=date(2026, 4, 28),
            parent_version_id="T1_2026-04-28_released_abc12345",
            parent_rules_snapshot=parent_rules,
            adjustments=[adj],
        )

        result = build_candidate_version(input_obj)

        assert result.version.status == StrategyVersionStatus.draft
        assert result.version.version_type == StrategyVersionType.candidate
        assert result.version.parent_version_id == "T1_2026-04-28_released_abc12345"
        assert "candidate" in result.version.version_id
        assert "T1" in result.version.version_id
        assert result.version.notes is not None
        assert "missed_opportunity" in result.version.notes

    def test_multiple_adjustments(self):
        """多条调整建议同时生效"""
        parent_rules = [
            make_rule("R1"),
            make_rule("R2"),
            make_rule("R3"),
            make_rule("R4"),
        ]
        adjustments = [
            make_adj("R1", "hit_rate_too_low_and_return_negative"),
            make_adj("R2", "missed_opportunity"),
            make_adj("R3", "high_hit_rate_but_negative_return"),
        ]
        input_obj = CandidateBuildInput(
            trader_id="T1",
            strategy_date=date(2026, 4, 28),
            parent_version_id="T1_2026-04-28_released",
            parent_rules_snapshot=parent_rules,
            adjustments=adjustments,
        )

        result = build_candidate_version(input_obj)

        rule_ids = [r["rule_id"] for r in result.version.rules_snapshot]
        assert "R1" not in rule_ids  # 删除
        assert "R2" in rule_ids       # 升级
        assert "R3" in rule_ids       # 复核
        assert "R4" in rule_ids       # 保留
        assert set(result.deleted_rules) == {"R1"}
        assert set(result.modified_rules) == {"R2", "R3"}
        assert result.kept_rules == ["R4"]
