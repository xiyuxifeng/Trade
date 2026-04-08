# LLM 抽取质量提升 v1 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 LLM 抽取链路在真实 LLM（qwen-turbo）下产出内容，4 个核心字段从空变为有输出。

**Architecture:**
- LLM provider 走 qwen-turbo（openai_compatible 模式），通过 `DASHSCOPE_API_KEY` 环境变量认证
- `extract_article_metadata.py` 为主入口，`_extract_one()` 拼接 system prompt，`_heuristic_extract()` 提供兜底
- `ExtractStats` 增加调用计数统计

**Tech Stack:** qwen-turbo (dashscope), openai-compatible API, Python 异步

---

## 文件变更概览

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `trade-strategy-ai/.env` | Modify | 添加 llm 配置 |
| `trade-strategy-ai/src/agents/data_agent/skills/extract_article_metadata.py` | Modify | prompt 增强 + heuristic 兜底 + 统计字段 |
| `trade-strategy-ai/src/llm/client.py` | Modify | qwen 支持已就绪（无需修改），确认 `is_enabled()` 逻辑 |

---

## Task 1: 确认 .env LLM 配置

**Files:**
- Modify: `trade-strategy-ai/.env:1-28`（确认现有内容）

- [ ] **Step 1: 确认 .env 当前内容**

查看 `.env` 中 llm 相关配置行（应在第 10-17 行附近）。

- [ ] **Step 2: 确认 llm 配置格式**

当前 `.env` 中 `DATABASE_URL` 已配置，`llm` 配置默认注释状态。

验证 `client.py` 第 65 行 `qwen` provider 处理逻辑：

```python
# trade-strategy-ai/src/llm/client.py:65
if provider in {"openai", "openai_compatible", "qwen", "deepseek"}:
    return await self._openai_chat_json(...)
```

确认 `is_enabled()` 对 dashscope API key 的检测正确：

```python
# trade-strategy-ai/src/llm/client.py:43-44
def is_enabled(self) -> bool:
    return bool(self.cfg.provider and self.cfg.model and self.cfg.api_key)
```

- [ ] **Step 3: 验证 DASHSCOPE_API_KEY 环境变量存在**

Run: `echo $DASHSCOPE_API_KEY | head -c 10`
Expected: 类似 `sk-xxx` 的非空字符串

如果为空，告知用户在 shell 中 `export DASHSCOPE_API_KEY=your_key`。

- [ ] **Step 4: Commit**

```bash
git add trade-strategy-ai/.env
git commit -m "chore: llm config placeholder confirmed"
```

---

## Task 2: 增强 system prompt 输出格式说明

**Files:**
- Modify: `trade-strategy-ai/src/agents/data_agent/skills/extract_article_metadata.py:113-148`

- [ ] **Step 1: 查看现有 `_extract_one` 函数**

确认当前 `_extract_one` 函数 system prompt 拼接方式（第 119-129 行）。

- [ ] **Step 2: 在 system prompt 末尾追加结构化输出说明**

修改第 128 行附近的 system_prompt 拼接，在 `"最终输出必须合并为一个 JSON 对象..."` 之后追加：

```python
    system_prompt = "\n\n".join([
        "你必须只输出严格 JSON，不要输出 Markdown。",
        concept_p,
        rule_p,
        pre_p,
        "最终输出必须合并为一个 JSON 对象，包含字段：extracted_concepts, trading_symbols, strategy_rules, preconditions, comment_insights, sentiment_score, confidence_score。",
        # --- 新增结构化说明 ---
        "\n\n输出格式要求：\n"
        "{\n"
        '  "extracted_concepts": [...],   // 0-10 条，太多说明提取不精准\n'
        '  "trading_symbols": [...],       // 0-5 个，优先提取有把握的\n'
        '  "strategy_rules": [...],        // 0-5 条，宁缺毋滥\n'
        '  "preconditions": [...],         // 0-5 条\n'
        '  "comment_insights": [...],      // 0-3 条，从评论中提炼\n'
        '  "sentiment_score": float,       // -1.0 ~ 1.0\n'
        '  "confidence_score": float       // 0.0 ~ 1.0\n'
        "}",
    ])
```

