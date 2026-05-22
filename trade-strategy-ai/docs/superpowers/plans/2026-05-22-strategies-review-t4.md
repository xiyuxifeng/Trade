# Strategies Review T4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成 review 文档里的策略辅助页面与版本构建任务，让 `/strategies` 体系在 Web 上以 Profile-only 方式完成策略版本、候选、历史、规则选择与正式运行入口，并满足验收标准。

**Architecture:** 前端以现有 `strategy-workspace` 组件为基础拆分独立页面，避免重复造轮子；后端先收口 `strategy-build` / `run-pre-market` / `run-after-close` 的 Web 契约，使 `profile_id` 成为正式入口并移除 Web 侧 `config_path` 依赖。页面层通过真实 API 读取版本、候选、历史和规则选择结果，所有关键页面都提供 loading / empty / error / retry / success 状态与返回首页入口。

**Tech Stack:** React + React Router + TanStack Query + Vitest, FastAPI, SQLAlchemy, existing job registry / job runner / strategy service.

---

### Task 1: 收口 strategy-build 的 Web 契约

**Files:**
- Modify: `src/services/job_registry.py`
- Modify: `src/services/job_runner.py`
- Modify: `src/services/strategy_service.py`
- Modify: `tests/unit/services/test_job_registry.py`
- Modify: `tests/unit/services/test_job_runner.py`
- Modify: `tests/unit/services/test_strategy_service.py`

- [ ] **Step 1: 写失败测试**

```python
def test_validate_job_submission_allows_profile_only_strategy_build():
    result = validate_job_submission(
        job_type="strategy-build",
        params={
            "profile_id": "default",
            "trader_id": "trader_a",
            "strategy_date": "2026-05-22",
            "force": False,
        },
        created_by="web",
    )
    assert result.status == "ok"
    assert "config_path" not in result.payload["params"]
```

- [ ] **Step 2: 运行测试确认当前失败**

Run: `python -m pytest tests/unit/services/test_job_registry.py::test_validate_job_submission_enforces_schema -q`
Expected: `strategy-build` 仍要求 `config_path`，测试不能覆盖 profile-only 提交。

- [ ] **Step 3: 最小实现**

```python
# src/services/job_registry.py
_def(
    job_type="strategy-build",
    ...
    param_schema=_schema(
        "策略构建参数",
        {
            "profile_id": _string("Profile ID", required=True),
            "config_path": _path_field("配置文件路径"),
            "trader_id": _string("交易员 ID", required=True),
            "strategy_date": _date_field("策略日期", required=True),
            "snapshot_id": _string("当前 Market Snapshot ID"),
            "market_regime_version": _string("市场状态版本", default="market-regime-v3"),
            "source_feature_version": _string("Market Regime 特征版本", default="market-regime-features-v3"),
            "applicability_profile_version": _string("规则适用性画像版本", default="rule-applicability-v1"),
            "selected_by": _string("选择来源", default="web"),
            "regime_selection": _object_field("Regime selection 摘要"),
            "force": _boolean("是否强制执行", default=False),
        },
    ),
```

```python
# src/services/job_runner.py
async def _strategy_build(params: dict[str, Any]) -> ServiceResult:
    service = StrategyService()
    return await service.build_strategy_version(
        config_path=params.get("config_path", "config/app.yaml"),
        profile_id=params.get("profile_id"),
        trader_id=str(params.get("trader_id") or ""),
        strategy_date=str(params.get("strategy_date") or date.today().isoformat()),
        force=_parse_bool(params.get("force"), default=False),
        regime_selection=params.get("regime_selection"),
        snapshot_id=params.get("snapshot_id"),
        market_regime_version=params.get("market_regime_version"),
        source_feature_version=params.get("source_feature_version"),
        applicability_profile_version=params.get("applicability_profile_version"),
        selected_by=params.get("selected_by"),
    )
```

