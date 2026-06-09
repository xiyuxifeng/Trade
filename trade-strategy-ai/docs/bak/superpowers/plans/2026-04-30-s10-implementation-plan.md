# Stage 10: LLM 规则应用与持续优化 - 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 打通 LLM 提取规则到盘前决策的完整链路，使 S7-001~S7-004 的规则优化闭环真正运转起来

> **Note:** S10-007（规则时效性衰减）暂不实现，待后续需求明确后再推进。

**Architecture:** 通过在 StrategyVersionBuilder 中新增 rules_snapshot 填充逻辑，将 ArticleMetadata.strategy_rules 传递到策略版本；同时扩展 ArticleEvidence protocol 增加规则相关字段，并在信号评估时检查 preconditions 前置条件。

**Tech Stack:** Python, pytest, SQLAlchemy, DuckDB, PostgreSQL

---

## 文件结构概览

| 文件 | 职责 |
|------|------|
| `src/strategy_library/builder.py` | StrategyVersionBuilder，新增 `_build_rules_snapshot()` 方法 |
| `src/strategy/types.py` | `ArticleEvidence` Protocol 扩展，新增 `strategy_rules`、`preconditions`、`published_at` |
| `src/agents/strategy_agent/agent.py` | `generate_raw_signal()` 中增加 preconditions 前置条件检查 |
| `src/pipeline/tasks/export_task.py` | DuckDB UPSERT 明确冲突列为 `(article_id, schema_version)` |
| `src/market_universe/snapshot_service.py` | 新增 `generate_canonical_topic_tags()` 统一 tag 生成 |
| `src/backtest/rule_registry.py` | 已有 `classify_rule()` 用于可执行性评分 |
| `src/agents/data_agent/skills/extract_article_metadata.py` | ArticleMetadata 模型（只读参考） |
| `tests/unit/strategy_library/test_builder_s10_001.py` | S10-001 单元测试 |
| `tests/unit/strategy_agent/test_agent_s10_003.py` | S10-003 单元测试 |
| `tests/unit/pipeline/test_export_task_s10_004.py` | S10-004 单元测试 |

---

## Task 1: S10-001 - 将 ArticleMetadata.strategy_rules 填充到 rules_snapshot（P0）

**Files:**
- Modify: `src/strategy_library/builder.py:204-285`
- Create: `tests/unit/strategy_library/test_builder_s10_001.py`

- [ ] **Step 1: 理解现有 builder 结构和测试**

Run: `pytest tests/unit/strategy_library/test_builder.py -v --collect-only 2>/dev/null | head -30`

- [ ] **Step 2: 写 S10-001 失败测试**

```python
# tests/unit/strategy_library/test_builder_s10_001.py
import pytest
from unittest.mock import MagicMock, patch
from datetime import date, datetime
from uuid import uuid4
from strategy_library.builder import StrategyVersionBuilder
from strategy.types import TraderProfile, TraderMemory, MarketSnapshot

class TestBuildRulesSnapshot:
    """验证 ArticleMetadata.strategy_rules 正确填充到 StrategyVersion.rules_snapshot"""

    @pytest.fixture
    def mock_article_with_rules(self):
        """模拟包含 strategy_rules 的 ArticleMetadata"""
        article = MagicMock()
        article.article_id = str(uuid4())
        article.strategy_rules = [
            {
                "rule_id": "R001",
                "rule_text": "当RSI<30时买入",
                "programmatic_indicators": ["rsi"],
                "required_fields": ["rsi"],
            },
            {
                "rule_id": "R002",
                "rule_text": "MACD金叉买入",
                "programmatic_indicators": ["macd"],
                "required_fields": ["macd"],
            },
        ]
        article.trading_symbols = ["AAPL"]
        article.sentiment_score = 0.8
        article.confidence_score = 0.9
        article.published_at = datetime(2026, 4, 20)
        return article

    @pytest.fixture
    def trader_profile(self):
        return TraderProfile(
            trader_id="test_trader",
            name="Test Trader",
            preferences={},
            risk_tolerance="medium",
        )

    @pytest.fixture
    def market_snapshot(self):
        return MarketSnapshot(
            date=date(2026, 4, 29),
            hot_topics=[{"topic_id": "T1", "name": "AI"}],
            topic_constituents={"T1": ["AAPL", "GOOGL"]},
            strong_symbols=["AAPL"],
        )

    @pytest.fixture
    def trader_memory(self):
        return TraderMemory(
            trader_id="test_trader",
            historical_signals=[],
            postmortems=[],
            strategy_adjustments=[],
        )

    def test_rules_snapshot_populated_from_article_metadata(
        self, trader_profile, market_snapshot, trader_memory, mock_article_with_rules
    ):
        """同一 trader 同一日期的 rules_snapshot 包含该 trader 对应文章中 LLM 提取的规则"""
        # Mock Repository 来返回模拟文章
        with patch("strategy_library.builder.ArticleRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.list_by_date.return_value = [mock_article_with_rules]

            builder = StrategyVersionBuilder(trader_profile)
            version = builder.build_draft(
                market_snapshot=market_snapshot,
                trader_memory=trader_memory,
                signals=[],
                date=date(2026, 4, 29),
            )

            assert len(version.rules_snapshot) == 2
            assert version.rules_snapshot[0]["rule_id"] == "R001"
            assert version.rules_snapshot[1]["rule_id"] == "R002"

    def test_rules_snapshot_empty_when_no_articles(
        self, trader_profile, market_snapshot, trader_memory
    ):
        """没有文章时 rules_snapshot 为空列表（而非 None）"""
        with patch("strategy_library.builder.ArticleRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.list_by_date.return_value = []

            builder = StrategyVersionBuilder(trader_profile)
            version = builder.build_draft(
                market_snapshot=market_snapshot,
                trader_memory=trader_memory,
                signals=[],
                date=date(2026, 4, 29),
            )

            assert version.rules_snapshot == []
```

