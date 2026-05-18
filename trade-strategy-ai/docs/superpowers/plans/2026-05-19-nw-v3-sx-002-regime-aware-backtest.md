# NW-V3-SX-002 Regime-aware Backtest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不破坏现有 benchmark 回测可复现性的前提下，把 `gap_down_rate_full_market` / `extreme_drop_count_full_market` 作为版本化特征落库，并让回测结果统一携带 overall / per-regime / per-rule per-regime 统计，满足 `NW-V3-SX-002` 和 `UI-V3-011`。

**Architecture:** 继续复用现有 `OHLCVBar`、`market_regime_features`、`market_regimes` 和 `/backtest_results` 文件结果体系，新增 `market-regime-features-v3` 与 `market-regime-v3` 作为 full-market 版本。回测结果不再拆成第二套 report schema，而是在现有 `BacktestResult` / `RuleBacktestResult` 上扩展 regime 分桶字段，保证 UI、artifact、fingerprint 和后续规则适用性任务共享同一 canonical 结果对象。

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy async, Pydantic, React, TanStack Query, Vitest, pytest.

---

### Task 1: Add full-market regime features and versioned persistence

**Files:**
- Modify: `src/services/market_regime_feature_service.py`
- Modify: `src/services/market_regime_rules.py`
- Modify: `src/services/market_regime_service.py`
- Modify: `src/models/market_regime.py`
- Modify: `src/db/repositories/market_regime_feature_repository.py`
- Test: `tests/unit/services/test_market_regime_feature_service.py`
- Test: `tests/unit/services/test_market_regime_rules.py`
- Test: `tests/unit/services/test_market_regime_service.py`
- Test: `tests/unit/db/repositories/test_market_regime_feature_repository.py`

- [ ] **Step 1: Write the failing tests**

```python
async def test_build_market_regime_features_adds_full_market_fields(service):
    result = await service.build_market_regime_features(
        snapshot_id="snap-001",
        feature_version="market-regime-features-v3",
    )
    payload = result.payload["feature_payload_json"]
    assert "gap_down_rate_full_market" in payload
    assert "extreme_drop_count_full_market" in payload
```

```python
def test_score_market_regime_uses_full_market_features_for_v3():
    result = score_market_regime(
        {
            "trend": {"feature_key": "trend", "value": {"ret_20d": -0.08}, "source_section": "ohlcv", "confidence": 0.95},
            "gap_down_rate_full_market": {"feature_key": "gap_down_rate_full_market", "value": 0.42, "source_section": "ohlcv_full_market", "confidence": 0.9},
            "extreme_drop_count_full_market": {"feature_key": "extreme_drop_count_full_market", "value": 5, "source_section": "ohlcv_full_market", "confidence": 0.9},
        },
        regime_version="market-regime-v3",
    )
    assert result.primary_label in {"weak_bear", "panic"}
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python -m pytest tests/unit/services/test_market_regime_feature_service.py tests/unit/services/test_market_regime_rules.py tests/unit/services/test_market_regime_service.py tests/unit/db/repositories/test_market_regime_feature_repository.py -q`

Expected: fail because `market-regime-features-v3` / full-market fields are not wired yet.

- [ ] **Step 3: Implement the minimal feature computation**

```python
def _build_full_market_metrics(self, session, trade_date: date) -> dict[str, Any]:
    # 读取当日全市场 OHLCV，统计跨股票跳空低开与极端下跌次数。
    # 返回 full-market summary + 两个派生字段，写入 feature_payload_json。
```

```python
feature_payload_json["gap_down_rate_full_market"] = {
    "feature_key": "gap_down_rate_full_market",
    "value": gap_down_rate_full_market,
    "source_section": "ohlcv_full_market",
    "source_version": "market-regime-features-v3",
    "confidence": 0.9,
    "weight": 1.0,
}
```

```python
feature_payload_json["extreme_drop_count_full_market"] = {
    "feature_key": "extreme_drop_count_full_market",
    "value": extreme_drop_count_full_market,
    "source_section": "ohlcv_full_market",
    "source_version": "market-regime-features-v3",
    "confidence": 0.9,
    "weight": 1.0,
}
```

- [ ] **Step 4: Make regime scoring consume the v3 fields**

