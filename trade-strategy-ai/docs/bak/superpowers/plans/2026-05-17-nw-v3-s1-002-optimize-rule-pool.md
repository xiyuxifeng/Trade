# NW-V3-S1-002 Optimize / Rule Pool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把候选创建、规则池回测和规则审核收敛成正式 Web 流程，保留 legacy `strategy-studio` 兼容层，但不再把它当成正式入口继续扩张。

**Architecture:** Canonical 事实源仍然是 `Job / Workflow / PipelineSpec / Artifact / Audit`。后端新增 `optimize` 与 `rule-pool` 的正式 workflow / pipeline contract，现有 `OptimizeService`、`RulePoolService`、`StrategyLibraryService` 继续承载业务逻辑，Router 只做输入输出和鉴权。Web 只把 `/rule-pool` 和 `/strategies` 作为正式入口，`/strategy-studio` 只保留兼容层，直到 V3 退役。

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, React, TanStack Query, Vitest, Pytest.

---

## Compatibility Boundaries

- Canonical UI:
  - `/rule-pool` 负责规则池审核。
  - `/strategies` 负责候选创建与候选对比。
- Legacy UI:
  - `/strategy-studio` 只保留兼容，不再新增正式导航文案。
- Canonical API:
  - 新增 `/api/ui/v1/optimize/*`
  - 新增 `/api/ui/v1/rule-pool/*`
- Legacy API:
  - `api/routers/ui/strategy_studio.py` 继续提供旧路径，但内部只做兼容转发或薄包装。

---

### Task 1: Canonical optimize / rule-pool pipeline contract

**Files:**
- Create: `src/pipelines/optimize_rule_pool_pipeline_spec.py`
- Modify: `src/pipelines/__init__.py`
- Modify: `src/services/job_registry.py`
- Modify: `src/services/workflow_service.py`
- Modify: `src/services/runtime_registry_bridge.py`
- Test: `tests/pipelines/test_optimize_rule_pool_pipeline_spec.py`
- Test: `tests/unit/services/test_job_registry.py`
- Test: `tests/unit/services/test_workflow_service.py`
- Test: `tests/unit/services/test_runtime_registry_bridge.py`

- [ ] **Step 1: Write the failing tests**

```python
from src.services.runtime_registry_bridge import get_pipeline_contract, get_job_contract, get_workflow_contract

def test_optimize_rule_pool_pipeline_contract():
    spec = get_pipeline_contract("optimize-rule-pool")
    assert spec["workflow_id"] == "optimize-rule-pool"
    assert spec["ui_page"] == "/rule-pool"
    assert spec["ui_task_ids"] == ["UI-V3-002", "UI-V3-003"]
    assert [step["step_id"] for step in spec["steps"]] == [
        "optimize-create-candidate",
        "rule-pool-backtest",
        "candidate-review",
        "rule-review",
    ]

def test_job_registry_exposes_optimize_rule_pool_jobs():
    assert get_job_contract("optimize-create-candidate") is not None
    assert get_job_contract("rule-pool-backtest") is not None
    assert get_job_contract("candidate-review") is not None
    assert get_job_contract("rule-review") is not None

def test_workflow_registry_exposes_optimize_and_rule_pool():
    assert get_workflow_contract("optimize") is not None
    assert get_workflow_contract("rule-pool") is not None
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run:

```bash
python -m pytest tests/pipelines/test_optimize_rule_pool_pipeline_spec.py tests/unit/services/test_job_registry.py tests/unit/services/test_workflow_service.py tests/unit/services/test_runtime_registry_bridge.py -q
```

Expected: fail because the canonical pipeline spec and new job/workflow entries do not exist yet.

- [ ] **Step 3: Implement the minimal contract**

Add `PipelineSpec` for `optimize-rule-pool` with:

- `workflow_id="optimize-rule-pool"`
- `ui_page="/rule-pool"`
- `ui_task_ids=("UI-V3-002", "UI-V3-003")`
- job types for candidate creation, rule-pool backtest, candidate review, and rule review
- output artifact kinds for candidate JSON, review report, and rule-pool backtest evidence

Update `JOB_DEFINITIONS`, `DEFAULT_WORKFLOWS`, and `runtime_registry_bridge` to expose the canonical contract without introducing a second facts source.

- [ ] **Step 4: Run the tests and confirm they pass**

Run the same `pytest` command again.

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/pipelines/optimize_rule_pool_pipeline_spec.py src/pipelines/__init__.py src/services/job_registry.py src/services/workflow_service.py src/services/runtime_registry_bridge.py tests/pipelines/test_optimize_rule_pool_pipeline_spec.py tests/unit/services/test_job_registry.py tests/unit/services/test_workflow_service.py tests/unit/services/test_runtime_registry_bridge.py
git commit -m "feat(rule-pool): add canonical optimize workflow contract"
```

