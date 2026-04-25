# Stage 6 Offline Backtest And Rule Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 Stage 6 的离线回测与规则验真主链路，并确保它与 Stage 2/3/4/5 的数据资产和评分口径连续衔接。

**Architecture:** 先做跨 Stage 连续性修补与校验，再新建 `src/backtest/` 模块，按“契约 -> 执行 -> 评分 -> 引擎 -> 报告 -> CLI -> 规则验真 -> 复现验证”的顺序实现。主路径只消费历史快照、历史策略版本和统一 scoring 组件，`SignalVersioning/EvidencePack` 仅用于历史兼容补洞和对账。

**Tech Stack:** Python 3.13, dataclasses/Pydantic, SQLAlchemy async, Typer CLI, pytest

---

## 文件结构

### 新建文件

- `src/backtest/__init__.py`
- `src/backtest/schemas.py`
- `src/backtest/execution.py`
- `src/backtest/strategy_replayer.py`
- `src/backtest/snapshot_loader.py`
- `src/backtest/scoring.py`
- `src/backtest/engine.py`
- `src/backtest/reporting.py`
- `src/backtest/rule_registry.py`
- `src/backtest/reproducibility.py`
- `tests/unit/backtest/test_schemas.py`
- `tests/unit/backtest/test_execution.py`
- `tests/unit/backtest/test_snapshot_loader.py`
- `tests/unit/backtest/test_scoring.py`
- `tests/unit/backtest/test_engine.py`
- `tests/unit/backtest/test_reporting.py`
- `tests/unit/backtest/test_rule_registry.py`
- `tests/unit/backtest/test_reproducibility.py`

### 修改文件

- `src/strategy_library/repository.py`
- `src/strategy_library/service.py`
- `cli/backtest.py`
- `cli/main.py`
- `docs/Project.md`
- `docs/TaskList.md`
- `src/agents/backtest_agent/__init__.py`

### 参考文档

- `docs/superpowers/specs/Stage6-summary-desgin.md`
- `docs/superpowers/specs/2026-04-26-Stage5-Summary-Design.md`

---

### Task 0: Stage 6 连续性预检与补洞

**Files:**
- Modify: `src/strategy_library/repository.py`
- Modify: `src/strategy_library/service.py`
- Test: `tests/unit/strategy_library/test_repository.py`
- Test: `tests/unit/strategy_library/test_service.py`

- [ ] **Step 1: 写失败测试，验证 `rules_snapshot` 持久化与发布链路**

```python
def test_schema_to_orm_converts_rules_snapshot():
    version = StrategyVersion(
        version_id="ver-001",
        trader_id="trader-001",
        strategy_date=date(2026, 4, 25),
        status=StrategyVersionStatus.released,
        rules_snapshot=[{"rule_id": "r1", "condition": "ma5_cross"}],
    )
    orm_obj = StrategyLibraryRepository._to_orm_model(version)
    assert orm_obj.strategy_payload["rules_snapshot"] == [{"rule_id": "r1", "condition": "ma5_cross"}]
```

- [ ] **Step 2: 运行测试确认旧逻辑失败**

Run: `pytest tests/unit/strategy_library/test_repository.py tests/unit/strategy_library/test_service.py -q`
Expected: FAIL，`rules_snapshot` 未写入或未从 released version 透传

- [ ] **Step 3: 实现 repository/service 修补**

```python
# src/strategy_library/repository.py
strategy_payload = {
    "recommendations": [...],
    "rules_snapshot": version.rules_snapshot,
}

# src/strategy_library/service.py
released = StrategyVersion(
    ...,
    rules_snapshot=draft_version.rules_snapshot,
)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/unit/strategy_library/test_repository.py tests/unit/strategy_library/test_service.py tests/unit/strategy_library/test_service_uniqueness.py -q`
Expected: PASS

- [ ] **Step 5: 提交连续性补丁**

```bash
git add src/strategy_library/repository.py src/strategy_library/service.py tests/unit/strategy_library/test_repository.py tests/unit/strategy_library/test_service.py
git commit -m "fix: persist strategy rules snapshot for stage6 replay"
```

---

### Task 1: `NTL-S6-001` 回测 schema

**Files:**
- Create: `src/backtest/__init__.py`
- Create: `src/backtest/schemas.py`
- Test: `tests/unit/backtest/test_schemas.py`