```python
# src/services/strategy_service.py
async def build_strategy_version(..., profile_id: str | None = None, config_path: str | Path | None = None, ...):
    runtime_config = resolve_runtime_config({"profile_id": profile_id, "config_path": config_path})
    loaded = load_app_config(runtime_config.config_path or "config/app.yaml")
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/unit/services/test_job_registry.py tests/unit/services/test_job_runner.py tests/unit/services/test_strategy_service.py -q`
Expected: `strategy-build` can be submitted with `profile_id` and no Web `config_path`.

- [ ] **Step 5: 提交**

```bash
git add src/services/job_registry.py src/services/job_runner.py src/services/strategy_service.py tests/unit/services/test_job_registry.py tests/unit/services/test_job_runner.py tests/unit/services/test_strategy_service.py
git commit -m "feat(strategy): allow profile-only web strategy build"
```

### Task 2: 拆分策略辅助页面

**Files:**
- Create: `web/src/pages/strategies/VersionsPage.tsx`
- Create: `web/src/pages/strategies/CandidatesPage.tsx`
- Create: `web/src/pages/strategies/HistoryPage.tsx`
- Modify: `web/src/pages/strategies/RegimeRuleSelectionPage.tsx`
- Modify: `web/src/app/router.tsx`
- Modify: `web/src/app/navigation.ts`
- Modify: `web/src/app/route-registry.ts`
- Modify: `web/src/pages/strategies/index.tsx`
- Create: `web/src/pages/strategies/VersionsPage.test.tsx`
- Create: `web/src/pages/strategies/CandidatesPage.test.tsx`
- Create: `web/src/pages/strategies/HistoryPage.test.tsx`
- Modify: `web/src/pages/strategies/RegimeRuleSelectionPage.test.tsx`

- [ ] **Step 1: 写失败测试**

```tsx
it('renders strategy versions page with build action and back link', async () => {
  renderWithRouter([{ path: '/strategies/versions', element: <VersionsPage /> }], ['/strategies/versions']);
  expect(await screen.findByRole('heading', { name: '策略版本' })).toBeInTheDocument();
  expect(screen.getByRole('link', { name: '返回策略首页' })).toHaveAttribute('href', '/strategies');
});
```

- [ ] **Step 2: 运行测试确认当前失败**

Run: `python -m pytest web/src/pages/strategies/VersionsPage.test.tsx -q`
Expected: page and route do not exist yet.

- [ ] **Step 3: 最小实现**

```tsx
// web/src/pages/strategies/VersionsPage.tsx
export function StrategyVersionsPage() {
  return <StrategyVersionsWorkspace />;
}

// router / navigation / route registry
{ path: 'strategies/versions', element: <StrategyVersionsPage /> },
{ label: '策略版本', path: '/strategies/versions', description: '策略版本构建与查看', kind: 'canonical' },
```

```tsx
// 页面结构必须包含
<Link to="/strategies">返回策略首页</Link>
<PageHeader title="策略版本" ... />
<useQuery listStrategyVersions />
<useMutation createJob({ job_type: 'strategy-build', params: { profile_id, trader_id, strategy_date, ... } }) />
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest web/src/pages/strategies/VersionsPage.test.tsx web/src/pages/strategies/CandidatesPage.test.tsx web/src/pages/strategies/HistoryPage.test.tsx web/src/pages/strategies/RegimeRuleSelectionPage.test.tsx -q`
Expected: pages render with real data, route back-links, and non-empty states.

- [ ] **Step 5: 提交**

```bash
git add web/src/pages/strategies web/src/app/router.tsx web/src/app/navigation.ts web/src/app/route-registry.ts
git commit -m "feat(strategy): split auxiliary strategy pages"
```

### Task 3: 去掉 Web 侧 config_path 并补齐 benchmark_symbol 兼容

