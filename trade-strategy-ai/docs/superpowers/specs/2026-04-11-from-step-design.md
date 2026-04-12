# Pipeline --from-step 参数设计（2026-04-11）

## 1. 目标

支持从指定步骤开始执行 pipeline，跳过前面的步骤，实现精准重跑。

## 2. 使用场景

### 2.1 常见使用场景

| 场景 | 命令 |
|------|------|
| 从头开始跑完整流程 | `pipeline-run` |
| 跳过爬取，从清洗开始 | `pipeline-run --from-step clean` |
| 跳过爬取和清洗，从验证开始 | `pipeline-run --from-step validate` |
| 只跑导出步骤 | `pipeline-run --from-step export` |

### 2.2 步骤顺序

Pipeline 的完整步骤顺序：

```
crawl → clean → validate → store → stock_info_update → process → export
```

## 3. 实现设计

### 3.1 参数定义

**--from-step 参数**：
```python
from_step: str | None = None
```

可选值：`crawl`, `clean`, `validate`, `store`, `stock_info_update`, `process`, `export`

**--use-db 参数**：
```python
use_db: bool = False  # 是否使用数据库模式存储原始数据
```

- `use_db=False`（默认）：Crawl → articles.jsonl 文件
- `use_db=True`：Crawl → raw_articles 表

### 3.2 跳过逻辑

在 `_build_data_pipeline_handlers` 中，通过 `_should_skip` 函数判断是否跳过：

```python
STEP_ORDER = ["crawl", "clean", "validate", "store", "stock_info_update", "process", "export"]

def _should_skip(step_name: str) -> bool:
    if from_step is None:
        return False
    from_index = STEP_ORDER.index(from_step)
    current_index = STEP_ORDER.index(step_name)
    return current_index < from_index
```

### 3.3 各步骤的跳过处理

| 步骤 | 跳过时的处理 |
|------|-------------|
| crawl | 返回空的 `CrawlResult(outputs=[])` |
| clean | 使用已存在的 `.cleaned.jsonl` 文件作为输入 |
| validate | 使用已存在的 `.validated.jsonl` 文件作为输入 |
| store | 返回空的 `StoreStats()` |
| stock_info_update | 返回空的 `StockInfoUpdateResult(updated=False)` |
| process | 返回空的 `ProcessTasksStats()` |
| export | 使用空的 `ExportResult` |

### 3.4 状态伪造

当跳过某些步骤时，需要伪造对应的结果对象以便后续步骤可以继续：

```python
def _clean(context: dict[str, Any]) -> CleanResult:
    if _should_skip("clean"):
        # 使用已存在的 .cleaned.jsonl 文件
        cleaned_paths = [out_dir / "xxx.articles.cleaned.jsonl"]
        return CleanResult(cleaned_paths=cleaned_paths, stats_path=...)
```

## 4. 使用示例

### 4.1 从 validate 开始（跳过 crawl 和 clean）

```bash
# 假设已有 .cleaned.jsonl 文件
python -m cli.main pipeline-run --from-step validate
```

### 4.2 从 store 开始（跳过 crawl、clean、validate）

```bash
# 假设已有 .validated.jsonl 文件
python -m cli.main pipeline-run --from-step store
```

### 4.3 从 export 开始（只导出到 DuckDB）

```bash
python -m cli.main pipeline-run --from-step export
```

### 4.4 使用 --force 强制重跑

```bash
# 从 clean 开始，强制重跑 clean 和后续步骤
python -m cli.main pipeline-run --from-step clean --force
```

### 4.5 使用 --use-db 数据库模式

```bash
# 使用数据库模式爬取
python -m cli.main pipeline-run --use-db

# 数据库模式 + 从 clean 开始
python -m cli.main pipeline-run --use-db --from-step clean
```

## 5. 注意事项

- `--from-step` 依赖已存在的中间产物文件
- 如果跳过的步骤所需的输入文件不存在，会报错
- `--skip-crawl` 和 `--from-step` 可以同时使用，但 `--skip-crawl` 只影响 crawl 步骤
- 建议配合 `--force` 使用以确保数据是最新的
- `--use-db` 会将数据写入 `raw_articles` 表，需要确保数据库可用

## 6. 代码位置

- CLI 入口：`cli/main.py`
- Pipeline 定义：`src/pipeline/dag.py`
- Handler 构建：`_build_data_pipeline_handlers` 函数