---

### Task 2: Canonical optimize / rule-pool API routers with legacy compatibility

**Files:**
- Create: `api/routers/ui/optimize.py`
- Create: `api/routers/ui/rule_pool.py`
- Modify: `api/routers/ui/__init__.py`
- Modify: `api/app.py`
- Modify: `api/routers/ui/strategy_studio.py`
- Test: `tests/api/routers/test_optimize.py`
- Test: `tests/api/routers/test_rule_pool.py`
- Test: `tests/api/routers/ui/test_strategy_studio.py`
- Test: `tests/api/test_ui_openapi_contract.py`

- [ ] **Step 1: Write the failing tests**

```python
async def test_canonical_optimize_router_creates_candidate(client):
    response = await client.post(
        "/api/ui/v1/optimize/create-candidate",
        json={
            "parent_version_id": "trader_a_2026-05-09_released",
            "trader_id": "trader_a",
            "strategy_date": "2026-05-09",
            "adjustments": [
                {
                    "trader_id": "trader_a",
                    "rule_id": "rule-1",
                    "current_status": "hit_rate_too_low_and_return_negative",
                    "suggestion": "建议删除该规则",
                    "confidence": 0.8,
                    "basis": "hit_rate=0.4, rule_text=price above moving average",
                }
            ],
            "recommendations": [],
            "notes": "version notes",
        },
    )
    assert response.status_code == 200
    assert response.json()["item"]["version_type"] == "candidate"

async def test_canonical_rule_pool_router_reviews_rule(client):
    response = await client.post("/api/ui/v1/rule-pool/rule-1/review", json={"decision": "approve", "force": True, "reviewed_by": "web"})
    assert response.status_code == 200
    assert response.json()["review_status"] == "approved"

async def test_legacy_strategy_studio_remains_compatibility(client):
    response = await client.post(
        "/api/ui/v1/strategy-studio/optimize/create-candidate",
        json={
            "parent_version_id": "trader_a_2026-05-09_released",
            "trader_id": "trader_a",
            "strategy_date": "2026-05-09",
            "adjustments": [],
            "recommendations": [],
            "notes": "version notes",
        },
    )
    assert response.status_code == 200
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run:

```bash
python -m pytest tests/api/routers/test_optimize.py tests/api/routers/test_rule_pool.py tests/api/routers/ui/test_strategy_studio.py tests/api/test_ui_openapi_contract.py -q
```

Expected: fail because the canonical routers and app registration do not exist yet.

- [ ] **Step 3: Implement the canonical routers**

Move the existing `OptimizeService` and `RulePoolService` endpoints out of `strategy_studio.py` into canonical routers:

- `api/routers/ui/optimize.py`
  - `POST /api/ui/v1/optimize/advise-rule-validations`
  - `POST /api/ui/v1/optimize/filter-active-traders`
  - `POST /api/ui/v1/optimize/create-candidate`
- `api/routers/ui/rule_pool.py`
  - `GET /api/ui/v1/rule-pool`
  - `GET /api/ui/v1/rule-pool/{rule_id}`
  - `POST /api/ui/v1/rule-pool/{rule_id}/review`
  - `POST /api/ui/v1/rule-pool/review-batch`

Keep `api/routers/ui/strategy_studio.py` as the compatibility layer that delegates to the same services and preserves the old combined page behavior until V3 retirement.

Register the new routers in `api/routers/ui/__init__.py` and `api/app.py`.

- [ ] **Step 4: Run the tests and confirm they pass**

Run the same `pytest` command again.

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add api/routers/ui/optimize.py api/routers/ui/rule_pool.py api/routers/ui/__init__.py api/app.py api/routers/ui/strategy_studio.py tests/api/routers/test_optimize.py tests/api/routers/test_rule_pool.py tests/api/routers/ui/test_strategy_studio.py tests/api/test_ui_openapi_contract.py
git commit -m "feat(api): add canonical optimize and rule-pool routers"
```