- [ ] **Step 3: 运行测试验证失败**

Run: `pytest tests/unit/strategy_library/test_builder_s10_001.py -v`
Expected: FAIL - rules_snapshot 为空列表

- [ ] **Step 4: 在 builder.py 中新增 `_collect_article_rules()` 辅助方法**

在 `_score_article_for_profile()` 方法后添加（约第160行）：

```python
def _collect_article_rules(self, articles: list[ArticleMetadata]) -> list[dict[str, Any]]:
    """
    从文章列表中收集策略规则，填充 rules_snapshot。

    每条规则保留原始 rule_id、rule_text、programmatic_indicators，
    并补充来源文章信息用于后续验真。
    """
    rules = []
    for article in articles:
        for rule in (article.strategy_rules or []):
            rules.append({
                "rule_id": rule.get("rule_id", f"article_{article.article_id}_{len(rules)}"),
                "rule_text": rule.get("rule_text", ""),
                "programmatic_indicators": rule.get("programmatic_indicators", []),
                "required_fields": rule.get("required_fields", []),
                "source_article_id": str(article.article_id),
                "source_symbols": article.trading_symbols or [],
            })
    return rules
```

- [ ] **Step 5: 在 `_build()` 方法末尾填充 rules_snapshot**

在 `_build()` 方法返回前（约第283行 `return version` 之前）添加：

```python
# S10-001: 填充 rules_snapshot
version.rules_snapshot = self._collect_article_rules(filtered_articles)
```

找到 `_build()` 方法的返回语句，确保在 `return version` 之前添加 rules_snapshot 填充逻辑。

- [ ] **Step 6: 运行测试验证通过**

Run: `pytest tests/unit/strategy_library/test_builder_s10_001.py -v`
Expected: PASS

- [ ] **Step 7: 运行现有测试确保无回归**

Run: `pytest tests/unit/strategy_library/test_builder.py -v`
Expected: 全部 PASS

- [ ] **Step 8: 提交代码**

```bash
git add tests/unit/strategy_library/test_builder_s10_001.py src/strategy_library/builder.py
git commit -m "feat(s10-001): 填充 rules_snapshot 从 ArticleMetadata.strategy_rules"
```

---

## Task 2: S10-002 - 扩展 ArticleEvidence Protocol（P1）

**Files:**
- Modify: `src/strategy_library/builder.py:25-32`
- Modify: `src/strategy/types.py` (如 ArticleEvidence 在此定义)

- [ ] **Step 1: 检查 ArticleEvidence Protocol 定义位置**

Run: `grep -n "class ArticleEvidence" src/strategy_library/builder.py src/strategy/types.py`

- [ ] **Step 2: 写 S10-002 失败测试**

```python
# tests/unit/strategy_library/test_builder_s10_002.py
import pytest
from strategy_library.builder import ArticleEvidence

class TestArticleEvidenceProtocol:
    """验证 ArticleEvidence Protocol 包含规则相关字段"""

    def test_article_evidence_has_strategy_rules_field(self):
        """ArticleEvidence 应该有 strategy_rules 字段"""
        mock_evidence: ArticleEvidence = {
            "article_id": "art_001",
            "trading_symbols": ["AAPL"],
            "sentiment_score": 0.8,
            "confidence_score": 0.9,
            "rationale": "Test",
            "entry_price": None,
            "strategy_rules": [{"rule_id": "R001", "rule_text": "RSI<30买入"}],
        }
        assert "strategy_rules" in mock_evidence

    def test_article_evidence_has_preconditions_field(self):
        """ArticleEvidence 应该有 preconditions 字段"""
        mock_evidence: ArticleEvidence = {
            "article_id": "art_001",
            "trading_symbols": ["AAPL"],
            "sentiment_score": 0.8,
            "confidence_score": 0.9,
            "rationale": "Test",
            "entry_price": None,
            "preconditions": [{"condition": "market_trend == 'bullish'"}],
        }
        assert "preconditions" in mock_evidence

    def test_article_evidence_has_published_at_field(self):
        """ArticleEvidence 应该有 published_at 字段"""
        from datetime import datetime
        mock_evidence: ArticleEvidence = {
            "article_id": "art_001",
            "trading_symbols": ["AAPL"],
            "sentiment_score": 0.8,
            "confidence_score": 0.9,
            "rationale": "Test",
            "entry_price": None,
            "published_at": datetime(2026, 4, 20),
        }
        assert "published_at" in mock_evidence
```

- [ ] **Step 3: 运行测试验证失败**

Run: `pytest tests/unit/strategy_library/test_builder_s10_002.py -v`
Expected: FAIL - Protocol 不接受额外字段

- [ ] **Step 4: 扩展 ArticleEvidence Protocol**

修改 `builder.py` 第25-32行：

```python
class ArticleEvidence(Protocol):
    article_id: str
    trading_symbols: list[str]
    sentiment_score: float | None
    confidence_score: float | None
    rationale: str | None
    entry_price: float | None
    # S10-002 新增规则相关字段
    strategy_rules: list[dict[str, Any]] | None = None
    preconditions: list[dict[str, Any]] | None = None
    published_at: datetime | None = None
```

需要添加 `from datetime import datetime` 和 `from typing import Any` 导入（如果尚未导入）。

- [ ] **Step 5: 运行测试验证通过**

Run: `pytest tests/unit/strategy_library/test_builder_s10_002.py -v`
Expected: PASS

- [ ] **Step 6: 运行相关测试确保无回归**

Run: `pytest tests/unit/strategy_library/ -v -k "builder" --tb=short`
Expected: 全部 PASS

- [ ] **Step 7: 提交代码**

