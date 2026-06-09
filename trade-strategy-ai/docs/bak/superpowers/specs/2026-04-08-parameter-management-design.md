# P4-018~P4-021 参数管理系统设计

## 1. 背景与目标

参数管理系统负责管理策略执行过程中的所有可配置参数，包括：
- 策略参数（止损/止盈阈值、仓位大小等）
- 风控参数（最大持仓、单股集中度等）
- 路由参数（评分权重、Top-K 选择等）

**目标**：
1. 提供统一的参数存储、版本控制、动态更新机制
2. 支持参数约束验证，确保参数合法性
3. 支持参数变更历史追溯

## 2. 数据结构设计

### 2.1 ParameterDef（参数定义）

```python
@dataclass
class ParameterDef:
    """单个参数的定义元数据。"""
    key: str                      # 参数键，如 "risk.max_position_pct"
    value: Any                    # 当前值
    param_type: ParamType         # int / float / bool / str / list / dict
    default: Any                  # 默认值
    min: float | None             # 最小值（数值类型）
    max: float | None             # 最大值（数值类型）
    choices: list | None         # 允许的枚举值
    description: str | None       # 参数描述
    version: int                  # 版本号
    updated_at: datetime          # 更新时间
    updated_by: str | None        # 更新人
```

### 2.2 ParameterSnapshot（参数快照）

```python
@dataclass
class ParameterSnapshot:
    """参数的版本快照（不可变）。"""
    snapshot_id: str              # UUID
    key: str                       # 参数键
    value: Any                     # 快照值
    version: int                   # 版本号
    created_at: datetime           # 创建时间
    created_by: str | None         # 创建人
    change_reason: str | None      # 变更原因
```

### 2.3 ParameterStore（参数存储）

```python
class ParameterStore:
    """参数存储核心类。"""

    def __init__(self, storage_path: str | None = None):
        self._params: dict[str, ParameterDef] = {}
        self._snapshots: list[ParameterSnapshot] = []
        self._storage_path = storage_path

    # ---- CRUD ----
    def register(self, key: str, default: Any, ...) -> None
    def get(self, key: str) -> Any
    def set(self, key: str, value: Any, reason: str | None = None) -> ParameterSnapshot

    # ---- 版本控制 ----
    def get_version(self, key: str) -> int
    def get_history(self, key: str) -> list[ParameterSnapshot]
    def rollback(self, key: str, version: int) -> ParameterSnapshot

    # ---- 批量操作 ----
    def register_many(self, definitions: list[ParameterDef]) -> None
    def get_all(self) -> dict[str, Any]
    def set_many(self, updates: dict[str, Any], reason: str | None = None) -> list[ParameterSnapshot]

    # ---- 约束验证 ----
    def validate(self, key: str, value: Any) -> ValidationResult
    def validate_all(self) -> list[ValidationResult]
```

## 3. 约束验证规则

| 规则 | 说明 |
|------|------|
| 类型检查 | 值类型必须与 param_type 匹配 |
| 范围检查 | 数值必须在 min/max 范围内 |
| 枚举检查 | 值必须在 choices 中 |
| 非空检查 | 不能设置为 None（除非 default 为 None） |

## 4. 版本控制策略

- 每次 `set()` 调用都会创建新快照
- 支持按版本号回滚
- 快照保留最近 N 条（默认 100 条），超限自动清理
- 支持变更原因记录

## 5. 持久化方案

- 默认使用 JSON 文件存储（`params.json`）
- 快照存储在单独文件（`params_snapshots.jsonl`）
- 可扩展为数据库存储

## 6. 使用示例

```python
from src.persona.param_store import ParameterStore, ParameterDef, ParamType

store = ParameterStore("data/params")

# 注册参数
store.register(
    key="risk.max_position_pct",
    default=0.1,
    param_type=ParamType.FLOAT,
    min=0.0,
    max=1.0,
    description="单股最大持仓比例"
)

# 获取参数
max_pos = store.get("risk.max_position_pct")

# 更新参数（自动创建快照）
snapshot = store.set("risk.max_position_pct", 0.15, reason="根据回测结果调整")

# 查看历史
history = store.get_history("risk.max_position_pct")

# 回滚
store.rollback("risk.max_position_pct", version=snapshot.version - 1)

# 验证
result = store.validate("risk.max_position_pct", 1.5)  # 失败，超出 max
```

## 7. 文件结构

```
src/persona/
    param_store.py      # 参数存储核心实现
    param_types.py      # 参数类型枚举和验证
    __init__.py         # 导出

tests/unit/persona/
    test_param_store.py # 单元测试
```