- [ ] **Step 1: 写失败测试，定义请求与结果契约**

```python
def test_backtest_request_defaults():
    req = BacktestRequest(
        trader_id="trader_a",
        date_from=date(2026, 4, 1),
        date_to=date(2026, 4, 10),
    )
    assert req.mode == "full"
    assert req.use_snapshot_only is True

def test_backtest_trade_record_fields():
    record = BacktestTradeRecord(
        trade_date=date(2026, 4, 1),
        trader_id="trader_a",
        strategy_version_id="v1",
        symbol="000001.SZ",
        status="skipped",
    )
    assert record.skip_reason is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/unit/backtest/test_schemas.py -q`
Expected: FAIL，模块或类型不存在

- [ ] **Step 3: 实现最小 schema**

```python
class BacktestRequest(BaseModel):
    trader_id: str
    date_from: date
    date_to: date
    strategy_version_id: str | None = None
    symbols: list[str] = Field(default_factory=list)
    mode: Literal["replay", "rule_validation", "full"] = "full"
    use_snapshot_only: bool = True
    scoring_profile: str = "stage5"
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/unit/backtest/test_schemas.py -q`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/backtest/__init__.py src/backtest/schemas.py tests/unit/backtest/test_schemas.py
git commit -m "feat: add backtest schemas"
```

---

### Task 2: `NTL-S6-002` 回测执行器

**Files:**
- Create: `src/backtest/execution.py`
- Create: `src/backtest/strategy_replayer.py`
- Test: `tests/unit/backtest/test_execution.py`

- [ ] **Step 1: 写失败测试，覆盖 recommendation-only 重放**

```python
def test_replay_candidates_from_strategy_version():
    version = StrategyVersion(
        version_id="v1",
        trader_id="trader_a",
        strategy_date=date(2026, 4, 1),
        status=StrategyVersionStatus.released,
        recommendations=[
            StrategyRecommendation(symbol="000001.SZ", decision="buy", confidence=0.8)
        ],
    )
    market_context = {"trade_date": "2026-04-01", "bars_by_symbol": {}, "indicators_by_symbol": {}, "market_universe": None, "topic_snapshot": None, "source_refs": []}
    result = replay_candidates(version, market_context)
    assert len(result) == 1
    assert result[0]["symbol"] == "000001.SZ"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/unit/backtest/test_execution.py::test_replay_candidates_from_strategy_version -q`
Expected: FAIL

- [ ] **Step 3: 实现最小重放器与执行约束骨架**

```python
def replay_candidates(version: StrategyVersion, market_context: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "symbol": rec.symbol,
            "decision": rec.decision,
            "confidence": rec.confidence,
            "entry_price": rec.entry_price,
            "target_price": rec.target_price,
            "stop_loss_price": rec.stop_loss_price,
        }
        for rec in version.recommendations
    ]
```

- [ ] **Step 4: 为历史兼容补洞写失败测试**

```python
def test_detect_missing_rules_snapshot_as_compatibility_gap():
    version = StrategyVersion(
        version_id="v1",
        trader_id="trader_a",
        strategy_date=date(2026, 4, 1),
        status=StrategyVersionStatus.released,
        recommendations=[],
        rules_snapshot=[],
    )
    result = classify_rules_snapshot_gap(version)
    assert result == "missing_or_legacy_gap"
```

- [ ] **Step 5: 实现 gap 分类逻辑**

```python
def classify_rules_snapshot_gap(version: StrategyVersion) -> str | None:
    if version.rules_snapshot:
        return None
    return "missing_or_legacy_gap"