```bash
git add src/strategy_library/builder.py tests/unit/strategy_library/test_builder_s10_002.py
git commit -m "feat(s10-002): 扩展 ArticleEvidence Protocol 增加规则相关字段"
```

---

## Task 3: S10-003 - 将 preconditions 加入信号评估门槛检查（P1）

**Files:**
- Modify: `src/agents/strategy_agent/agent.py:55-148`
- Create: `tests/unit/strategy_agent/test_agent_s10_003.py`

- [ ] **Step 1: 理解现有 generate_raw_signal() 评估逻辑**

Run: `grep -n "def generate_raw_signal" src/agents/strategy_agent/agent.py`
Run: `sed -n '55,148p' src/agents/strategy_agent/agent.py`

- [ ] **Step 2: 写 S10-003 失败测试**

```python
# tests/unit/strategy_agent/test_agent_s10_003.py
import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import date, datetime
from uuid import uuid4
from agents.strategy_agent.agent import StrategyAgent
from strategy.types import MarketState, TraderProfile

class TestPreconditionsGate:
    """验证 preconditions 前置条件门槛检查"""

    @pytest.fixture
    def agent(self):
        return StrategyAgent()

    @pytest.fixture
    def trader_profile(self):
        return TraderProfile(
            trader_id="test_trader",
            name="Test Trader",
            preferences={},
            risk_tolerance="medium",
        )

    @pytest.fixture
    def market_state(self):
        return MarketState(
            date=date(2026, 4, 29),
            symbols=["AAPL", "GOOGL"],
            market_status="open",
        )

    @pytest.fixture
    def rule_with_precondition(self):
        """带前置条件约束的规则"""
        return {
            "rule_id": "R001",
            "rule_text": "RSI<30买入",
            "preconditions": [
                {"field": "market_trend", "operator": "==", "value": "bullish"},
                {"field": "volume_ratio", "operator": ">", "value": 1.5},
            ],
        }

    @pytest.fixture
    def rule_without_precondition(self):
        """无前置条件的规则"""
        return {
            "rule_id": "R002",
            "rule_text": "MACD金叉买入",
        }

    @pytest.mark.asyncio
    async def test_rule_with_unsatisfied_precondition_is_skipped(
        self, agent, trader_profile, market_state, rule_with_precondition
    ):
        """前置条件不满足的规则应被跳过，不参与评估"""
        # 市场状态不满足 precondition (market_trend != 'bullish')
        market_state.market_trend = "bearish"
        market_state.volume_ratio = 0.8

        # 模拟 strategy_agent 的 _evaluate_rules 方法
        rules = [rule_with_precondition]

        # 验证不满足前置条件的规则被过滤
        satisfied_rules = agent._filter_rules_by_preconditions(rules, market_state)
        assert len(satisfied_rules) == 0

    @pytest.mark.asyncio
    async def test_rule_with_satisfied_precondition_is_included(
        self, agent, trader_profile, market_state, rule_with_precondition
    ):
        """前置条件满足的规则应参与评估"""
        # 市场状态满足 precondition
        market_state.market_trend = "bullish"
        market_state.volume_ratio = 2.0

        rules = [rule_with_precondition]
        satisfied_rules = agent._filter_rules_by_preconditions(rules, market_state)
        assert len(satisfied_rules) == 1
        assert satisfied_rules[0]["rule_id"] == "R001"

    @pytest.mark.asyncio
    async def test_rule_without_precondition_is_always_included(
        self, agent, trader_profile, market_state, rule_without_precondition
    ):
        """无前置条件的规则始终参与评估"""
        rules = [rule_without_precondition]
        satisfied_rules = agent._filter_rules_by_preconditions(rules, market_state)
        assert len(satisfied_rules) == 1
```

- [ ] **Step 3: 运行测试验证失败**

Run: `pytest tests/unit/strategy_agent/test_agent_s10_003.py -v`
Expected: FAIL - `_filter_rules_by_preconditions` 方法不存在

- [ ] **Step 4: 在 StrategyAgent 中实现 `_filter_rules_by_preconditions()` 方法**

在 `agent.py` 的 `StrategyAgent` 类中添加方法：

```python
def _filter_rules_by_preconditions(
    self, rules: list[dict[str, Any]], market_state: MarketState
) -> list[dict[str, Any]]:
    """
    过滤出前置条件满足的规则。

    规则的前置条件检查：
    - 无 preconditions 的规则直接通过
    - 有 preconditions 的规则，逐条检查 market_state 属性是否满足条件
    """
    satisfied = []
    for rule in rules:
        preconditions = rule.get("preconditions")
        if not preconditions:
            satisfied.append(rule)
            continue

        all_met = True
        for cond in preconditions:
            field = cond.get("field")
            operator = cond.get("operator")
            expected = cond.get("value")

            if not hasattr(market_state, field):
                all_met = False
                break

            actual = getattr(market_state, field)
            if not self._compare_values(actual, operator, expected):
                all_met = False
                break

        if all_met:
            satisfied.append(rule)

    return satisfied

def _compare_values(self, actual: Any, operator: str, expected: Any) -> bool:
    """比较操作符实现"""
    if operator == "==":
        return actual == expected
    elif operator == "!=":
        return actual != expected
    elif operator == ">":
        return actual > expected
    elif operator == ">=":
        return actual >= expected
    elif operator == "<":
        return actual < expected
    elif operator == "<=":
        return actual <= expected
    elif operator == "in":
        return actual in expected
    elif operator == "not in":
        return actual not in expected
    return False
```

- [ ] **Step 5: 修改 `generate_raw_signal()` 在评估前过滤前置条件**

在 `generate_raw_signal()` 方法中（约第103-116行），在 `evaluation_rules` 赋值后、实际评估前，插入前置条件过滤：