**Files:**
- Modify: `web/src/features/strategy-workspace/strategy-workspace-actions.tsx`
- Modify: `web/src/features/strategy-workspace/strategy-pre-market-page.tsx`
- Modify: `web/src/features/strategy-workspace/strategy-lifecycle-page.tsx`
- Modify: `web/src/features/strategy-workspace/strategy-workspace-shell.tsx`
- Modify: `web/src/features/strategy-workspace/strategy-workspace-shell.test.tsx`
- Modify: `web/src/pages/strategies/lifecycle.test.tsx`
- Modify: `web/src/lib/api/contract.test.ts`

- [ ] **Step 1: 写失败测试**

```tsx
expect(mockedCreateJob.mock.calls[0][0].params).not.toHaveProperty('config_path');
expect(mockedCreateJob.mock.calls[0][0].params).toMatchObject({
  profile_id: 'default',
});
```

- [ ] **Step 2: 运行测试确认当前失败**

Run: `python -m pytest web/src/pages/strategies/lifecycle.test.tsx web/src/features/strategy-workspace/strategy-workspace-shell.test.tsx -q`
Expected: current code still sends `config_path` from the strategy workspace.

- [ ] **Step 3: 最小实现**

```tsx
// buildStrategyJobParams
return {
  profile_id: profileId,
  trader_id: traderId,
  strategy_date: strategyDate,
  force: false,
  snapshot_id: snapshotId ?? undefined,
  market_regime_version: 'market-regime-v3',
  selected_by: 'web',
};
```

```tsx
// pre-market page
const params = {
  profile_id: selectedProfileId,
  as_of_date: strategyDate,
  force: runForce,
  export_html: runExportHtml,
};
if (benchmarkSymbol.trim()) params.benchmark_symbol = benchmarkSymbol.trim();
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest web/src/pages/strategies/lifecycle.test.tsx web/src/features/strategy-workspace/strategy-workspace-shell.test.tsx web/src/lib/api/contract.test.ts -q`
Expected: Web submissions no longer include `config_path`; `benchmark_symbol` remains optional.

- [ ] **Step 5: 提交**

```bash
git add web/src/features/strategy-workspace web/src/pages/strategies web/src/lib/api/contract.test.ts
git commit -m "feat(strategy): remove web config_path from strategy submissions"
```

### Task 4: 验证与收尾

**Files:**
- Modify: `docs/review/strategies_new.md`
- Modify: `docs/New-Web-Linked-TaskLists/New-Web-TaskList.md`
- Modify: `docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md`
- Create or update: `daily-sessions/2026-05-22.md`
- Create or update: `daily-report/2026-05-22.md`

- [ ] **Step 1: 运行全量相关测试**

Run:
`python -m pytest tests/unit/services/test_job_registry.py tests/unit/services/test_job_runner.py tests/unit/services/test_strategy_service.py tests/api/routers/ui/test_strategy_studio.py web/src/pages/strategies/lifecycle.test.tsx web/src/features/strategy-workspace/strategy-workspace-shell.test.tsx web/src/pages/strategies/RegimeRuleSelectionPage.test.tsx -q`

- [ ] **Step 2: 运行前端关键验证**

Run:
`npm test -- web/src/pages/strategies/VersionsPage.test.tsx web/src/pages/strategies/CandidatesPage.test.tsx web/src/pages/strategies/HistoryPage.test.tsx`

- [ ] **Step 3: 同步文档与任务状态**

```md
- 将 T4 状态更新为 [x]，并写明已完成的页面与契约改动。
- 在 daily-session 中记录本次实现范围、验证命令和后续风险。
- 在 daily-report 中记录 review 文档对应的验收结果。
```

- [ ] **Step 4: 最终检查**

确认：
- `/strategies/versions`
- `/strategies/candidates`
- `/strategies/history`
- `/strategies/regime-selection`
- `/strategies/pre-market`
- `/strategies/after-close`

都能在浏览器中访问，且 `config_path` 不再出现在 Web 策略提交参数中。