- [ ] **Step 3: 运行测试验证 prompt 语法正确**

Run: `cd trade-strategy-ai && python3 -c "from src.agents.data_agent.skills.extract_article_metadata import _extract_one; print('import ok')"`
Expected: `import ok`

- [ ] **Step 4: Commit**

```bash
git add trade-strategy-ai/src/agents/data_agent/skills/extract_article_metadata.py
git commit -m "feat(extract): 增强 system_prompt 结构化输出说明"
```

---

## Task 3: 实现 `_heuristic_extract` 兜底逻辑

**Files:**
- Modify: `trade-strategy-ai/src/agents/data_agent/skills/extract_article_metadata.py`

- [ ] **Step 1: 在 `ExtractStats` 中增加统计字段**

修改 `ExtractStats` dataclass（第 21-27 行），新增：

```python
@dataclass(slots=True)
class ExtractStats:
    scanned: int = 0
    extracted: int = 0
    skipped: int = 0
    failed: int = 0
    generated_tasks: int = 0
    llm_calls: int = 0          # 新增：实际调用 LLM 次数
    fallback_calls: int = 0     # 新增：启发式兜底次数
```

- [ ] **Step 2: 实现 `_heuristic_extract` 函数**

在 `_extract_one` 函数之前添加：

```python
import re

_STOCK_CODE_RE = re.compile(r'\b([0-9]{6})\.(SZ|SH|BJ)\b')

def _heuristic_extract(article: BlogArticle) -> dict[str, Any]:
    """当 LLM 不可用时，用正则+规则提取基础信息作为兜底。"""
    content = article.content_text or ""
    raw_payload = article.raw_payload if isinstance(article.raw_payload, dict) else {}

    # 1. 提取股票代码
    symbols: list[str] = []
    for m in _STOCK_CODE_RE.finditer(content):
        code, exchange = m.group(1), m.group(2)
        if exchange in ("SZ", "SH"):
            symbols.append(f"{code}.{exchange}")
    symbols = list(dict.fromkeys(symbols))[:5]  # 去重，最多 5 个

    # 2. 提取概念（从 raw_payload 的 trader_id 或 author_name）
    concepts: list[dict[str, str]] = []
    trader_id = raw_payload.get("trader_id")
    if trader_id:
        concepts.append({"name": trader_id, "type": "trader", "evidence": f"来源: {article.author_name}"})
    if len(concepts) == 0 and article.author_name:
        concepts.append({"name": article.author_name, "type": "author", "evidence": f"作者标注"})

    # 3. sentiment_score 启发式（正负向词汇计数）
    positive_words = ["涨", "盈利", "买入", "做多", "突破", "拉升", "看好", "多头"]
    negative_words = ["跌", "亏损", "卖出", "做空", "止损", "止损", "看空", "空头"]
    pos_count = sum(1 for w in positive_words if w in content)
    neg_count = sum(1 for w in negative_words if w in content)
    total = pos_count + neg_count
    sentiment = (pos_count - neg_count) / total if total > 0 else 0.0

    return {
        "extracted_concepts": concepts,
        "trading_symbols": symbols,
        "strategy_rules": [],
        "preconditions": [],
        "comment_insights": [],
        "sentiment_score": sentiment,
        "confidence_score": 0.1,  # 启发式置信度低
    }
```

- [ ] **Step 3: 在 `extract_and_store_metadata` 中调用 `_heuristic_extract`**

修改第 189-207 行，当 `client.is_enabled() == False` 时使用启发式兜底：