---

### Task 3: Rule Pool Review UI

**Files:**
- Create: `web/src/features/rule-pool/rule-pool-review.tsx`
- Create: `web/src/lib/api/rule-pool.ts`
- Create: `web/src/types/rule-pool.ts`
- Modify: `web/src/pages/rule-pool/index.tsx`
- Modify: `web/src/pages/rule-pool/index.test.tsx`
- Modify: `web/src/app/navigation.ts`
- Modify: `web/src/app/route-registry.ts`
- Modify: `web/src/app/navigation.test.ts`
- Modify: `web/src/app/route-registry.test.ts`

- [ ] **Step 1: Write the failing tests**

```tsx
renderWithRouter([{ path: '/rule-pool', element: <RulePoolPage /> }], ['/rule-pool']);
expect(await screen.findByRole('heading', { name: '规则池审核中心' })).toBeInTheDocument();
expect(screen.getByRole('button', { name: '批准' })).toBeInTheDocument();
expect(screen.getByRole('button', { name: '拒绝' })).toBeInTheDocument();
expect(screen.getByText('审计历史')).toBeInTheDocument();
expect(screen.getByText('回测证据')).toBeInTheDocument();
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run:

```bash
node ./node_modules/vitest/vitest.mjs run src/pages/rule-pool/index.test.tsx src/app/navigation.test.ts src/app/route-registry.test.ts
```

Expected: fail because the page still only exposes the placeholder view and there is no canonical rule-pool client yet.

- [ ] **Step 3: Implement the minimal UI**

Replace the placeholder `/rule-pool` page with a formal review workspace:

- rule list with summary cards
- rule detail panel
- backtest result evidence panel
- approve / reject / pending actions
- audit history panel
- high-risk confirmation before write actions
- loading / empty / permission denied / retry states

Use `web/src/lib/api/rule-pool.ts` as the only client for the page.

- [ ] **Step 4: Run the tests and confirm they pass**

Run the same `vitest` command again.

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add web/src/features/rule-pool/rule-pool-review.tsx web/src/lib/api/rule-pool.ts web/src/types/rule-pool.ts web/src/pages/rule-pool/index.tsx web/src/pages/rule-pool/index.test.tsx web/src/app/navigation.ts web/src/app/route-registry.ts web/src/app/navigation.test.ts web/src/app/route-registry.test.ts
git commit -m "feat(rule-pool-ui): add formal review workspace"
```

---

### Task 4: Optimize Candidate UI in the formal strategy workspace

**Files:**
- Create: `web/src/features/strategy-workspace/strategy-workspace-candidate.tsx`
- Create: `web/src/lib/api/optimize.ts`
- Create: `web/src/types/optimize.ts`
- Modify: `web/src/features/strategy-workspace/strategy-workspace-shell.tsx`
- Modify: `web/src/features/strategy-workspace/strategy-workspace-actions.tsx`
- Modify: `web/src/pages/strategies/index.test.tsx`
- Modify: `web/src/features/strategy-workspace/strategy-workspace-shell.test.tsx`
- Modify: `web/src/features/strategy-studio/strategy-studio.tsx`
- Modify: `web/src/pages/strategy-studio/index.test.tsx`

- [ ] **Step 1: Write the failing tests**