```python
feature_keys = (
    "benchmark_ohlcv_window",
    "trend",
    "ret_5d",
    "ret_20d",
    "ma20_gap",
    "ma60_gap",
    "breadth",
    "breadth_up_ratio",
    "breadth_down_ratio",
    "volatility",
    "vol_spike",
    "liquidity",
    "turnover_level",
    "turnover_ratio",
    "theme_strength",
    "theme_concentration",
    "limit_up_count",
    "limit_down_count",
    "gap_down_rate",
    "extreme_drop_count",
    "gap_down_rate_full_market",
    "extreme_drop_count_full_market",
)
```

- [ ] **Step 5: Run the focused tests again**

Run: `python -m pytest tests/unit/services/test_market_regime_feature_service.py tests/unit/services/test_market_regime_rules.py tests/unit/services/test_market_regime_service.py tests/unit/db/repositories/test_market_regime_feature_repository.py -q`

Expected: PASS with the new full-market version persisted and scored.

- [ ] **Step 6: Commit the feature slice**

```bash
git add src/services/market_regime_feature_service.py src/services/market_regime_rules.py src/services/market_regime_service.py src/models/market_regime.py src/db/repositories/market_regime_feature_repository.py tests/unit/services/test_market_regime_feature_service.py tests/unit/services/test_market_regime_rules.py tests/unit/services/test_market_regime_service.py tests/unit/db/repositories/test_market_regime_feature_repository.py
git commit -m "feat(market-regime): add full-market v3 features"
```

### Task 2: Extend canonical backtest results with regime breakdowns

**Files:**
- Modify: `src/backtest/schemas.py`
- Modify: `src/rule_pool/schemas.py`
- Modify: `src/backtest/engine.py`
- Modify: `src/backtest/reproducibility.py`
- Modify: `src/backtest/reporting.py`
- Modify: `src/services/backtest_service.py`
- Modify: `src/services/job_runner.py`
- Modify: `src/services/job_registry.py`
- Modify: `src/rule_backtest/scheduler.py`
- Modify: `src/pipelines/optimize_rule_pool_pipeline_spec.py`
- Test: `tests/unit/backtest/test_rule_pool_backtest.py`
- Test: `tests/unit/services/test_backtest_service.py`
- Test: `tests/unit/backtest/test_engine_regime_context.py`
- Test: `tests/unit/backtest/test_snapshot_loader.py`
- Test: `tests/unit/backtest/test_backtest_reporting.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_rule_backtest_result_exposes_regime_metrics():
    result = RuleBacktestResult(
        run_id="run-1",
        run_at=datetime.now(),
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 10),
        regime_metrics=[
            {"regime_label": "panic", "sample_count": 4, "hit_rate": 0.5, "avg_return": -0.02, "max_drawdown": 0.08, "confidence": 0.7},
        ],
    )
    assert result.regime_metrics[0]["regime_label"] == "panic"
```

```python
def test_backtest_result_exposes_regime_breakdown():
    result = BacktestResult(
        request_trader_id="rule_pool",
        request_date_from=date(2026, 5, 1),
        request_date_to=date(2026, 5, 10),
        regime_version="market-regime-v3",
        source_feature_version="market-regime-features-v3",
        regime_metrics=[{"regime_label": "panic", "sample_count": 4, "hit_rate": 0.5}],
        rule_regime_metrics={"rule-1": [{"regime_label": "panic", "sample_count": 4, "hit_rate": 0.5}]},
    )
    payload = asdict(result)
    assert payload["regime_version"] == "market-regime-v3"
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python -m pytest tests/unit/backtest/test_rule_pool_backtest.py tests/unit/services/test_backtest_service.py tests/unit/backtest/test_engine_regime_context.py tests/unit/backtest/test_snapshot_loader.py tests/unit/backtest/test_backtest_reporting.py -q`

Expected: fail because `BacktestResult` / `RuleBacktestResult` do not yet expose regime breakdown fields.

- [ ] **Step 3: Extend the result schemas and fingerprint**

```python
@dataclass
class RegimeBacktestMetric:
    regime_label: str
    sample_count: int
    hit_trades: int
    miss_trades: int
    hit_rate: float | None = None
    avg_return: float | None = None
    max_drawdown: float | None = None
    profit_factor: float | None = None
    confidence: float = 0.0
    low_sample: bool = False
```

```python
@dataclass
class BacktestResult:
    ...
    regime_version: str | None = None
    source_feature_version: str | None = None
    regime_metrics: list[RegimeBacktestMetric] = field(default_factory=list)
    rule_regime_metrics: dict[str, list[RegimeBacktestMetric]] = field(default_factory=dict)
```