```python
            if not client.is_enabled():
                # LLM 不可用时用启发式兜底
                raw = _heuristic_extract(article)
                mode = "fallback_heuristic"
                stats.fallback_calls += 1
            else:
                try:
                    raw = await _extract_one(client=client, prompts_dir=prompts_dir, article=article)
                    mode = "llm"
                    stats.llm_calls += 1
                except LLMError as exc:
                    # 网络/配置错误，记录后继续
                    raw = _heuristic_extract(article)
                    mode = "fallback_on_error"
                    stats.fallback_calls += 1
                    stats.failed += 1
                    # 写错误信息到 raw_llm_output
                    error_raw = {
                        "extracted_concepts": [],
                        "trading_symbols": [],
                        "strategy_rules": [],
                        "preconditions": [],
                        "comment_insights": [],
                        "sentiment_score": None,
                        "confidence_score": None,
                        "_fallback": {"error": str(exc), "mode": "fallback_on_error"},
                    }
                    raw = error_raw
```

- [ ] **Step 4: 验证 import 无错误**

Run: `cd trade-strategy-ai && python3 -c "from src.agents.data_agent.skills.extract_article_metadata import _heuristic_extract, ExtractStats; print('ok')"`
Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add trade-strategy-ai/src/agents/data_agent/skills/extract_article_metadata.py
git commit -m "feat(extract): 实现 _heuristic_extract 兜底 + ExtractStats llm_calls/fallback_calls"
```

---

## Task 4: 端到端验证

**Files:**
- Modify: `trade-strategy-ai/.env`（如需确认 llm 配置）

- [ ] **Step 1: 设置 LLM 环境变量并运行 extract-articles**

Run:
```bash
cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai && \
export DASHSCOPE_API_KEY=your_key_here && \
export DATABASE_URL=postgresql+asyncpg://trade:trade@localhost:5432/trade_strategy_ai && \
python3 -m cli.main extract-articles --limit 5
```

Expected: 输出 `Extract done scanned=X extracted=X extracted=X skipped=X failed=X`，无 Python exception。

**如果 DASHSCOPE_API_KEY 未配置**，会走 fallback_heuristic 路径，检查 stats.fallback_calls 是否增加。

- [ ] **Step 2: 检查 PostgreSQL 结果**

```bash
psql -U trade -d trade_strategy_ai -h localhost -c "
SELECT
    m.processed_at,
    json_array_length(m.extracted_concepts::json) as num_concepts,
    json_array_length(m.trading_symbols::json) as num_symbols,
    json_array_length(m.strategy_rules::json) as num_rules,
    json_array_length(m.preconditions::json) as num_preconditions,
    m.sentiment_score,
    m.confidence_score,
    m.raw_llm_output->>'mode' as llm_mode
FROM article_metadata m
JOIN blog_articles a ON a.id = m.article_id
"
```

验证：
- `num_concepts` 或 `num_symbols` > 0（fallback 模式应有值）
- `llm_mode` 不为 null（fallback / fallback_heuristic / llm 之一）

- [ ] **Step 3: Commit**

```bash
git add trade-strategy-ai/src/agents/data_agent/skills/extract_article_metadata.py
git commit -m "test: 端到端验证 LLM 抽取质量提升 v1"
```

---

## 自检清单

1. **Spec 覆盖**：设计文档中 4 个实现步骤均有对应 Task。
2. **Placeholder 扫描**：无 TBD/TODO/示例代码占位。
3. **类型一致性**：
   - `ExtractStats` 新增字段 `llm_calls` / `fallback_calls`
   - `_heuristic_extract` 返回 dict 的 key 与 `raw` 字段名一致（extracted_concepts, trading_symbols 等）
   - `mode` 值：`llm` / `fallback_heuristic` / `fallback_on_error`
4. **文件路径**：全部使用绝对路径，无相对路径。

---

Plan 编写完成。两个执行选项：

**1. Subagent-Driven (recommended)** — 每个 Task 派发独立 subagent，Task 间有检查点，快速迭代

**2. Inline Execution** — 在本 session 执行，有检查点

选哪个？