```tsx
renderWithRouter([{ path: '/strategies', element: <StrategiesPage /> }], ['/strategies']);
expect(await screen.findByRole('heading', { name: '策略工作台' })).toBeInTheDocument();
expect(screen.getByText('候选版本')).toBeInTheDocument();
expect(screen.getByText('候选对比')).toBeInTheDocument();
expect(screen.getByRole('button', { name: '生成候选版本' })).toBeInTheDocument();
expect(screen.getByRole('button', { name: '提交审核' })).toBeInTheDocument();
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run:

```bash
node ./node_modules/vitest/vitest.mjs run src/pages/strategies/index.test.tsx src/features/strategy-workspace/strategy-workspace-shell.test.tsx src/pages/strategy-studio/index.test.tsx
```

Expected: fail because the candidate workspace still lives in the legacy combined page, not in the formal strategy workspace.

- [ ] **Step 3: Implement the formal candidate workspace**

Move candidate creation and comparison into the formal `/strategies` workspace:

- candidate summary panel
- parent version comparison
- candidate adjustments preview
- backtest evidence links
- submit / approve / reject actions
- explicit risk confirmation for write actions
- loading / empty / error / permission denied states

Keep `web/src/features/strategy-studio/strategy-studio.tsx` as legacy compatibility only. It should not become a second formal entry.

- [ ] **Step 4: Run the tests and confirm they pass**

Run the same `vitest` command again.

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add web/src/features/strategy-workspace/strategy-workspace-candidate.tsx web/src/lib/api/optimize.ts web/src/types/optimize.ts web/src/features/strategy-workspace/strategy-workspace-shell.tsx web/src/features/strategy-workspace/strategy-workspace-actions.tsx web/src/pages/strategies/index.test.tsx web/src/features/strategy-workspace/strategy-workspace-shell.test.tsx web/src/features/strategy-studio/strategy-studio.tsx web/src/pages/strategy-studio/index.test.tsx
git commit -m "feat(strategy-ui): add formal candidate workspace"
```

---

### Task 5: Review, docs, and task sync

**Files:**
- Modify: `docs/New-Web-Linked-TaskLists/New-Web-TaskList.md`
- Modify: `docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md`
- Modify: `daily-sessions/2026-05-17.md`
- Modify: `daily-report/2026-05-17.md`

- [ ] **Step 1: Run the focused regression set**

Run:

```bash
python -m pytest tests/unit/services/test_optimize_rule_pool_service.py tests/api/routers/test_optimize.py tests/api/routers/test_rule_pool.py tests/unit/services/test_workflow_service.py -q
node ./node_modules/vitest/vitest.mjs run src/pages/rule-pool/index.test.tsx src/pages/strategies/index.test.tsx src/pages/strategy-studio/index.test.tsx src/app/navigation.test.ts src/app/route-registry.test.ts
```

Expected: all pass.

- [ ] **Step 2: Review against acceptance**

Check each TaskList line item:

- 候选版本可追溯
- 规则审核有权限和审计
- 高风险操作需要确认
- 结果可以回写并审计
- Web 可完成审核流程

If any line is not covered, keep the task open and do not mark `[x]`.

- [ ] **Step 3: Update docs and task state**

Mark `NW-V3-S1-002`, `UI-V3-002`, and `UI-V3-003` only after the code, tests, and UI/API contract all pass review.

- [ ] **Step 4: Commit**

```bash
git add docs/New-Web-Linked-TaskLists/New-Web-TaskList.md docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md daily-sessions/2026-05-17.md daily-report/2026-05-17.md
git commit -m "docs(v3): sync optimize and rule-pool plan"
```

---

## Self-Review Checklist

- `optimize-rule-pool` pipeline contract has a task and a test.
- Canonical API routers are split from legacy compatibility.
- `/rule-pool` and `/strategies` are the only formal UI entry points for this slice.
- `/strategy-studio` is explicitly legacy only.
- Every task has a concrete test command and expected result.
- No placeholder text like `TBD` or `TODO`.
- No CLI-first implementation path is introduced.
