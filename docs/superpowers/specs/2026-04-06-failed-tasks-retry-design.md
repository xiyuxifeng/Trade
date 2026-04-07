# P1-026E: failed_tasks.jsonl 自动重试 + TTL 清理设计

## 问题

`failed_tasks.jsonl` 当前只追加不清理，失败任务会永久积累。任务失败后永久跳过，无法恢复。

## 解法

结合重试计数器 + TTL 清理：
- **重试计数**：失败任务在再次触发时被重试，超过 3 次上限后移入 dead_tasks
- **TTL 清理**：超过 7 天的失败记录自动清理

## 数据结构变更

`failed_tasks.jsonl` 每行增加两个字段：

```json
{
  "task_id": "...",
  "type": "...",
  "details": {...},
  "created_at": "...",
  "failed_at": "2026-04-06T10:00:00Z",
  "retry_count": 1
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `failed_at` | ISO8601 string | 首次失败时间（用于 TTL 计算） |
| `retry_count` | int | 累计失败次数（每次追加 +1） |

**向后兼容**：缺少 `failed_at`/`retry_count` 的旧记录视为 retry_count=0，failed_at=now。

## 常量

```python
MAX_RETRY_COUNT = 3   # 超过此值移入 dead_tasks
FAILED_TTL_DAYS = 7   # 超过此天数的失败记录清理
```

## 文件

| 文件 | 说明 |
|------|------|
| `data/processed/pipeline/failed_tasks.jsonl` | 失败任务（retry_count < 3） |
| `data/processed/pipeline/dead_tasks.jsonl` | 永久死亡任务（retry_count >= 3 或超过 TTL） |

## 函数设计

### `_load_failed_with_metadata(path: Path) -> list[dict[str, Any]]`

加载 failed_tasks，解析 `failed_at`（ISO8601）和 `retry_count`（默认 0）。旧格式（无这两个字段）自动补全。

### `_save_failed_with_metadata(path: Path, tasks: list[dict[str, Any]]) -> None`

写入带 `failed_at` 和 `retry_count` 的 JSONL。每行追加模式。

### `_cleanup_failed_tasks(tasks: list[dict[str, Any]]) -> tuple[list[dict], list[dict]]`

输入失败任务列表，返回 `(alive_tasks, dead_tasks)`：
- `alive_tasks`：retry_count < 3 且 failed_at 在 7 天内
- `dead_tasks`：retry_count >= 3 或 failed_at 超过 7 天

### `_update_failed_task(existing: dict, exc: Exception) -> dict`

更新失败任务记录：
- `retry_count += 1`
- `failed_at` 保持首次失败时间

## 重试流程

在 `run_process_tasks` 处理每个 task 时：

```
task 失败 →
  读取 failed_tasks.jsonl →
  找到匹配的 task_id →
  retry_count += 1 →
  if retry_count >= 3:
    移入 dead_tasks.jsonl
  else:
    写回 failed_tasks.jsonl
```

## TTL 清理流程

在 `run_process_tasks` 开头执行：

```
1. 加载 failed_tasks.jsonl
2. 过滤：failed_at > now - 7天 AND retry_count < 3 → 保留
3. 过滤：failed_at <= now - 7天 OR retry_count >= 3 → 移入 dead_tasks
4. 写回清理后的 failed_tasks.jsonl
5. 追加 dead_tasks 到 dead_tasks.jsonl
```

## ProcessTasksStats 变更

```python
@dataclass
class ProcessTasksStats:
    processed: int = 0
    skipped_dedup: int = 0
    retried: int = 0
    failed: int = 0
    dead: int = 0        # 新增：被判定为 dead 的任务数
    duration_ms: int = 0
```

## 变更点

| 文件 | 变更 |
|------|------|
| `process_tasks.py` | 修改 `run_process_tasks` 集成重试 + TTL 逻辑 |
| `process_tasks.py` | 新增 `_load_failed_with_metadata`、`_save_failed_with_metadata`、`_cleanup_failed_tasks`、`_update_failed_task` |

## 验证

1. 单元测试：TTL 过滤（7 天边界）、重试计数逻辑（3 次上限）
2. E2E：模拟任务失败 3 次，验证进入 dead_tasks
3. E2E：验证超过 7 天 TTL 的失败任务被清理
