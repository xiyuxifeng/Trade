# NW-V3-SX-004 Regime-aware Rule Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic regime-aware rule selector to the strategy workspace, persist its result in the existing strategy/job chain, and expose it in the Web UI without creating a second strategy source of truth.

**Architecture:** The selector is a pure backend service that consumes the current strategy version, trader profile, market regime, and rule applicability profiles, then emits a selection artifact plus a compact summary. The canonical execution entry is the existing `strategy-build` job path, which is extended in place so the feature stays inside the current Web/runtime contract and does not fork the strategy schema.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async, Pydantic, React, TanStack Query, Vitest, Pytest.

---

### Task 1: Build the pure regime-aware selector and its artifact schema

**Files:**
- Create: `src/models/regime_rule_selection.py`
- Create: `src/services/regime_rule_selection_service.py`
- Test: `tests/unit/services/test_regime_rule_selection_service.py`

- [ ] **Step 1: Write the failing test**

```python
async def test_build_regime_rule_selection_prefers_applicable_and_excludes_blocked() -> None:
    result = await service.build_regime_rule_selection(
        strategy_version_id="sv-1",
        snapshot_id="snap-1",
        trader_id="trader_a",
        profile_id="profile_a",
        market_regime_version="market-regime-v3",
        selected_by="web",
    )

    assert result.status == "ok"
    selection = result.payload["selection"]
    assert [item["rule_id"] for item in selection["selected_rules"]] == ["rule_applicable"]
    assert "rule_blocked" not in {item["rule_id"] for item in selection["selected_rules"]}
    assert any(item["rule_id"] == "rule_blocked" for item in selection["blocked_rules"])


async def test_build_regime_rule_selection_marks_theme_hot_neutral_as_low_weight_fallback() -> None:
    result = await service.build_regime_rule_selection(
        strategy_version_id="sv-2",
        snapshot_id="snap-2",
        trader_id="trader_a",
        profile_id="profile_a",
        market_regime_version="market-regime-v3",
        selected_by="web",
    )

    selection = result.payload["selection"]
    assert selection["quality_status"] in {"ok", "partial"}
    assert any(item["decision"] == "neutral" for item in selection["skipped_rules"] + selection["selected_rules"])
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
python -m pytest tests/unit/services/test_regime_rule_selection_service.py -q
```

Expected: FAIL because `RegimeRuleSelectionService` and the artifact schema do not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Implement:

```python
@dataclass(frozen=True)
class RegimeRuleSelectionRecord:
    rule_id: str
    decision: str
    score: float
    reason: str
    evidence: list[str]
    regime_version: str
    applicability_profile_version: str | None
    sample_count: int
    profile_confidence: float
    override_applied: bool = False
    rule_applicability_profile_id: str | None = None


@dataclass(frozen=True)
class RegimeRuleSelectionResult:
    selection_id: str
    strategy_version_id: str
    snapshot_id: str
    market_regime_version: str
    source_feature_version: str | None
    applicability_profile_version: str | None
    selected_rules: list[RegimeRuleSelectionRecord]
    skipped_rules: list[RegimeRuleSelectionRecord]
    blocked_rules: list[RegimeRuleSelectionRecord]
    selection_reason: str
    evidence: list[str]
    override: dict[str, Any] | None
    confidence: float
    quality_status: str
    warnings: list[str]
    created_at: datetime
```

and:

```python
class RegimeRuleSelectionService(BaseService):
    async def build_regime_rule_selection(
        self,
        *,
        strategy_version_id: str,
        snapshot_id: str,
        trader_id: str,
        profile_id: str,
        market_regime_version: str,
        selected_by: str,
        applicability_profile_version: str | None = None,
        override: dict[str, Any] | None = None,
    ) -> ServiceResult:
        ...
```

The implementation should:

- load the strategy version, trader profile, market regime, and rule applicability profiles;
- choose `applicable_regimes` first, `neutral_regimes` second, and exclude `blocked_regimes` unless `override` is explicit;
- resolve multiple profiles deterministically by regime version, review status, created time, then profile id;
- emit a selection artifact under `data/processed/strategy_regime_selection/...`;
- return a `ServiceResult` with `selection`, `artifact_ref`, and `warnings`.

- [ ] **Step 4: Run the test to verify it passes**

Run:

```bash
python -m pytest tests/unit/services/test_regime_rule_selection_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/models/regime_rule_selection.py src/services/regime_rule_selection_service.py tests/unit/services/test_regime_rule_selection_service.py
git commit -m "feat: add regime-aware rule selection service"
```

---

### Task 2: Thread regime-aware selection into the strategy build contract

**Files:**
- Modify: `src/strategy_library/schemas.py`
- Modify: `src/strategy_library/repository.py`
- Modify: `src/services/strategy_service.py`
- Modify: `src/services/job_runner.py`
- Modify: `src/services/job_registry.py`
- Modify: `src/pipelines/strategy_pipeline_spec.py`
- Test: `tests/unit/services/test_strategy_service.py`
- Test: `tests/unit/services/test_job_runner.py`
- Test: `tests/pipelines/test_strategy_pipeline_spec.py`

