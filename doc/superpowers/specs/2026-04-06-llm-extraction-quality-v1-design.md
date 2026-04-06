# LLM 抽取质量提升 v1 设计

## 目标

让 LLM 抽取链路（`extract_article_metadata`）在真实 LLM（通义千问）下产出内容，使 `extracted_concepts`、`trading_symbols`、`strategy_rules`、`preconditions` 四个字段从空变为有输出。

---

## 现状分析

| 字段 | 当前状态 | 问题 |
|------|----------|------|
| `extracted_concepts` | 0 条 | LLM 未配置，fallback 模式 |
| `trading_symbols` | 0 条 | 同上 |
| `strategy_rules` | 0 条 | 同上 |
| `preconditions` | 0 条 | 同上 |
| `comment_insights` | 空 | prompt 未覆盖 |
| `sentiment_score` | null | 同上 |
| `confidence_score` | null | 同上 |

- LLM API：已配置 `DASHSCOPE_API_KEY`，provider 为 `qwen`（openai_compatible 模式）
- 当前 1 条 article metadata 处于 `fallback` 模式，所有字段为空

---

## 实现方案（第 1 轮：字段填充优先）

### 1. 配置 LLM provider 为 qwen

修改 `config/app.yaml` 或 `.env`：

```yaml
llm:
  provider: openai_compatible  # qwen 走 openai 兼容模式
  model: qwen-turbo            # 免费模型先行
  url: https://dashscope.aliyuncs.com/compatible-mode/v1
  api_key: ${DASHSCOPE_API_KEY}
```

**已有代码支持**：`client.py` 第 65 行已处理 `qwen` / `openai_compatible` 场景，无需修改。

### 2. 调整 content 截断策略

当前截断为 12000 字符。qwen-turbo 免费版 context window 足够，但第一条输出可能过于冗长。

**策略**：保持 12000，不做修改。先跑出结果再决定是否压缩。

### 3. 合并 system prompt 结构

当前 `_extract_one` 把三个 prompt 文件拼接为 system_prompt，LLM 可能不清楚"每个字段分别输出多少"。

**改进**：在 system prompt 末尾增加结构化说明：

```
输出格式要求：
{
  "extracted_concepts": [...],   // 0-10 条，太多说明提取不精准
  "trading_symbols": [...],       // 0-5 个，优先提取有把握的
  "strategy_rules": [...],        // 0-5 条，宁缺毋滥
  "preconditions": [...],         // 0-5 条
  "comment_insights": [...],      // 0-3 条，从评论中提炼
  "sentiment_score": float,       // -1.0 ~ 1.0
  "confidence_score": float       // 0.0 ~ 1.0
}
```

### 4. 添加 fallback 时的启发式兜底

当前 LLMError 时写入全空 fallback：

```python
# 改进：LLM 不可用时，用启发式规则提取 trading_symbols
if not client.is_enabled():
    raw = _heuristic_extract(article)
```

`_heuristic_extract` 实现思路：
- 从 `content_text` 中用正则提取股票代码（`\d{6}\.(SZ|SH|BJ)`）
- 从 `raw_payload` 中读取 `author_name` 作为概念标签
- sentiment_score 用启发式（正负向词汇计数）

### 5. 统计与日志

在 `ExtractStats` 中增加：

```python
@dataclass
class ExtractStats:
    # 现有字段...
    llm_calls: int = 0           # 实际调用 LLM 次数
    fallback_calls: int = 0       # 启发式兜底次数
```

---

## 第 2 轮：Schema 合规性 + 可调试性（后续迭代）

> 以下为预留计划，完成第 1 轮后执行，TaskList 标记为 TODO。

### 2.1 Schema 合规性

**目标**：让每条 strategy_rule / precondition 都符合 `ArticleStrategyRule` / `ArticlePrecondition` schema，不合规条目不再静默丢弃。

实现方式：
- 增加 `_validate_and_log_rules()` 函数，记录被丢弃的条目及原因
- 统计合规率：`valid_rules / extracted_rules`
- prompt 增加"严格按 schema 输出"的说明

### 2.2 错误分类与可调试性

**目标**：LLM 出错时能分类溯源，不重复踩坑。

增加错误分类：

```python
class ExtractErrorType(Enum):
    NETWORK_ERROR = "network"      # 连接/超时错误
    JSON_PARSE_ERROR = "json"      # LLM 输出非 JSON
    SCHEMA_VALIDATION_ERROR = "schema"  # 输出不合 schema
    LLM_QUALITY_ERROR = "quality"  # LLM 能力不足（返回空/无效内容）
    UNKNOWN_ERROR = "unknown"
```

每条 failed record 写入 `data/processed/llm_extraction_errors.jsonl`，格式：

```json
{
  "article_id": "...",
  "error_type": "json",
  "error_message": "...",
  "raw_output": "...",    // 截断到 500 字符
  "retry_count": 0,
  "timestamp": "..."
}
```

---

## 验证方式

1. 运行 `python -m cli.main extract-articles --limit 5`
2. 检查 PostgreSQL 中 `article_metadata` 各字段是否非空
3. 对比 prompt 改进前后的字段填充率

---

## 风险与备选

| 风险 | 应对 |
|------|------|
| qwen-turbo 免费版限流 | 加重试 + exponential backoff |
| 免费模型抽取质量差 | 先接受低质量，快速迭代 prompt；后续切付费模型 |
| JSON 输出不稳定 | prompt 中强调"不要 markdown"，加 `response_format: json_object` |

---

## 实现步骤

1. 更新 `config/app.yaml` 的 llm 配置（或 .env）
2. 修改 `_extract_one` 的 system_prompt，补充输出格式说明
3. 实现 `_heuristic_extract` 兜底逻辑
4. `ExtractStats` 增加 `llm_calls` / `fallback_calls`
5. 端到端运行验证
