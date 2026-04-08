"""
参数存储核心实现 — P4-018~P4-021。

提供统一的参数存储、版本控制、动态更新和约束验证机制。
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from src.persona.param_types import (
    ParamType,
    ValidationError,
    ValidationResult,
    validate_param,
)


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class ParameterDef:
    """单个参数的定义元数据。"""
    key: str
    value: Any
    param_type: ParamType
    default: Any
    min_val: float | None = None
    max_val: float | None = None
    choices: list | None = None
    description: str | None = None
    version: int = 1
    updated_at: datetime = field(default_factory=datetime.now)
    updated_by: str | None = None

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "value": self.value,
            "param_type": self.param_type.value,
            "default": self.default,
            "min_val": self.min_val,
            "max_val": self.max_val,
            "choices": self.choices,
            "description": self.description,
            "version": self.version,
            "updated_at": self.updated_at.isoformat(),
            "updated_by": self.updated_by,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ParameterDef":
        d = dict(d)
        d["param_type"] = ParamType(d["param_type"])
        d["updated_at"] = datetime.fromisoformat(d["updated_at"])
        return cls(**d)


@dataclass
class ParameterSnapshot:
    """参数的版本快照（不可变）。"""
    snapshot_id: str
    key: str
    value: Any
    version: int
    created_at: datetime
    created_by: str | None
    change_reason: str | None

    def to_dict(self) -> dict:
        return {
            "snapshot_id": self.snapshot_id,
            "key": self.key,
            "value": self.value,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "change_reason": self.change_reason,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ParameterSnapshot":
        d = dict(d)
        d["created_at"] = datetime.fromisoformat(d["created_at"])
        return cls(**d)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ParameterError(Exception):
    """参数相关错误基类。"""
    pass


class ParameterNotFoundError(ParameterError):
    """参数不存在。"""
    pass


class ParameterValidationError(ParameterError):
    """参数验证失败。"""
    def __init__(self, result: ValidationResult):
        super().__init__(f"Validation failed: {result.errors}")
        self.result = result


# ---------------------------------------------------------------------------
# Parameter Store
# ---------------------------------------------------------------------------

class ParameterStore:
    """参数存储核心类。

    提供统一的参数存储、版本控制、动态更新和约束验证机制。

    用法：
        store = ParameterStore("data/params")

        # 注册参数
        store.register("risk.max_position_pct", default=0.1, param_type=ParamType.FLOAT,
                       min_val=0.0, max_val=1.0)

        # 获取参数
        max_pos = store.get("risk.max_position_pct")

        # 更新参数
        snapshot = store.set("risk.max_position_pct", 0.15, reason="根据回测结果调整")

        # 查看历史
        history = store.get_history("risk.max_position_pct")

        # 回滚
        store.rollback("risk.max_position_pct", version=snapshot.version - 1)
    """

    DEFAULT_MAX_SNAPSHOTS = 100

    def __init__(
        self,
        storage_path: str | Path | None = None,
        max_snapshots: int = DEFAULT_MAX_SNAPSHOTS,
    ):
        """初始化参数存储。

        Args:
            storage_path: 存储路径（JSON 文件），为 None 则只存储在内存
            max_snapshots: 每个参数保留的最大快照数
        """
        self._params: dict[str, ParameterDef] = {}
        self._snapshots: list[ParameterSnapshot] = []
        self._storage_path = Path(storage_path) if storage_path else None
        self._max_snapshots = max_snapshots

        if self._storage_path:
            self._load()

    # ---- Internal ----

    def _load(self) -> None:
        """从磁盘加载参数。"""
        if not self._storage_path or not self._storage_path.exists():
            return

        try:
            with open(self._storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            params_data = data.get("params", {})
            for key, param_dict in params_data.items():
                self._params[key] = ParameterDef.from_dict(param_dict)

            snapshots_data = data.get("snapshots", [])
            for snap_dict in snapshots_data:
                self._snapshots.append(ParameterSnapshot.from_dict(snap_dict))
        except (json.JSONDecodeError, KeyError) as e:
            raise ParameterError(f"Failed to load params from {self._storage_path}: {e}") from e

    def _save(self) -> None:
        """保存参数到磁盘。"""
        if not self._storage_path:
            return

        self._storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "params": {k: v.to_dict() for k, v in self._params.items()},
            "snapshots": [s.to_dict() for s in self._snapshots],
        }

        with open(self._storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _get_param(self, key: str) -> ParameterDef:
        """获取参数定义。"""
        if key not in self._params:
            raise ParameterNotFoundError(f"Parameter not found: {key}")
        return self._params[key]

    def _cleanup_snapshots(self, key: str) -> None:
        """清理超过最大数量的快照。"""
        key_snapshots = [s for s in self._snapshots if s.key == key]
        if len(key_snapshots) > self._max_snapshots:
            # 按版本号排序（降序），保留最新的 N 个
            key_snapshots.sort(key=lambda s: s.version, reverse=True)
            to_remove = key_snapshots[self._max_snapshots:]
            for snap in to_remove:
                self._snapshots.remove(snap)

    # ---- CRUD ----

    def register(
        self,
        key: str,
        default: Any,
        param_type: ParamType,
        min_val: float | None = None,
        max_val: float | None = None,
        choices: list | None = None,
        description: str | None = None,
        value: Any | None = None,
        updated_by: str | None = None,
    ) -> None:
        """注册新参数。

        Args:
            key: 参数键
            default: 默认值
            param_type: 参数类型
            min_val: 最小值（数值类型）
            max_val: 最大值（数值类型）
            choices: 枚举选项
            description: 参数描述
            value: 初始值（为 None 则使用 default）
            updated_by: 更新人

        Raises:
            ParameterError: 参数已存在
        """
        if key in self._params:
            raise ParameterError(f"Parameter already exists: {key}")

        # 验证默认值
        result = validate_param(default, param_type, min_val, max_val, choices)
        if not result.valid:
            raise ParameterValidationError(result)

        # 验证初始值（如果提供）
        initial_value = value if value is not None else default
        result = validate_param(initial_value, param_type, min_val, max_val, choices)
        if not result.valid:
            raise ParameterValidationError(result)

        self._params[key] = ParameterDef(
            key=key,
            value=initial_value,
            param_type=param_type,
            default=default,
            min_val=min_val,
            max_val=max_val,
            choices=choices,
            description=description,
            version=1,
            updated_at=datetime.now(),
            updated_by=updated_by,
        )
        self._save()

    def register_many(self, definitions: list[dict]) -> None:
        """批量注册参数。

        Args:
            definitions: 参数定义列表，每项包含 register() 所需的参数
        """
        for d in definitions:
            self.register(**d)

    def get(self, key: str, default: Any | None = None) -> Any:
        """获取参数值。

        Args:
            key: 参数键
            default: 参数不存在时返回的默认值

        Returns:
            参数值

        Raises:
            ParameterNotFoundError: 参数不存在且未指定 default
        """
        try:
            return self._get_param(key).value
        except ParameterNotFoundError:
            if default is not None:
                return default
            raise

    def set(
        self,
        key: str,
        value: Any,
        reason: str | None = None,
        updated_by: str | None = None,
    ) -> ParameterSnapshot:
        """更新参数值。

        Args:
            key: 参数键
            value: 新值
            reason: 变更原因
            updated_by: 更新人

        Returns:
            创建的快照

        Raises:
            ParameterNotFoundError: 参数不存在
            ParameterValidationError: 验证失败
        """
        param = self._get_param(key)

        # 验证新值
        result = validate_param(
            value, param.param_type, param.min_val, param.max_val, param.choices
        )
        if not result.valid:
            raise ParameterValidationError(result)

        # 创建快照
        snapshot = ParameterSnapshot(
            snapshot_id=str(uuid.uuid4()),
            key=key,
            value=param.value,
            version=param.version,
            created_at=datetime.now(),
            created_by=updated_by,
            change_reason=reason,
        )
        self._snapshots.append(snapshot)

        # 更新参数
        param.value = value
        param.version += 1
        param.updated_at = datetime.now()
        param.updated_by = updated_by

        # 清理旧快照
        self._cleanup_snapshots(key)
        self._save()

        return snapshot

    def set_many(
        self,
        updates: dict[str, Any],
        reason: str | None = None,
        updated_by: str | None = None,
    ) -> list[ParameterSnapshot]:
        """批量更新参数。

        Args:
            updates: 参数键值对
            reason: 变更原因
            updated_by: 更新人

        Returns:
            创建的快照列表
        """
        snapshots = []
        for key, value in updates.items():
            try:
                snapshot = self.set(key, value, reason=reason, updated_by=updated_by)
                snapshots.append(snapshot)
            except (ParameterNotFoundError, ParameterValidationError):
                # 跳过无效的参数更新
                continue
        return snapshots

    def delete(self, key: str) -> None:
        """删除参数。

        Args:
            key: 参数键

        Raises:
            ParameterNotFoundError: 参数不存在
        """
        if key not in self._params:
            raise ParameterNotFoundError(f"Parameter not found: {key}")
        del self._params[key]
        # 保留快照（用于审计）
        self._save()

    # ---- 版本控制 ----

    def get_version(self, key: str) -> int:
        """获取参数当前版本号。

        Args:
            key: 参数键

        Returns:
            版本号
        """
        return self._get_param(key).version

    def get_history(self, key: str) -> list[ParameterSnapshot]:
        """获取参数变更历史。

        Args:
            key: 参数键

        Returns:
            快照列表（按时间倒序）
        """
        snapshots = [s for s in self._snapshots if s.key == key]
        snapshots.sort(key=lambda s: s.created_at, reverse=True)
        return snapshots

    def rollback(
        self,
        key: str,
        version: int,
        reason: str | None = None,
        updated_by: str | None = None,
    ) -> ParameterSnapshot:
        """回滚参数到指定版本。

        Args:
            key: 参数键
            version: 目标版本号
            reason: 回滚原因
            updated_by: 操作人

        Returns:
            创建的新快照

        Raises:
            ParameterNotFoundError: 参数不存在
            ParameterError: 版本不存在
        """
        snapshots = self.get_history(key)

        # 找到目标版本之前的值（即 version 对应的快照）
        target_snapshot = None
        for s in snapshots:
            if s.version == version:
                target_snapshot = s
                break

        if target_snapshot is None:
            raise ParameterError(f"Version {version} not found for key: {key}")

        # 使用目标版本的值进行回滚
        return self.set(key, target_snapshot.value, reason=reason or f"Rollback to version {version}", updated_by=updated_by)

    # ---- 批量操作 ----

    def get_all(self) -> dict[str, Any]:
        """获取所有参数的键值对。

        Returns:
            参数键值对字典
        """
        return {k: p.value for k, p in self._params.items()}

    def get_all_definitions(self) -> dict[str, ParameterDef]:
        """获取所有参数定义。

        Returns:
            参数定义字典
        """
        return dict(self._params)

    # ---- 约束验证 ----

    def validate(self, key: str, value: Any) -> ValidationResult:
        """验证参数值。

        Args:
            key: 参数键
            value: 要验证的值

        Returns:
            验证结果
        """
        try:
            param = self._get_param(key)
        except ParameterNotFoundError:
            return ValidationResult.failure([
                ValidationError(field="key", message=f"Parameter not found: {key}", value=key)
            ])

        return validate_param(
            value, param.param_type, param.min_val, param.max_val, param.choices
        )

    def validate_all(self) -> dict[str, ValidationResult]:
        """验证所有参数的当前值。

        Returns:
            参数键 -> 验证结果 的字典
        """
        results = {}
        for key, param in self._params.items():
            results[key] = validate_param(
                param.value, param.param_type, param.min_val, param.max_val, param.choices
            )
        return results

    # ---- 工具方法 ----

    def reset(self, key: str, updated_by: str | None = None) -> ParameterSnapshot:
        """重置参数为默认值。

        Args:
            key: 参数键
            updated_by: 操作人

        Returns:
            创建的快照
        """
        param = self._get_param(key)
        return self.set(key, param.default, reason="Reset to default", updated_by=updated_by)

    def reset_all(self, updated_by: str | None = None) -> list[ParameterSnapshot]:
        """重置所有参数为默认值。

        Args:
            updated_by: 操作人

        Returns:
            创建的快照列表
        """
        snapshots = []
        for key in self._params:
            try:
                snapshot = self.reset(key, updated_by=updated_by)
                snapshots.append(snapshot)
            except ParameterError:
                continue
        return snapshots

    def export(self) -> dict:
        """导出所有参数为字典。

        Returns:
            导出数据
        """
        return {
            "exported_at": datetime.now().isoformat(),
            "params": {k: p.to_dict() for k, p in self._params.items()},
            "snapshots": [s.to_dict() for s in self._snapshots],
        }

    def import_data(self, data: dict) -> None:
        """从字典导入参数。

        Args:
            data: 导出的数据
        """
        params_data = data.get("params", {})
        for key, param_dict in params_data.items():
            self._params[key] = ParameterDef.from_dict(param_dict)

        snapshots_data = data.get("snapshots", [])
        for snap_dict in snapshots_data:
            self._snapshots.append(ParameterSnapshot.from_dict(snap_dict))

        self._save()


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------

_default_store: ParameterStore | None = None


def get_param_store(storage_path: str | None = None) -> ParameterStore:
    """获取全局 ParameterStore 实例。

    Args:
        storage_path: 存储路径

    Returns:
        ParameterStore 实例
    """
    global _default_store
    if _default_store is None or storage_path is not None:
        _default_store = ParameterStore(storage_path)
    return _default_store