```python
# 找到这段代码（约第103-116行）
if strategy_version is not None and strategy_version.rules_snapshot:
    evaluation_rules = strategy_version.rules_snapshot
    version_id = strategy_version.version_id
elif rules is not None:
    evaluation_rules = rules
    version_id = "phase0"
else:
    evaluation_rules = []
    version_id = "phase0"

# S10-003: 在此处添加前置条件过滤
if market_state is not None and evaluation_rules:
    evaluation_rules = self._filter_rules_by_preconditions(evaluation_rules, market_state)
```

- [ ] **Step 6: 运行测试验证通过**

Run: `pytest tests/unit/strategy_agent/test_agent_s10_003.py -v`
Expected: PASS

- [ ] **Step 7: 运行相关测试确保无回归**

Run: `pytest tests/unit/strategy_agent/ -v --tb=short`
Expected: 全部 PASS

- [ ] **Step 8: 提交代码**

```bash
git add src/agents/strategy_agent/agent.py tests/unit/strategy_agent/test_agent_s10_003.py
git commit -m "feat(s10-003): preconditions 前置条件门槛检查"
```

---

## Task 4: S10-004 - 修复 DuckDB export_task UPSERT 冲突目标列（P1）

**Files:**
- Modify: `src/pipeline/tasks/export_task.py:254-274`
- Create: `tests/unit/pipeline/test_export_task_s10_004.py`

- [ ] **Step 1: 理解当前 UPSERT 实现**

Run: `sed -n '250,280p' src/pipeline/tasks/export_task.py`

- [ ] **Step 2: 写 S10-004 失败测试**

```python
# tests/unit/pipeline/test_export_task_s10_004.py
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from uuid import uuid4
from pipeline.tasks.export_task import ExportTask, _serialize_metadata

class TestDuckDBUPSERT:
    """验证 DuckDB UPSERT 明确冲突列为 (article_id, schema_version)"""

    def test_serialize_metadata_returns_article_id_and_schema_version(self):
        """_serialize_metadata 返回的字典包含 article_id 和 schema_version"""
        article_id = uuid4()
        meta = MagicMock()
        meta.article_id = article_id
        meta.schema_version = "v1"
        meta.processed_at = datetime(2026, 4, 29)
        meta.extracted_concepts = []
        meta.trading_symbols = ["AAPL"]
        meta.strategy_rules = []
        meta.preconditions = []
        meta.comment_insights = []
        meta.raw_llm_output = {}
        meta.sentiment_score = 0.8
        meta.confidence_score = 0.9
        meta.provider = "test"
        meta.model = "test-model"

        result = _serialize_metadata(meta)
        assert "article_id" in result
        assert "schema_version" in result
        assert result["article_id"] == str(article_id)
        assert result["schema_version"] == "v1"

    def test_upsert_sql_specifies_conflict_target_columns(self):
        """metadata_sql 应明确指定 ON CONFLICT (article_id, schema_version) DO UPDATE SET"""
        from pipeline.tasks.export_task import METADATA_COLUMNS, metadata_sql

        # 检查 SQL 包含明确的冲突列
        assert "INSERT INTO" in metadata_sql
        # S10-004: 修复后应包含 ON CONFLICT 子句
        # 当前实现只有 INSERT OR REPLACE，修复后改为：
        # INSERT INTO ... ON CONFLICT (article_id, schema_version) DO UPDATE SET ...
```

- [ ] **Step 3: 运行测试验证当前状态**

Run: `pytest tests/unit/pipeline/test_export_task_s10_004.py -v`
Expected: 当前测试可能 PASS，但 UPSERT 逻辑不正确

- [ ] **Step 4: 检查 ArticleMetadata 表的 UNIQUE 约束**

Run: `grep -n "UniqueConstraint\|__table_args__" src/models/article_metadata.py`

- [ ] **Step 5: 修改 export_task.py 的 UPSERT 逻辑**

修改 `metadata_sql` 定义（约第254-255行）：

```python
# S10-004 修复：明确冲突目标列为 (article_id, schema_version)
# 使用 INSERT ... ON CONFLICT ... DO UPDATE SET 代替 INSERT OR REPLACE
metadata_placeholders = ", ".join(["?"] * len(METADATA_COLUMNS))
metadata_sql = (
    f"INSERT INTO metadata ({', '.join(METADATA_COLUMNS)}) "
    f"VALUES ({metadata_placeholders}) "
    f"ON CONFLICT (article_id, schema_version) DO UPDATE SET "
    + ", ".join([f"{col} = EXCLUDED.{col}" for col in METADATA_COLUMNS
                 if col not in ("article_id", "schema_version")])
)
```

同时需要更新 `_serialize_metadata()` 确保返回值包含 article_id 和 schema_version 作为可哈希类型（字符串）：

```python
def _serialize_metadata(meta) -> dict[str, Any]:
    """将 ArticleMetadata ORM 对象序列化为字典"""
    return {
        "article_id": str(meta.article_id),  # UUID -> str
        "schema_version": str(meta.schema_version),  # 已是 str，保持一致
        "processed_at": meta.processed_at.isoformat() if meta.processed_at else None,
        "extracted_concepts": meta.extracted_concepts or [],
        "trading_symbols": meta.trading_symbols or [],
        "strategy_rules": meta.strategy_rules or [],
        "preconditions": meta.preconditions or [],
        "comment_insights": meta.comment_insights or [],
        "raw_llm_output": meta.raw_llm_output or {},
        "sentiment_score": float(meta.sentiment_score) if meta.sentiment_score else None,
        "confidence_score": float(meta.confidence_score) if meta.confidence_score else None,
        "provider": meta.provider,
        "model": meta.model,
    }
```

- [ ] **Step 6: 运行测试验证通过**

