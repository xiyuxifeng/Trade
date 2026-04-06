# Pending Tasks Processor 设计

## 目标
实现 pending_tasks 处理器：读取 `pending_tasks.jsonl`，根据 task type 分发到对应处理器，支持重试和 article_id 去重。

## 背景

Pipeline 当前只在 `store_db` 和 `extract_metadata` 时往 `pending_tasks.jsonl` 写任务，但没有任何消费端。pending_tasks 处理器负责把这些任务实际处理完。

## 任务类型与处理器映射

| task.type | 处理器 | 说明 |
|---|---|---|
| `article_ingested` | `extract_and_store_metadata()` | 触发 LLM 抽取 |
| `article_metadata_extracted` | `build_clusters_from_db()` | 触发聚类重建 |

## 处理器设计

### ProcessTasksStats
```python
@dataclass
class ProcessTasksStats:
    processed: int      # 成功处理
    skipped_dedup: int  # article_id 去重跳过
    retried: int        # 重试成功
    failed: int         # 重试耗尽后失败
    duration_ms: int
```

### 核心逻辑

```
1. 读取 pending_tasks.jsonl 所有任务（按 created_at 顺序）
2. 按 article_id 去重：以该 article 最新 task 为准，丢弃旧 task
3. 遍历每个任务：
   a. 根据 type 分发到对应处理器
   b. 成功 → 从 pending_tasks.jsonl 移除（或标记完成）
   c. 失败 → 重试（最多 max_retries 次）
   d. 重试耗尽 → 写入 failed_tasks.jsonl
4. 返回 ProcessTasksStats
```

### 去重规则
- 基于 `details.article_id` 去重
- 同一 article_id 只保留**最新** task（按 created_at 倒序）
- `article_metadata_extracted` 任务：如果该 article 的 metadata 已存在（`processed_at IS NOT NULL`），跳过

### 重试规则
- 最大重试次数：3（可配置）
- 指数退避：第 N 次重试等待 `2^N` 秒
- 重试耗尽后写入 `data/processed/pipeline/failed_tasks.jsonl`

## Pipeline 集成

在 `dag.py` 中，`store` 之后新增 `process_pending_tasks` 步骤：

```
crawl → clean → validate → store → **process_pending_tasks** → export
```

## 文件结构

```
src/pipeline/tasks/process_tasks.py   # 核心处理器
```

## 输出文件

- `data/processed/pipeline/pending_tasks.jsonl` — 处理完成后清空（所有任务已处理或移至 failed）
- `data/processed/pipeline/failed_tasks.jsonl` — 永久失败任务