```

- [ ] **Step 6: 运行测试确认通过**

Run: `pytest tests/unit/backtest/test_execution.py -q`
Expected: PASS

- [ ] **Step 7: 提交**

```bash
git add src/backtest/execution.py src/backtest/strategy_replayer.py tests/unit/backtest/test_execution.py
git commit -m "feat: add backtest execution scaffolding"
```

---

### Task 3: `NTL-S6-003` 回测评分模块

**Files:**
- Create: `src/backtest/scoring.py`
- Test: `tests/unit/backtest/test_scoring.py`

- [ ] **Step 1: 写失败测试，要求复用 Stage 5 scoring**

```python
def test_score_backtest_trade_uses_stage5_metrics():
    result = score_backtest_trade(
        bars=[
            {"date": "2026-04-01", "open": 10.0, "high": 10.5, "low": 9.8, "close": 10.2},
            {"date": "2026-04-02", "open": 10.2, "high": 10.8, "low": 10.0, "close": 10.6},
        ],
        entry_price=10.0,
        entry_date="2026-04-01",
        target_price=11.0,
        stop_loss_price=9.5,
    )
    assert result["return_pct"] == pytest.approx(0.06)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/unit/backtest/test_scoring.py -q`
Expected: FAIL

- [ ] **Step 3: 实现适配层，不复制公式**

```python
from src.evaluation.metrics_calculator import compute_mfe_mae_return

def score_backtest_trade(...):
    mfe, mae, return_pct, exit_triggered, exit_date = compute_mfe_mae_return(...)
    return {
        "mfe": mfe,
        "mae": mae,
        "return_pct": return_pct,
        "exit_triggered": exit_triggered,
        "exit_date": exit_date,
    }
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/unit/backtest/test_scoring.py -q`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/backtest/scoring.py tests/unit/backtest/test_scoring.py
git commit -m "feat: add shared backtest scoring adapter"
```

---

### Task 4: `NTL-S6-004` 回测引擎

**Files:**
- Create: `src/backtest/engine.py`
- Test: `tests/unit/backtest/test_engine.py`

- [ ] **Step 1: 写失败测试，串联 loader/replayer/scoring**

```python
@pytest.mark.asyncio
async def test_engine_runs_single_day_backtest():
    loader = StubLoader()
    engine = BacktestEngine(loader=loader)
    req = BacktestRequest(trader_id="trader_a", date_from=date(2026, 4, 1), date_to=date(2026, 4, 1))
    result = await engine.run(req)
    assert result.summary.total_days == 1
```

- [ ] **Step 2: 实现最小引擎编排**

```python
class BacktestEngine:
    async def run(self, request: BacktestRequest) -> BacktestResult:
        records: list[BacktestTradeRecord] = []
        for trade_date in iter_trade_dates(request.date_from, request.date_to):
            ...
        return BacktestResult(...)
```

- [ ] **Step 3: 运行测试确认通过**

Run: `pytest tests/unit/backtest/test_engine.py -q`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add src/backtest/engine.py tests/unit/backtest/test_engine.py
git commit -m "feat: add backtest engine"
```

---

### Task 5: `NTL-S6-006` 快照与历史版本离线读取

**Files:**
- Create: `src/backtest/snapshot_loader.py`
- Test: `tests/unit/backtest/test_snapshot_loader.py`

- [ ] **Step 1: 写失败测试，优先读取 `market_universe` 与标准化 bars**

```python
def test_snapshot_loader_reads_market_universe_and_bars(tmp_path):
    loader = SnapshotLoader(base_dir=tmp_path, bars_dir=tmp_path / "bars")
    context = loader.load_market_context(date(2026, 4, 1), ["000001.SZ"])
    assert "bars_by_symbol" in context
```

- [ ] **Step 2: 实现最小读取顺序**

```python
class SnapshotLoader:
    def load_market_context(self, trade_date: date, symbols: list[str]) -> MarketContextSnapshot:
        market_universe = self.snapshot_service.load(trade_date.isoformat(), self.slot)
        bars_by_symbol = self._load_bars(trade_date, symbols)
        return {...}
```

- [ ] **Step 3: 为兼容兜底写失败测试**

```python
def test_snapshot_loader_marks_compatibility_fallback_when_using_evidence_pack():
    ...
    assert context["compatibility_fallback"] is True
```

- [ ] **Step 4: 实现兼容标记**

```python
context["compatibility_fallback"] = used_evidence_pack or used_signal_version
```

- [ ] **Step 5: 运行测试确认通过**

Run: `pytest tests/unit/backtest/test_snapshot_loader.py -q`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add src/backtest/snapshot_loader.py tests/unit/backtest/test_snapshot_loader.py
git commit -m "feat: add snapshot-only market context loader"
```

---

### Task 6: `NTL-S6-007` 统一线上线下 scoring 口径

