# P1-026D: process_tasks 去 global config 设计

## 问题

`run_process_tasks(config=...)` 接收 config 参数后写入 `global _config`，handlers 通过 `_get_config()` 隐式读取。

**问题**：
- 隐式依赖 global state，单测困难
- 并发 worker 可能互相覆盖 `_config`
- 违反显式依赖原则

## 解法

用闭包捕获替代 global：`run_process_tasks` 内部创建 handler 闭包，显式捕获 config。

## 架构

```
run_process_tasks(config=...)
        ↓
    _create_handlers(config) → 创建闭包 handler
        ↓
    处理 tasks，用局部 handlers
```

## 变更点

### 删除

- `global _config`（run_process_tasks 内）
- `_config` 变量声明
- `_get_config()` 函数
- `from src.common.config import AppConfig`（如不再需要）

### 新增

`_create_handlers(config: AppConfig) -> dict[str, TaskHandler]`：

```python
def _create_handlers(config: AppConfig) -> dict[str, TaskHandler]:
    async def handle_article_ingested(details: dict[str, Any]) -> None:
        from src.agents.data_agent.skills.extract_article_metadata import extract_and_store_metadata
        await extract_and_store_metadata(
            config=config,  # 闭包捕获，无 global
            base_dir=Path("."),
            limit=20,
        )

    async def handle_article_metadata_extracted(details: dict[str, Any]) -> None:
        from src.persona.cluster_builder import build_clusters_from_db
        dest = Path("data/processed/persona/clusters.real.json")
        await build_clusters_from_db(config=config, dest=dest)

    return {
        "article_ingested": handle_article_ingested,
        "article_metadata_extracted": handle_article_metadata_extracted,
    }
```

`_process_one` 签名改为接收 `handlers: dict[str, TaskHandler]` 而非从 `TASK_HANDLERS` 读取。

### 不变

- `run_process_tasks(config, ...)` 接口（DAG 调用方不需改）
- `ProcessTasksStats` dataclass
- `TASK_HANDLERS` 全局注册表（保留供外部 `register_handler` 使用，但 run_process_tasks 内部不用）

## 事务语义

无变化：`_process_one` 失败 → 写入 failed_tasks.jsonl → 继续处理下一个。

## 测试收益

单测可注入 mock config：

```python
mock_config = MockConfig()
handlers = _create_handlers(mock_config)
handler = handlers["article_ingested"]
# handler 直接使用 mock_config，无 global 污染
```

## 验证

1. 全量测试通过：`pytest tests/ -v`
2. 端到端验证：pipeline DAG 端到端运行，pending_tasks 清空，failed_tasks 无新增