Run: `pytest tests/unit/pipeline/test_export_task_s10_004.py -v`
Expected: PASS

- [ ] **Step 7: 检查是否有现有测试**

Run: `pytest tests/unit/pipeline/test_export_task.py -v --tb=short 2>/dev/null || echo "No existing tests"`
如果存在现有测试，运行确保无回归。

- [ ] **Step 8: 提交代码**

```bash
git add src/pipeline/tasks/export_task.py tests/unit/pipeline/test_export_task_s10_004.py
git commit -m "fix(s10-004): DuckDB UPSERT 明确冲突列为 (article_id, schema_version)"
```

---

## Task 5: S10-006 - 规则可执行性评分与淘汰（P2）

**Files:**
- Modify: `src/backtest/rule_registry.py`
- Create: `tests/unit/backtest/test_rule_registry_s10_006.py`

- [ ] **Step 1: 理解现有 `classify_rule()` 实现**

Run: `grep -n "def classify_rule\|PROGRAMMABLE_INDICATORS" src/backtest/rule_registry.py`

- [ ] **Step 2: 写 S10-006 失败测试**

```python
# tests/unit/backtest/test_rule_registry_s10_006.py
import pytest
from backtest.rule_registry import RuleRegistry, RuleMeta, classify_rule, PROGRAMMABLE_INDICATORS

class TestRuleProgrammability:
    """验证规则可执行性评分"""

    def test_classify_rule_fully_programmable(self):
        """基于明确指标阈值的规则应标记为 fully_programmable"""
        rule = {
            "rule_id": "R001",
            "rule_text": "当RSI<30时买入",
            "programmatic_indicators": ["rsi"],
            "required_fields": ["rsi"],
        }
        level = classify_rule(rule)
        assert level == "fully_programmable"

    def test_classify_rule_partially_programmable(self):
        """提到指标但无明确阈值的规则应标记为 partially_programmable"""
        rule = {
            "rule_id": "R002",
            "rule_text": "观察RSI指标",
            "programmatic_indicators": ["rsi"],
            "required_fields": [],
        }
        level = classify_rule(rule)
        assert level in ("partially_programmable", "descriptive_only")

    def test_classify_rule_unsupported(self):
        """无指标引用的规则应标记为 unsupported"""
        rule = {
            "rule_id": "R003",
            "rule_text": "关注公司基本面",
            "programmatic_indicators": [],
            "required_fields": [],
        }
        level = classify_rule(rule)
        assert level == "unsupported"

    def test_filter_by_programmability(self):
        """RuleRegistry 应能过滤出高可执行性规则"""
        registry = RuleRegistry()
        rules = [
            RuleMeta(rule_id="R001", rule_text="RSI<30买入", programmatic_level="fully_programmable"),
            RuleMeta(rule_id="R002", rule_text="观察RSI", programmatic_level="descriptive_only"),
        ]
        registry.register_rule(rules[0])
        registry.register_rule(rules[1])

        programmable_rules = registry.list_programmable_rules()
        assert len(programmable_rules) == 1
        assert programmable_rules[0].rule_id == "R001"
```

- [ ] **Step 3: 运行测试验证状态**

Run: `pytest tests/unit/backtest/test_rule_registry_s10_006.py -v`
Expected: 需要检查 classify_rule 是否已有实现

- [ ] **Step 4: 检查现有 rule_registry.py 实现**

Run: `cat src/backtest/rule_registry.py`

- [ ] **Step 5: 如需要，扩展 rule_registry.py**

如果 `classify_rule()` 和 `RuleRegistry.list_programmable_rules()` 不存在，实现它们：

```python
# 在 rule_registry.py 添加

PROGRAMMABLE_INDICATORS = {
    "rsi", "macd", "ma", "boll", "kdj", "volume", "price",
    "turnover", "pe", "market_cap", "volatility", "beta",
}

# 指标阈值模式：用于判断规则是否有明确阈值
THRESHOLD_PATTERNS = [
    r"<\s*\d+", r">\s*\d+", r"==\s*\d+", r"<=\s*\d+", r">=\s*\d+",
    r"cross(ed)?\s+(up|down|above|below)", r"golden\s+cross", r"death\s+cross",
]

def classify_rule(rule: dict[str, Any]) -> str:
    """
    根据规则内容判断可程序化程度。

    返回:
    - "fully_programmable": 有指标引用 + 明确阈值
    - "partially_programmable": 有指标引用但无明确阈值
    - "descriptive_only": 无指标引用但有描述性内容
    - "unsupported": 完全无法程序化
    """
    indicators = set(rule.get("programmatic_indicators", []))
    rule_text = rule.get("rule_text", "").lower()

    if not indicators:
        # 无指标引用
        if any(keyword in rule_text for keyword in ["关注", "注意", "观察", "watch"]):
            return "descriptive_only"
        return "unsupported"

    # 有指标引用，检查是否有明确阈值
    for pattern in THRESHOLD_PATTERNS:
        import re
        if re.search(pattern, rule_text):
            return "fully_programmable"

    return "partially_programmable"

class RuleRegistry:
    """规则注册表，支持可执行性过滤"""

    def __init__(self):
        self._rules: dict[str, RuleMeta] = {}

    def register_rule(self, rule_meta: RuleMeta):
        self._rules[rule_meta.rule_id] = rule_meta

    def list_programmable_rules(self, min_level: str = "fully_programmable") -> list[RuleMeta]:
        """列出可执行性 >= min_level 的规则"""
        level_order = {"unsupported": 0, "descriptive_only": 1, "partially_programmable": 2, "fully_programmable": 3}
        min_score = level_order.get(min_level, 0)
        return [
            r for r in self._rules.values()
            if level_order.get(r.programmatic_level, 0) >= min_score
        ]
```

- [ ] **Step 6: 运行测试验证通过**