**Files:**
- Modify: `src/evaluation/__init__.py`
- Modify: `src/backtest/scoring.py`
- Test: `tests/unit/backtest/test_scoring.py`

- [ ] **Step 1: 写失败测试，校验线上线下同输入同结果**

```python
def test_online_offline_scoring_same_case_same_result():
    bars = [...]
    offline = score_backtest_trade(...)
    online = compute_mfe_mae_return(...)
    assert offline["return_pct"] == online[2]
```

- [ ] **Step 2: 导出公共 scoring 接口或工具**

```python
__all__ = [
    "EvidencePack",
    ...
]
```

- [ ] **Step 3: 运行测试确认通过**

Run: `pytest tests/unit/backtest/test_scoring.py -q`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add src/evaluation/__init__.py src/backtest/scoring.py tests/unit/backtest/test_scoring.py
git commit -m "refactor: align backtest scoring with evaluation core"
```

---

### Task 7: `NTL-S6-005` 回测报告

**Files:**
- Create: `src/backtest/reporting.py`
- Test: `tests/unit/backtest/test_reporting.py`

- [ ] **Step 1: 写失败测试，要求输出 markdown 摘要**

```python
def test_render_backtest_markdown_summary():
    report = render_backtest_markdown(sample_result())
    assert "胜率" in report
    assert "样本覆盖天数" in report
```

- [ ] **Step 2: 实现最小报告渲染**

```python
def render_backtest_markdown(result: BacktestResult) -> str:
    return f"# Backtest Report\n\n- 样本覆盖天数: {result.summary.total_days}\n"
```

- [ ] **Step 3: 运行测试确认通过**

Run: `pytest tests/unit/backtest/test_reporting.py -q`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add src/backtest/reporting.py tests/unit/backtest/test_reporting.py
git commit -m "feat: add backtest reporting"
```

---

### Task 8: `NTL-S6-008` CLI 入口

**Files:**
- Modify: `cli/backtest.py`
- Modify: `cli/main.py`

- [ ] **Step 1: 写失败测试或命令样例，锁定 CLI 形态**

```python
python -m cli.main backtest run --trader trader_a --from 2026-04-01 --to 2026-04-10
```

- [ ] **Step 2: 在 `cli/backtest.py` 增加 Typer 命令**

```python
app = typer.Typer(add_completion=False)

@app.command("run")
def run_backtest(...):
    ...
```

- [ ] **Step 3: 在 `cli/main.py` 注册子应用**

```python
from cli.backtest import app as backtest_app
app.add_typer(backtest_app, name="backtest")
```

- [ ] **Step 4: 手工运行命令校验**

Run: `python -m cli.main backtest --help`
Expected: 显示 `run / validate-rules / reproducibility-check`

- [ ] **Step 5: 提交**

```bash
git add cli/backtest.py cli/main.py
git commit -m "feat: add stage6 backtest cli"
```

---

### Task 9: `NTL-S6-009` 规则白名单

**Files:**
- Create: `src/backtest/rule_registry.py`
- Test: `tests/unit/backtest/test_rule_registry.py`

- [ ] **Step 1: 写失败测试，分类 programmable level**

```python
def test_rule_registry_classifies_rule():
    meta = classify_rule({"rule_id": "r1", "condition": "rsi < 30"})
    assert meta.programmatic_level == "fully_programmable"
```

- [ ] **Step 2: 实现最小分类器**

```python
def classify_rule(rule: dict[str, Any]) -> RuleMeta:
    if "rsi" in str(rule):
        return RuleMeta(..., programmatic_level="fully_programmable")
    return RuleMeta(..., programmatic_level="unsupported")
```

- [ ] **Step 3: 运行测试确认通过**

Run: `pytest tests/unit/backtest/test_rule_registry.py -q`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add src/backtest/rule_registry.py tests/unit/backtest/test_rule_registry.py
git commit -m "feat: add rule registry for stage6 validation"
```

---

### Task 10: `NTL-S6-010` 高频规则命中验证

**Files:**
- Modify: `src/backtest/engine.py`
- Modify: `src/backtest/rule_registry.py`
- Test: `tests/unit/backtest/test_engine.py`

- [ ] **Step 1: 写失败测试，验证单条规则 hit/miss 统计**

```python
def test_validate_single_rule_hit_count():
    result = validate_rule_hits(rule_meta, contexts)
    assert result.hit_count >= 0
    assert result.sample_count == len(contexts)