- [ ] **Step 1: Write the failing tests**

Add a strategy service test that proves `build_strategy_version()` accepts regime-aware selection inputs and stores a compact summary on the saved strategy version.

```python
async def test_build_strategy_version_attaches_regime_selection_summary() -> None:
    result = await service.build_strategy_version(
        config_path=config_path,
        trader_id="trader_a",
        strategy_date="2026-05-19",
        force=True,
        snapshot_id="snap-1",
        market_regime_version="market-regime-v3",
        applicability_profile_version="rule-applicability-v1",
        selected_by="web",
    )

    assert result.payload["strategy_version"]["regime_selection"]["snapshot_id"] == "snap-1"
    assert result.payload["strategy_version"]["regime_selection"]["market_regime_version"] == "market-regime-v3"
```

Add a job runner test that proves the `strategy-build` job forwards the new parameters.

```python
assert captured["params"]["snapshot_id"] == "snap-1"
assert captured["params"]["market_regime_version"] == "market-regime-v3"
assert captured["params"]["applicability_profile_version"] == "rule-applicability-v1"
assert captured["params"]["selected_by"] == "web"
```

Add a pipeline spec test that proves the canonical `strategy` spec exposes the new input fields and a `regime-selection-json` artifact.

```python
spec = get_pipeline_contract("strategy")
assert "snapshot_id" in spec["input_schema"]["fields"]
assert "market_regime_version" in spec["input_schema"]["fields"]
assert "selected_by" in spec["input_schema"]["fields"]
assert any(item["kind"] == "regime-selection-json" for item in spec["output_artifacts"])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
python -m pytest tests/unit/services/test_strategy_service.py tests/unit/services/test_job_runner.py tests/pipelines/test_strategy_pipeline_spec.py -q
```

Expected: FAIL because the strategy build contract does not yet accept or persist the selection summary.

- [ ] **Step 3: Write the minimal implementation**

Implement the contract extension in this order:

1. Add `regime_selection` to `StrategyVersion` so it can round-trip through the repository without adding a second strategy schema.
2. Extend `StrategyLibraryRepository` so `strategy_payload["regime_selection"]` is saved and restored with the rest of the strategy payload.
3. Extend `StrategyService.build_strategy_version()` to accept selection inputs, call `RegimeRuleSelectionService`, and return the selection summary in the payload.
4. Extend `job_runner.py` so the `strategy-build` handler forwards the new parameters, including `selected_by`.
5. Extend `job_registry.py` and `strategy_pipeline_spec.py` so the canonical `strategy-build` schema lists the new selection fields, including `selected_by`, and the `regime-selection-json` artifact.

