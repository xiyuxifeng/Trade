"""
参数存储单元测试 — P4-018~P4-021。
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.persona.param_store import (
    ParameterError,
    ParameterNotFoundError,
    ParameterStore,
    ParameterValidationError,
)
from src.persona.param_types import ParamType, ValidationResult


class TestParameterDef:
    """ParameterDef 数据类测试。"""

    def test_to_dict_from_dict(self):
        from src.persona.param_store import ParameterDef
        from datetime import datetime

        param = ParameterDef(
            key="test.param",
            value=0.5,
            param_type=ParamType.FLOAT,
            default=0.1,
            min_val=0.0,
            max_val=1.0,
        )

        d = param.to_dict()
        restored = ParameterDef.from_dict(d)

        assert restored.key == param.key
        assert restored.value == param.value
        assert restored.param_type == param.param_type


class TestParameterStore:
    """ParameterStore 核心功能测试。"""

    def test_register_and_get(self):
        store = ParameterStore()
        store.register(
            "risk.max_position_pct",
            default=0.1,
            param_type=ParamType.FLOAT,
            min_val=0.0,
            max_val=1.0,
            description="单股最大持仓比例"
        )

        assert store.get("risk.max_position_pct") == 0.1

    def test_register_with_initial_value(self):
        store = ParameterStore()
        store.register(
            "test.int_param",
            default=10,
            param_type=ParamType.INT,
            value=20
        )

        assert store.get("test.int_param") == 20

    def test_register_validation_failure(self):
        store = ParameterStore()
        with pytest.raises(ParameterValidationError):
            store.register(
                "test.float",
                default=0.1,
                param_type=ParamType.FLOAT,
                min_val=0.0,
                max_val=1.0,
                value=2.0  # 超出范围
            )

    def test_get_not_found(self):
        store = ParameterStore()
        with pytest.raises(ParameterNotFoundError):
            store.get("nonexistent.param")

    def test_get_with_default(self):
        store = ParameterStore()
        assert store.get("nonexistent.param", default=42) == 42

    def test_set(self):
        store = ParameterStore()
        store.register("test.value", default=10, param_type=ParamType.INT)

        snapshot = store.set("test.value", 20, reason="测试更新")

        assert store.get("test.value") == 20
        assert snapshot.key == "test.value"
        assert snapshot.value == 10  # 旧值
        assert snapshot.version == 1
        assert snapshot.change_reason == "测试更新"

    def test_set_validation_failure(self):
        store = ParameterStore()
        store.register("test.int", default=10, param_type=ParamType.INT)

        with pytest.raises(ParameterValidationError):
            store.set("test.int", "not_an_int")

    def test_set_unknown_param(self):
        store = ParameterStore()
        with pytest.raises(ParameterNotFoundError):
            store.set("unknown.param", 100)

    def test_register_many(self):
        store = ParameterStore()
        store.register_many([
            {"key": "param.a", "default": 1, "param_type": ParamType.INT},
            {"key": "param.b", "default": 2, "param_type": ParamType.INT},
            {"key": "param.c", "default": 3, "param_type": ParamType.INT},
        ])

        assert store.get("param.a") == 1
        assert store.get("param.b") == 2
        assert store.get("param.c") == 3

    def test_set_many(self):
        store = ParameterStore()
        store.register_many([
            {"key": "x", "default": 1, "param_type": ParamType.INT},
            {"key": "y", "default": 2, "param_type": ParamType.INT},
        ])

        snapshots = store.set_many({"x": 10, "y": 20}, reason="批量更新")

        assert store.get("x") == 10
        assert store.get("y") == 20
        assert len(snapshots) == 2

    def test_get_version(self):
        store = ParameterStore()
        store.register("v.param", default=1, param_type=ParamType.INT)

        assert store.get_version("v.param") == 1

        store.set("v.param", 2)
        assert store.get_version("v.param") == 2

    def test_get_history(self):
        store = ParameterStore()
        store.register("h.param", default=1, param_type=ParamType.INT)

        store.set("h.param", 2, reason="第一次更新")
        store.set("h.param", 3, reason="第二次更新")

        history = store.get_history("h.param")

        assert len(history) == 2
        assert history[0].value == 2  # 最新的是第二个值
        assert history[0].change_reason == "第二次更新"

    def test_rollback(self):
        store = ParameterStore()
        store.register("r.param", default=1, param_type=ParamType.INT)

        store.set("r.param", 2)
        store.set("r.param", 3)

        # 回滚到版本 1（值为 1）
        snapshot = store.rollback("r.param", version=1, reason="测试回滚")

        assert store.get("r.param") == 1
        assert snapshot.value == 3  # 回滚前的值
        assert store.get_version("r.param") == 4  # 版本递增

    def test_rollback_invalid_version(self):
        store = ParameterStore()
        store.register("rv.param", default=1, param_type=ParamType.INT)

        with pytest.raises(ParameterError):
            store.rollback("rv.param", version=999)

    def test_get_all(self):
        store = ParameterStore()
        store.register_many([
            {"key": "a", "default": 1, "param_type": ParamType.INT},
            {"key": "b", "default": 2, "param_type": ParamType.INT},
        ])

        all_params = store.get_all()
        assert all_params == {"a": 1, "b": 2}

    def test_delete(self):
        store = ParameterStore()
        store.register("d.param", default=1, param_type=ParamType.INT)

        store.delete("d.param")

        with pytest.raises(ParameterNotFoundError):
            store.get("d.param")


class TestValidation:
    """约束验证测试。"""

    def test_validate_success(self):
        store = ParameterStore()
        store.register(
            "v.param",
            default=0.5,
            param_type=ParamType.FLOAT,
            min_val=0.0,
            max_val=1.0,
            choices=[0.1, 0.5, 0.9]
        )

        result = store.validate("v.param", 0.9)
        assert result.valid

    def test_validate_type_mismatch(self):
        store = ParameterStore()
        store.register("vm.param", default=1, param_type=ParamType.INT)

        result = store.validate("vm.param", "string")
        assert not result.valid
        assert "type" in result.errors[0].field

    def test_validate_out_of_range(self):
        store = ParameterStore()
        store.register(
            "vr.param",
            default=0.5,
            param_type=ParamType.FLOAT,
            min_val=0.0,
            max_val=1.0
        )

        result = store.validate("vr.param", 2.0)
        assert not result.valid
        assert "max" in result.errors[0].field

    def test_validate_not_in_choices(self):
        store = ParameterStore()
        store.register(
            "vc.param",
            default="a",
            param_type=ParamType.STR,
            choices=["a", "b", "c"]
        )

        result = store.validate("vc.param", "d")
        assert not result.valid
        assert "choices" in result.errors[0].field

    def test_validate_all(self):
        store = ParameterStore()
        store.register("good", default=0.5, param_type=ParamType.FLOAT)
        # Use valid default, then manually set invalid value
        store.register("bad", default=1, param_type=ParamType.INT, min_val=0, max_val=5)

        # Manually set an invalid value (bypassing validation for testing)
        store._params["bad"].value = 100

        results = store.validate_all()
        assert results["good"].valid
        assert not results["bad"].valid


class TestReset:
    """重置功能测试。"""

    def test_reset(self):
        store = ParameterStore()
        store.register("rs.param", default=1, param_type=ParamType.INT)
        store.set("rs.param", 100)

        snapshot = store.reset("rs.param")

        assert store.get("rs.param") == 1
        assert snapshot.value == 100

    def test_reset_all(self):
        store = ParameterStore()
        store.register_many([
            {"key": "ra.a", "default": 1, "param_type": ParamType.INT},
            {"key": "ra.b", "default": 2, "param_type": ParamType.INT},
        ])
        store.set_many({"ra.a": 100, "ra.b": 200})

        snapshots = store.reset_all()

        assert store.get("ra.a") == 1
        assert store.get("ra.b") == 2
        assert len(snapshots) == 2


class TestPersistence:
    """持久化测试。"""

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "params.json"

            # 创建并保存
            store1 = ParameterStore(path)
            store1.register("p.value", default=1, param_type=ParamType.INT)
            store1.set("p.value", 100, reason="持久化测试")

            # 加载
            store2 = ParameterStore(path)
            assert store2.get("p.value") == 100
            assert store2.get_version("p.value") == 2

    def test_export_import(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "params.json"

            store1 = ParameterStore(path)
            store1.register("e.param", default=1, param_type=ParamType.INT)
            store1.set("e.param", 2, reason="导出测试")

            exported = store1.export()

            store2 = ParameterStore()
            store2.import_data(exported)

            assert store2.get("e.param") == 2


class TestEdgeCases:
    """边界情况测试。"""

    def test_bool_parameter(self):
        store = ParameterStore()
        store.register("enabled", default=False, param_type=ParamType.BOOL)
        assert store.get("enabled") is False

        store.set("enabled", True)
        assert store.get("enabled") is True

    def test_list_parameter(self):
        store = ParameterStore()
        store.register("watchlist", default=[], param_type=ParamType.LIST)
        assert store.get("watchlist") == []

        store.set("watchlist", ["000001.SZ", "510300.SH"])
        assert store.get("watchlist") == ["000001.SZ", "510300.SH"]

    def test_dict_parameter(self):
        store = ParameterStore()
        store.register("config", default={}, param_type=ParamType.DICT)
        assert store.get("config") == {}

        store.set("config", {"timeout": 30, "retries": 3})
        assert store.get("config") == {"timeout": 30, "retries": 3}

    def test_snapshot_max_limit(self):
        store = ParameterStore(max_snapshots=5)
        store.register("ml.param", default=0, param_type=ParamType.INT)

        for i in range(10):
            store.set("ml.param", i)

        history = store.get_history("ml.param")
        # 最多保留 5 个
        assert len(history) == 5
        # 最新的 5 个快照（按版本降序）
        # 版本 1-9 有快照，当前值是版本 10
        assert [h.value for h in history] == [8, 7, 6, 5, 4]