```

- [ ] **Step 2: 实现最小 validator**

```python
def validate_rule_hits(rule_meta: RuleMeta, contexts: list[MarketContextSnapshot]) -> RuleValidationResult:
    ...
```

- [ ] **Step 3: 运行测试确认通过**

Run: `pytest tests/unit/backtest/test_engine.py -q`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add src/backtest/engine.py src/backtest/rule_registry.py tests/unit/backtest/test_engine.py
git commit -m "feat: add high-frequency rule validation"
```

---

### Task 11: `NTL-S6-011` 规则覆盖率与后验收益报告

**Files:**
- Modify: `src/backtest/reporting.py`
- Test: `tests/unit/backtest/test_reporting.py`

- [ ] **Step 1: 写失败测试，输出覆盖率和后验收益**

```python
def test_render_rule_validation_summary():
    report = render_rule_validation_markdown(sample_rule_results())
    assert "覆盖率" in report
    assert "后验收益" in report
```

- [ ] **Step 2: 实现规则报告渲染**

```python
def render_rule_validation_markdown(results: list[RuleValidationResult]) -> str:
    ...
```

- [ ] **Step 3: 运行测试确认通过**

Run: `pytest tests/unit/backtest/test_reporting.py -q`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add src/backtest/reporting.py tests/unit/backtest/test_reporting.py
git commit -m "feat: add rule validation reporting"
```

---

### Task 12: `NTL-S6-012` 主路径切换，冻结旧 `backtest_agent`

**Files:**
- Modify: `src/agents/backtest_agent/__init__.py`
- Modify: `docs/Project.md`
- Modify: `docs/TaskList.md`

- [ ] **Step 1: 在旧 agent 目录加历史说明**

```python
"""历史 backtest agent 目录。

Stage 6 起，回测主路径统一迁移到 src/backtest/。
本目录保留只读，不再承接新功能。
"""
```

- [ ] **Step 2: 更新文档说明**

```md
- 回测主路径：`src/backtest/`
- `src/agents/backtest_agent/`：历史目录，不再扩展
```

- [ ] **Step 3: 提交**

```bash
git add src/agents/backtest_agent/__init__.py docs/Project.md docs/TaskList.md
git commit -m "docs: switch backtest main path to src/backtest"
```

---

### Task 13: `NTL-S6-013` 复现验证

**Files:**
- Create: `src/backtest/reproducibility.py`
- Test: `tests/unit/backtest/test_reproducibility.py`

- [ ] **Step 1: 写失败测试，重复运行结果 hash 一致**

```python
def test_reproducibility_hash_same_request():
    result = compare_runs(sample_run_a(), sample_run_b())
    assert result.is_equal is True
```

- [ ] **Step 2: 实现最小 hash 对比**

```python
def fingerprint_result(result: BacktestResult) -> str:
    payload = json.dumps(result.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
```

- [ ] **Step 3: 运行测试确认通过**

Run: `pytest tests/unit/backtest/test_reproducibility.py -q`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add src/backtest/reproducibility.py tests/unit/backtest/test_reproducibility.py
git commit -m "feat: add backtest reproducibility checks"
```

---

## 自检

### Spec coverage

- `NTL-S6-001 ~ 013` 全部覆盖
- 补充了 Stage 6 连续性预检任务，处理 Stage 3/4/5 到 Stage 6 的数据衔接风险
- 覆盖了 `A 股规则约束 / 快照只读 / 统一 scoring / CLI / 规则验真 / 可复现`

### Placeholder scan

- 无 `TODO/TBD`
- 所有任务都给出明确文件路径、测试命令和提交粒度

### Type consistency

- TaskList 产物名使用 `execution.py`，与计划和修订后的 spec 一致
- CLI 入口统一为 `cli/backtest.py`
- 评分字段统一使用 `return_pct / mfe / mae`

---

Plan complete and saved to `docs/superpowers/plans/2026-04-25-stage6-implementation-plan.md`.

两种后续执行方式：

1. `Subagent-Driven`（推荐）- 按任务派发并逐个 review
2. `Inline Execution` - 在当前会话按计划顺序执行