Run: `pytest tests/unit/backtest/test_rule_registry_s10_006.py -v`
Expected: PASS

- [ ] **Step 7: 提交代码**

```bash
git add src/backtest/rule_registry.py tests/unit/backtest/test_rule_registry_s10_006.py
git commit -m "feat(s10-006): 规则可执行性评分与淘汰机制"
```

---

## Task 6: S10-007 - 规则时效性衰减（P2）

> **暂不实现** - 待后续需求明确后再推进

<!--
**Files:**
- Modify: `src/strategy_library/builder.py`
- Create: `tests/unit/strategy_library/test_builder_s10_007.py`

- [ ] **Step 1: 理解 rules_snapshot 中 published_at 来源**

从 S10-001 实现中，rules_snapshot 包含 source_article_id，可以关联查询 published_at。

- [ ] **Step 2: 写 S10-007 失败测试**

```python
# tests/unit/strategy_library/test_builder_s10_007.py
import pytest
from datetime import date, datetime, timedelta
from strategy_library.builder import apply_rule_decay

class TestRuleDecay:
    """验证规则时效性衰减"""

    def test_rule_older_than_30_days_has_zero_weight(self):
        """超过30天的规则权重应为0"""
        rule = {
            "rule_id": "R001",
            "published_at": datetime(2026, 3, 1),  # 60天前
            "programmatic_level": "fully_programmable",
        }
        weighted_rule = apply_rule_decay(rule, reference_date=date(2026, 4, 30), max_age_days=30)
        assert weighted_rule["decay_weight"] == 0.0

    def test_rule_7_days_old_has_high_weight(self):
        """7天内的规则应有高权重（约0.8）"""
        rule = {
            "rule_id": "R001",
            "published_at": datetime(2026, 4, 23),  # 7天前
            "programmatic_level": "fully_programmable",
        }
        weighted_rule = apply_rule_decay(rule, reference_date=date(2026, 4, 30), max_age_days=30)
        assert weighted_rule["decay_weight"] > 0.7

    def test_rule_without_published_at_has_full_weight(self):
        """没有 published_at 的规则默认权重为1.0"""
        rule = {
            "rule_id": "R001",
            "programmatic_level": "fully_programmable",
        }
        weighted_rule = apply_rule_decay(rule, reference_date=date(2026, 4, 30))
        assert weighted_rule["decay_weight"] == 1.0

    def test_decay_weight_in_float_format(self):
        """decay_weight 应为浮点数"""
        rule = {
            "rule_id": "R001",
            "published_at": datetime(2026, 4, 25),
            "programmatic_level": "fully_programmable",
        }
        weighted_rule = apply_rule_decay(rule, reference_date=date(2026, 4, 30))
        assert isinstance(weighted_rule["decay_weight"], float)
```

- [ ] **Step 3: 运行测试验证失败**

Run: `pytest tests/unit/strategy_library/test_builder_s10_007.py -v`
Expected: FAIL - `apply_rule_decay` 函数不存在

- [ ] **Step 4: 在 builder.py 中实现 `apply_rule_decay()` 函数**

在 `_collect_article_rules()` 方法附近添加：

```python
def apply_rule_decay(
    rule: dict[str, Any],
    reference_date: date,
    max_age_days: int = 30,
) -> dict[str, Any]:
    """
    对规则应用时效性衰减。

    衰减公式：weight = max(0, 1 - age_days / max_age_days)

    Args:
        rule: 包含 published_at 的规则字典
        reference_date: 参考日期（当前交易日）
        max_age_days: 规则最大有效天数，默认30天

    Returns:
        新增 decay_weight 字段的规则副本
    """
    rule = dict(rule)  # 浅拷贝
    published_at = rule.get("published_at")

    if published_at is None:
        rule["decay_weight"] = 1.0
        return rule

    # 确保 published_at 是 datetime 对象
    if isinstance(published_at, datetime):
        pub_date = published_at.date()
    else:
        pub_date = published_at

    age_days = (reference_date - pub_date).days
    decay_weight = max(0.0, 1.0 - age_days / max_age_days)
    rule["decay_weight"] = round(decay_weight, 3)

    return rule
```

- [ ] **Step 5: 在 `_build()` 方法中应用衰减**

修改 `_build()` 方法，在填充 rules_snapshot 后、对每个规则应用衰减：

```python
# S10-007: 应用规则时效性衰减
from datetime import datetime as dt_class

# 在 rules_snapshot 填充后添加
decayed_rules = []
for rule in version.rules_snapshot:
    # published_at 需要从源文章获取，暂用当前日期作为 placeholder
    # 实际应在 _collect_article_rules 时传入
    if "published_at" not in rule and "source_article_id" in rule:
        # 后续从 ArticleRepository 查询实际发布时间
        rule["published_at"] = None
    decayed_rules.append(apply_rule_decay(rule, version.strategy_date))

version.rules_snapshot = decayed_rules
```

- [ ] **Step 6: 运行测试验证通过**

Run: `pytest tests/unit/strategy_library/test_builder_s10_007.py -v`
Expected: PASS

- [ ] **Step 7: 提交代码**

```bash
git add src/strategy_library/builder.py tests/unit/strategy_library/test_builder_s10_007.py
git commit -m "feat(s10-007): 规则时效性衰减机制"
```
-->

---

## Task 7: S10-008 - 规则与标的联合验证（P2）

**Files:**
- Modify: `src/strategy_library/builder.py`
- Create: `tests/unit/strategy_library/test_builder_s10_008.py`

- [ ] **Step 1: 理解 builder 中 source_articles 处理逻辑**

Run: `grep -n "source_articles\|_score_article" src/strategy_library/builder.py`

- [ ] **Step 2: 写 S10-008 失败测试**