Keep the new parameters optional at the job schema level for backward compatibility, but make the Web strategy workspace supply them in the new flow.

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
python -m pytest tests/unit/services/test_strategy_service.py tests/unit/services/test_job_runner.py tests/pipelines/test_strategy_pipeline_spec.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/strategy_library/schemas.py src/strategy_library/repository.py src/services/strategy_service.py src/services/job_runner.py src/services/job_registry.py src/pipelines/strategy_pipeline_spec.py tests/unit/services/test_strategy_service.py tests/unit/services/test_job_runner.py tests/pipelines/test_strategy_pipeline_spec.py
git commit -m "feat(strategy): thread regime-aware selection into build"
```

---

### Task 3: Add the UI for regime-aware selection in the strategy workspace

**Files:**
- Modify: `web/src/types/strategyStudio.ts`
- Modify: `web/src/lib/api/strategyStudio.ts`
- Modify: `web/src/features/strategy-workspace/strategy-workspace-actions.tsx`
- Modify: `web/src/features/strategy-workspace/strategy-workspace-shell.tsx`
- Modify: `web/src/app/router.tsx`
- Modify: `web/src/app/route-registry.ts`
- Create: `web/src/pages/strategy/RegimeRuleSelectionPage.tsx`
- Create: `web/src/pages/strategy/RegimeRuleSelectionPage.test.tsx`
- Test: `web/src/lib/api/strategyStudio.test.ts`
- Test: `web/src/features/strategy-workspace/strategy-workspace-shell.test.tsx`

- [ ] **Step 1: Write the failing tests**

Add a `strategyStudio` API client test that verifies the strategy version detail now returns `regime_selection`.

```ts
const detail = await getStrategyVersion('sv-1');
expect(detail.item.regime_selection?.selected_rules?.[0]?.rule_id).toBe('rule_applicable');
```

Add a page test for the new selection page that verifies it renders selected, skipped, blocked, evidence, and override sections.

```tsx
renderWithRouter([{ path: '/strategies/regime-selection', element: <RegimeRuleSelectionPage /> }], ['/strategies/regime-selection']);
expect(screen.getByText('selected_rules')).toBeInTheDocument();
expect(screen.getByText('blocked_rules')).toBeInTheDocument();
```

Add a strategy workspace shell test that verifies the workspace exposes a link or CTA into the new regime-aware selection page.

```tsx
expect(screen.getByRole('link', { name: /规则选择/i })).toHaveAttribute('href', '/strategies/regime-selection');
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
./node_modules/.bin/vitest run web/src/lib/api/strategyStudio.test.ts web/src/pages/strategy/RegimeRuleSelectionPage.test.tsx web/src/features/strategy-workspace/strategy-workspace-shell.test.tsx
```

Expected: FAIL because the new route, UI component, and `regime_selection` type are not wired yet.

- [ ] **Step 3: Write the minimal implementation**

Implement:

1. `web/src/types/strategyStudio.ts` adds the `regime_selection` shape to strategy version detail.
2. `web/src/lib/api/strategyStudio.ts` continues using the existing strategy version endpoints but round-trips the new selection field.
3. `web/src/features/strategy-workspace/strategy-workspace-actions.tsx` passes the new selection inputs, including `selected_by: 'web'`, when submitting `strategy-build`.
4. `web/src/features/strategy-workspace/strategy-workspace-shell.tsx` shows the latest selection summary and links to the new page.
5. `web/src/pages/strategy/RegimeRuleSelectionPage.tsx` renders the selected / skipped / blocked rule tables, reason blocks, and override audit.
6. `web/src/app/router.tsx` registers the canonical `/strategies/regime-selection` route.
7. `web/src/app/route-registry.ts` adds the canonical route entry so navigation and breadcrumbs stay consistent.

The page should remain read-only: it shows how a strategy version was selected, but it does not make the selection itself.

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
./node_modules/.bin/vitest run web/src/lib/api/strategyStudio.test.ts web/src/pages/strategy/RegimeRuleSelectionPage.test.tsx web/src/features/strategy-workspace/strategy-workspace-shell.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/types/strategyStudio.ts web/src/lib/api/strategyStudio.ts web/src/features/strategy-workspace/strategy-workspace-actions.tsx web/src/features/strategy-workspace/strategy-workspace-shell.tsx web/src/app/router.tsx web/src/app/route-registry.ts web/src/pages/strategy/RegimeRuleSelectionPage.tsx web/src/pages/strategy/RegimeRuleSelectionPage.test.tsx web/src/lib/api/strategyStudio.test.ts web/src/features/strategy-workspace/strategy-workspace-shell.test.tsx
git commit -m "feat(strategy-ui): add regime-aware selection view"
```

---

### Task 4: Close the rollout with docs, TaskLists, and full verification

**Files:**
- Modify: `docs/New-Web-TaskList.md`
- Modify: `docs/New-Web-UI-TaskList.md`
- Modify: `docs/superpowers/specs/2026-05-19-nw-v3-sx-004-regime-aware-rule-selection-design.md` only if the implementation surfaces a contract clarification that changes the approved spec
- Modify: `daily-sessions/2026-05-19.md`
- Modify: `daily-report/2026-05-19.md`
- Test: full backend/frontend regression set touched by the feature

- [ ] **Step 1: Verify the feature against the acceptance checklist**

Confirm the implementation satisfies the spec:

```text
- different market regimes produce different selected rule sets
- blocked rules do not enter selected_rules by default
- every rule has a reason and evidence trail
- the strategy version can recover regime version and applicability profile version
- the UI can show selected / skipped / blocked / override
```

- [ ] **Step 2: Update the task lists**

Mark `NW-V3-SX-004` as complete only after the backend and UI tests pass.
Mark `UI-V3-013` as complete only after the new page and workspace link work end to end.

- [ ] **Step 3: Run the focused verification set**

Run:

```bash
python -m pytest tests/unit/services/test_regime_rule_selection_service.py tests/unit/services/test_strategy_service.py tests/unit/services/test_job_runner.py tests/pipelines/test_strategy_pipeline_spec.py tests/api/routers/ui/test_strategy_studio.py -q
./node_modules/.bin/vitest run web/src/lib/api/strategyStudio.test.ts web/src/pages/strategy/RegimeRuleSelectionPage.test.tsx web/src/features/strategy-workspace/strategy-workspace-shell.test.tsx
```

Expected: all tests pass.

- [ ] **Step 4: Record the outcome**

Update the daily session and daily report with:

- the new selection contract,
- the exact runtime path used,
- the verification commands,
- and any residual follow-up such as `NW-V3-SX-003A` or selection tuning.

- [ ] **Step 5: Commit**

```bash
git add docs/New-Web-TaskList.md docs/New-Web-UI-TaskList.md docs/superpowers/specs/2026-05-19-nw-v3-sx-004-regime-aware-rule-selection-design.md daily-sessions/2026-05-19.md daily-report/2026-05-19.md
git commit -m "docs: close regime-aware rule selection rollout"
```