```python
class RuleBacktestResult(BaseModel):
    ...
    regime_metrics: list[dict[str, Any]] = Field(default_factory=list)
```

- [ ] **Step 4: Thread market_regime_version through rule-pool backtest**

```python
async def run_rules_backtest(..., market_regime_version: str | None = None) -> BacktestResult:
    result = await self._backtest_single_rule(
        rule,
        start_date,
        end_date,
        session=session,
        forward_bars=forward_bars,
        market_regime_version=market_regime_version,
    )
```

```python
def _def(job_type="rule-pool-backtest", ...):
    param_schema=_schema(
        "规则池回测参数",
        {
            "start_date": _date_field("开始日期", required=True),
            "end_date": _date_field("结束日期", required=True),
            "rule_ids": _array_field("规则列表", default=[]),
            "min_confidence": _number_field("最小置信度", default=0.5),
            "market_regime_version": _string("Market Regime 版本", default="market-regime-v3"),
            "config_path": _path_field("配置文件路径"),
        },
    )
```

```python
ctx = await loader.load_market_context(
    trade_date=trade_date,
    symbols=[],
    regime_version=market_regime_version,
)
```

- [ ] **Step 5: Aggregate per-regime and per-rule per-regime metrics**

```python
if regime_label is not None:
    regime_buckets[regime_label].append(hit_return)
    rule_regime_buckets[rule.rule_id][regime_label].append(hit_return)
```

```python
regime_metrics = [
    {
        "regime_label": label,
        "sample_count": len(values),
        "hit_rate": ...,
        "avg_return": ...,
        "max_drawdown": ...,
        "confidence": ...,
        "low_sample": len(values) < 10,
    }
    for label, values in sorted(regime_buckets.items())
]
```

- [ ] **Step 6: Update reporting and reproducibility output**

```python
def render_backtest_markdown(result: BacktestResult) -> str:
    lines.append("## Regime Breakdown")
    for item in result.regime_metrics:
        lines.append(f"- {item.regime_label}: sample={item.sample_count}, hit_rate={item.hit_rate}, avg_return={item.avg_return}")
```

```python
def fingerprint_result(result: BacktestResult) -> str:
    d = asdict(result)
    d = _json_safe(d)
    return hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
```

- [ ] **Step 7: Run the backtest regression tests**

Run: `python -m pytest tests/unit/backtest/test_rule_pool_backtest.py tests/unit/services/test_backtest_service.py tests/unit/backtest/test_engine_regime_context.py tests/unit/backtest/test_snapshot_loader.py tests/unit/backtest/test_backtest_reporting.py -q`

Expected: PASS, and the JSON result files now include regime breakdown fields without breaking old consumers.

- [ ] **Step 8: Commit the canonical backtest slice**

```bash
git add src/backtest/schemas.py src/rule_pool/schemas.py src/backtest/engine.py src/backtest/reproducibility.py src/backtest/reporting.py src/services/backtest_service.py src/rule_backtest/scheduler.py src/services/job_registry.py tests/unit/backtest/test_rule_pool_backtest.py tests/unit/services/test_backtest_service.py tests/unit/backtest/test_engine_regime_context.py tests/unit/backtest/test_snapshot_loader.py tests/unit/backtest/test_backtest_reporting.py
git commit -m "feat(backtest): add regime-aware result schema"
```

### Task 3: Add regime-aware backtest report UI and surface the new result fields

**Files:**
- Modify: `web/src/features/backtest/backtest-center.tsx`
- Add: `web/src/features/backtest/regime-backtest-report.tsx`
- Add: `web/src/pages/backtest/RegimeBacktestReportPage.tsx`
- Modify: `web/src/lib/api/backtests.ts`
- Modify: `web/src/types/backtests.ts`
- Modify: `web/src/app/router.tsx`
- Modify: `web/src/app/navigation.ts`
- Test: `web/src/features/backtest/backtest-center.test.tsx`
- Test: `web/src/features/backtest/regime-backtest-report.test.tsx`
- Test: `web/src/pages/backtest/RegimeBacktestReportPage.test.tsx`

- [ ] **Step 1: Write the failing UI tests**

```tsx
it('renders regime breakdown when backtest result includes regime metrics', async () => {
  render(<RegimeBacktestReportPage />);
  expect(await screen.findByText('Regime Breakdown')).toBeInTheDocument();
});
```