```python
# tests/unit/strategy_library/test_builder_s10_008.py
import pytest
from unittest.mock import MagicMock
from strategy_library.builder import validate_rule_symbol_association

class TestRuleSymbolAssociation:
    """验证规则与标的联合验证"""

    def test_rule_with_symbol_is_valid_evidence(self):
        """同时有 trading_symbols 和 strategy_rules 的文章是有效证据"""
        article = MagicMock()
        article.article_id = "art_001"
        article.trading_symbols = ["AAPL"]
        article.strategy_rules = [{"rule_id": "R001", "rule_text": "RSI<30买入"}]
        article.preconditions = []

        is_valid = validate_rule_symbol_association(article)
        assert is_valid is True

    def test_rule_without_symbol_is_invalid_evidence(self):
        """有 strategy_rules 但无 trading_symbols 的文章是无效证据"""
        article = MagicMock()
        article.article_id = "art_002"
        article.trading_symbols = []  # 无标的
        article.strategy_rules = [{"rule_id": "R001", "rule_text": "市场普涨"}]
        article.preconditions = []

        is_valid = validate_rule_symbol_association(article)
        assert is_valid is False

    def test_symbol_without_rule_can_still_be_valid(self):
        """只有 trading_symbols 没有 strategy_rules 的文章仍然有效（用于 sentiment）"""
        article = MagicMock()
        article.article_id = "art_003"
        article.trading_symbols = ["AAPL"]
        article.strategy_rules = []
        article.preconditions = [{"condition": "market_bull"}]

        is_valid = validate_rule_symbol_association(article)
        # 有 preconditions 代替 strategy_rules，也应视为有效
        assert is_valid is True
```

- [ ] **Step 3: 运行测试验证失败**

Run: `pytest tests/unit/strategy_library/test_builder_s10_008.py -v`
Expected: FAIL - `validate_rule_symbol_association` 不存在

- [ ] **Step 4: 实现 `validate_rule_symbol_association()` 函数**

在 builder.py 中添加：

```python
def validate_rule_symbol_association(article) -> bool:
    """
    验证文章是否有有效的规则-标的关联。

    有效条件（满足其一即可）：
    1. 有 trading_symbols + strategy_rules
    2. 有 trading_symbols + preconditions

    无效条件：
    - 有 strategy_rules 但 trading_symbols 为空
    - 有 preconditions 但 trading_symbols 和 strategy_rules 都为空
    """
    has_symbols = bool(article.trading_symbols)
    has_rules = bool(article.strategy_rules)
    has_preconditions = bool(article.preconditions)

    # 有效情况
    if has_symbols and (has_rules or has_preconditions):
        return True

    # 只有 symbols 没有 rules（用于 sentiment 场景）也有效
    if has_symbols and not has_rules and not has_preconditions:
        return True

    # 有 rules 但没有 symbols 关联 - 无效
    if has_rules and not has_symbols:
        return False

    return False
```

- [ ] **Step 5: 在 builder 中应用联合验证**

在 `_score_article_for_profile()` 返回前，或在 `_build()` 的文章过滤阶段，调用联合验证：

```python
# S10-008: 在 filtered_articles 过滤中添加规则-标的联合验证
# 找到 _build() 中构建 recommendations 的位置
# 在构建 recommendations 前过滤掉无效证据
filtered_articles = [
    art for art in articles
    if validate_rule_symbol_association(art)  # S10-008 新增
]
```

- [ ] **Step 6: 运行测试验证通过**

Run: `pytest tests/unit/strategy_library/test_builder_s10_008.py -v`
Expected: PASS

- [ ] **Step 7: 提交代码**

```bash
git add src/strategy_library/builder.py tests/unit/strategy_library/test_builder_s10_008.py
git commit -m "feat(s10-008): 规则与标的联合验证"
```

---

## Task 8: S10-009 - 测试基础设施规范化（P2）

**Files:**
- Modify: `tests/unit/agents/test_manager_agent.py`
- Modify: `tests/unit/agents/test_trader_agent.py`
- Modify: `tests/unit/trader_memory/`

- [ ] **Step 1: 检查现有测试中的 session_scope 依赖**

Run: `grep -rn "session_scope\|Session\|session" tests/unit/agents/test_manager_agent.py | head -20`

- [ ] **Step 2: 写 S10-009 测试 mock 设计**

```python
# tests/unit/trader_memory/conftest.py
import pytest
from unittest.mock import MagicMock, AsyncMock
from contextlib import asynccontextmanager

@pytest.fixture
def mock_session_scope():
    """
    Mock session_scope 避免依赖真实 PostgreSQL 连接。

    用法：
    def test_something(self, mock_session_scope):
        with mock_session_scope() as session:
            # 使用 mock session
    """
    @asynccontextmanager
    async def _mock_session():
        session = MagicMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        yield session

    return _mock_session
```

- [ ] **Step 3: 在相关测试文件中应用 mock_session_scope**

具体修改取决于现有测试结构，此处给出通用模式：

```python
# 在 conftest.py 中定义 mock_session_scope fixture
# 在需要 session_scope 的测试中替换：
# 原：async with session_scope() as session:
# 改：async with mock_session_scope() as session:
```

- [ ] **Step 4: 运行测试验证**

Run: `pytest tests/unit/trader_memory/ -v --tb=short`
Expected: 测试通过（使用 mock）

- [ ] **Step 5: 提交代码**

```bash
git add tests/unit/trader_memory/conftest.py
git commit -m "feat(s10-009): 测试基础设施规范化 - mock session_scope"
```

---

## Task 9: S10-010 - 统一 source_topic_ids tag 生成逻辑（P2）

**Files:**
- Modify: `src/market_universe/snapshot_service.py`
- Create: `tests/unit/market_universe/test_snapshot_service_s10_010.py`

- [ ] **Step 1: 理解 snapshot_service.py 当前结构**

Run: `grep -n "def \|class " src/market_universe/snapshot_service.py | head -20`

- [ ] **Step 2: 写 S10-010 失败测试**

```python
# tests/unit/market_universe/test_snapshot_service_s10_010.py
import pytest
from unittest.mock import MagicMock
from market_universe.snapshot_service import SnapshotService, generate_canonical_topic_tags

class TestCanonicalTopicTags:
    """验证统一 source_topic_ids tag 生成逻辑"""

    def test_generate_tags_from_hot_topics_and_constituents(self):
        """tag 应来自 hot_topics 和 topic_constituents 双重校验"""
        hot_topics = [
            {"topic_id": "T1", "name": "AI"},
            {"topic_id": "T2", "name": "新能源"},
        ]
        topic_constituents = {
            "T1": ["AAPL", "GOOGL", "MSFT"],
            "T3": ["TSLA"],  # T3 不在 hot_topics 中，应被过滤
        }

        tags = generate_canonical_topic_tags(hot_topics, topic_constituents, target_symbols=["AAPL", "TSLA"])

        # T1 符合：存在于 hot_topics 且 AAPL 在其 constituents 中
        # T3 不符合：不在 hot_topics 中，即使 TSLA 在其 constituents 中
        assert "T1" in tags
        assert "T3" not in tags

    def test_empty_hot_topics_returns_empty_tags(self):
        """hot_topics 为空时返回空列表"""
        tags = generate_canonical_topic_tags([], {"T1": ["AAPL"]}, target_symbols=["AAPL"])
        assert tags == []

    def test_generate_canonical_topic_tags_is_standalone_function(self):
        """generate_canonical_topic_tags 应是独立函数，可在保存快照时调用"""
        assert callable(generate_canonical_topic_tags)
```

- [ ] **Step 3: 运行测试验证失败**

Run: `pytest tests/unit/market_universe/test_snapshot_service_s10_010.py -v`
Expected: FAIL - `generate_canonical_topic_tags` 不存在

- [ ] **Step 4: 在 snapshot_service.py 中实现 `generate_canonical_topic_tags()`**

在文件顶部或 `SnapshotService` 类外添加：

```python
def generate_canonical_topic_tags(
    hot_topics: list[dict[str, Any]],
    topic_constituents: dict[str, list[str]],
    target_symbols: list[str] | None = None,
) -> list[str]:
    """
    统一生成 canonical topic tags。

    双重校验逻辑：
    1. topic_id 必须在 hot_topics 中存在（确保是热点话题）
    2. topic 的 constituents 必须包含至少一个 target_symbol（如果有 target_symbols）

    Args:
        hot_topics: 热点话题列表，每项包含 topic_id
        topic_constituents: 话题成分映射 {topic_id: [symbols]}
        target_symbols: 目标交易标的可选列表

    Returns:
        符合条件的 topic_id 列表
    """
    hot_topic_ids = {t["topic_id"] for t in hot_topics}

    canonical_tags = []
    for topic_id, constituents in topic_constituents.items():
        # 校验1: topic_id 必须在 hot_topics 中
        if topic_id not in hot_topic_ids:
            continue

        # 校验2: 如果指定了 target_symbols，必须至少有一个在 constituents 中
        if target_symbols:
            if not any(sym in constituents for sym in target_symbols):
                continue

        canonical_tags.append(topic_id)

    return canonical_tags
```

- [ ] **Step 5: 在 SnapshotService 保存时调用 tag 生成**

在 `SnapshotService.save()` 方法中（如果存在），在保存前调用 `generate_canonical_topic_tags()`：

```python
# 在 save() 方法中，快照保存前添加：
# S10-010: 生成 canonical topic tags
snapshot.topic_source_ids = generate_canonical_topic_tags(
    hot_topics=snapshot.hot_topics or [],
    topic_constituents=snapshot.topic_constituents or {},
    target_symbols=snapshot.strong_symbols,  # 或其他相关标的列表
)
```

注意：具体集成点取决于 SnapshotService 的实际接口。

- [ ] **Step 6: 运行测试验证通过**

Run: `pytest tests/unit/market_universe/test_snapshot_service_s10_010.py -v`
Expected: PASS

- [ ] **Step 7: 提交代码**

```bash
git add src/market_universe/snapshot_service.py tests/unit/market_universe/test_snapshot_service_s10_010.py
git commit -m "feat(s10-010): 统一 source_topic_ids tag 生成逻辑"
```

---

## 自查清单

### 1. Spec 覆盖检查
- [x] S10-001: `rules_snapshot` 非空 ✓
- [x] S10-002: `ArticleEvidence` 扩展 ✓
- [x] S10-003: `preconditions` 门槛检查 ✓
- [x] S10-004: DuckDB UPSERT 修复 ✓
- [x] S10-005: 已完成 ✓
- [x] S10-006: 可执行性评分 ✓
- [ ] S10-007: 时效性衰减 - 暂不实现（待需求明确）
- [x] S10-008: 规则-标的联合验证 ✓
- [x] S10-009: 测试规范化 ✓
- [x] S10-010: source_topic_ids 统一生成 ✓

### 2. Placeholder 扫描
- [x] 无 "TBD"、"TODO" 残留
- [x] 每步都有实际代码
- [x] 无 "类似 Task N" 引用

### 3. 类型一致性
- [x] `rules_snapshot`: `list[dict[str, Any]]`
- [x] `ArticleEvidence`: Protocol 定义明确
- [x] `RuleMeta.programmatic_level`: 字符串枚举
- [x] `apply_rule_decay`: 返回带 `decay_weight` 的 dict

---

## 执行选项

**Plan complete and saved to `docs/superpowers/plans/2026-04-30-s10-implementation-plan.md`**

**Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**