```tsx
it('keeps the formal backtest workbench working with old and new result fields', async () => {
  render(<BacktestPage />);
  expect(screen.getByText('最近结果')).toBeInTheDocument();
  expect(screen.getByText('Regime Breakdown')).not.toBeVisible();
});
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `pnpm --dir web test -- src/features/backtest/backtest-center.test.tsx src/features/backtest/regime-backtest-report.test.tsx src/pages/backtest/RegimeBacktestReportPage.test.tsx`

Expected: fail because the report page and regime breakdown rendering do not exist yet.

- [ ] **Step 3: Implement the regime report page and API typing**

```ts
export type RegimeBacktestMetric = {
  regime_label: string;
  sample_count: number;
  hit_trades: number;
  miss_trades: number;
  hit_rate: number | null;
  avg_return: number | null;
  max_drawdown: number | null;
  profit_factor: number | null;
  confidence: number;
  low_sample: boolean;
};
```

```tsx
function RegimeBreakdownPanel({ result }: { result: BacktestResultItem }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Regime Breakdown</CardTitle>
      </CardHeader>
      <CardContent>{/* overall / per-regime / per-rule per-regime tables */}</CardContent>
    </Card>
  );
}
```

- [ ] **Step 4: Wire the route and navigation**

```tsx
<Route path="/backtest/regime" element={<RegimeBacktestReportPage />} />
```

```ts
{ label: 'Regime 回测', path: '/backtest/regime', description: '查看按 market regime 分桶的回测报告' }
```

- [ ] **Step 5: Re-run the UI tests**

Run: `pnpm --dir web test -- src/features/backtest/backtest-center.test.tsx src/features/backtest/regime-backtest-report.test.tsx src/pages/backtest/RegimeBacktestReportPage.test.tsx`

Expected: PASS with the report page showing overall / per-regime / per-rule per-regime metrics.

- [ ] **Step 6: Commit the UI slice**

```bash
git add web/src/features/backtest/backtest-center.tsx web/src/features/backtest/regime-backtest-report.tsx web/src/pages/backtest/RegimeBacktestReportPage.tsx web/src/lib/api/backtests.ts web/src/types/backtests.ts web/src/app/router.tsx web/src/app/navigation.ts web/src/features/backtest/backtest-center.test.tsx web/src/features/backtest/regime-backtest-report.test.tsx web/src/pages/backtest/RegimeBacktestReportPage.test.tsx
git commit -m "feat(backtest-ui): add regime-aware report"
```

### Task 4: Update docs, TaskLists, and verification artifacts

**Files:**
- Modify: `docs/New-Web-Market-Regime-Definition.md`
- Modify: `docs/New-Web-Linked-TaskLists/New-Web-TaskList.md`
- Modify: `docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md`
- Modify: `daily-sessions/2026-05-19.md`
- Modify: `daily-report/2026-05-19.md`

- [ ] **Step 1: Sync the regime definition document**

```md
- `gap_down_rate_full_market`：已落地，benchmark 版与 full-market 版并存。
- `extreme_drop_count_full_market`：已落地，benchmark 版与 full-market 版并存。
- `NW-V3-SX-002` 使用 `market-regime-features-v3` 和 `market-regime-v3`。
```

- [ ] **Step 2: Mark the linked tasks only after code and tests pass**

```md
- `NW-V3-SX-002` -> `[x]`
- `UI-V3-011` -> `[x]`
```

- [ ] **Step 3: Write the session/report recap**

```md
## Current Context
## Resume Point
## Completed
## Verification
## Remaining Risks
```

- [ ] **Step 4: Run the final validation commands**

Run:
`python -m pytest tests/unit/services/test_market_regime_feature_service.py tests/unit/services/test_market_regime_rules.py tests/unit/services/test_market_regime_service.py tests/unit/backtest/test_rule_pool_backtest.py tests/unit/services/test_backtest_service.py tests/unit/backtest/test_engine_regime_context.py tests/unit/backtest/test_snapshot_loader.py tests/unit/backtest/test_backtest_reporting.py -q`

Run:
`pnpm --dir web test -- src/features/backtest/backtest-center.test.tsx src/features/backtest/regime-backtest-report.test.tsx src/pages/backtest/RegimeBacktestReportPage.test.tsx`

Run:
`git diff --check`

- [ ] **Step 5: Commit the docs and verification updates**

```bash
git add docs/New-Web-Market-Regime-Definition.md docs/New-Web-Linked-TaskLists/New-Web-TaskList.md docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md daily-sessions/2026-05-19.md daily-report/2026-05-19.md
git commit -m "docs(regime): align regime-aware backtest rollout"
```
