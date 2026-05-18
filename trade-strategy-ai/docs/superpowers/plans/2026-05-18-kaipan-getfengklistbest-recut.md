# Kaipan GetFengKListBest Recut Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Kaipan 的“收盘强势标的”入口统一改为 `GetFengKListBest`，并同步收口数据抓取、快照构建、schema、UI 文案和测试。

**Architecture:** 保留现有 `/kaipan` 入口和 `get_feng_k_list` 数据集语义，但把底层 canonical API 改成 `GetFengKListBest`，因为它提供股票强度字段且与当前解析逻辑一致。快照层和 UI 只消费标准化后的 `strength_score` 结果，不再暴露旧的明细接口名。

**Tech Stack:** Python、Pytest、YAML schema、TypeScript、Vitest

---

### Task 1: Provider request/normalize recut

**Files:**
- Modify: `src/providers/kaipan_provider.py`
- Modify: `src/providers/kaipan_schema/get_feng_k_list.yaml`
- Test: `tests/unit/providers/test_kaipan_provider.py`
- Test: `tests/providers/test_kaipan_pipeline.py`

- [ ] **Step 1: Write the failing test**

```python
def test_get_feng_k_list_uses_best_endpoint_and_strength_fields(tmp_path):
    provider = _build_provider(tmp_path)
    captured = []

    def fake_fetch_and_save(**kwargs):
        captured.append(kwargs)
        return {"List": [["000001", "示例", 88.0, "", 4.5, 1000.0, None, None, 120.0, 80.0, "题材A"]]}

    provider._fetch_and_save = fake_fetch_and_save
    payload = provider.fetch_get_feng_k_list(trade_date=date(2026, 4, 22), slot="17-30")

    assert captured[0]["api_name"] == "GetFengKListBest"
    assert payload["items"][0]["strength_score"] == 88.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/providers/test_kaipan_provider.py tests/providers/test_kaipan_pipeline.py -q`
Expected: FAIL because the endpoint is still `GetFengKList`.

- [ ] **Step 3: Write minimal implementation**

```python
def _request_get_feng_k_list(...):
    return self._fetch_and_save(
        dataset="get_feng_k_list",
        api_name="GetFengKListBest",
        controller="StockFengKData",
        base_url_key=self._resolve_history_or_today_url(...),
        method="POST",
        canonical_name="get_feng_k_list",
        Day=td.strftime("%Y%m%d"),
        Time=time_value,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/providers/test_kaipan_provider.py tests/providers/test_kaipan_pipeline.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/providers/kaipan_provider.py src/providers/kaipan_schema/get_feng_k_list.yaml tests/unit/providers/test_kaipan_provider.py tests/providers/test_kaipan_pipeline.py
git commit -m "fix(kaipan): use best fengk endpoint"
```

### Task 2: Snapshot builder and UI wording

**Files:**
- Modify: `src/services/market_snapshot_builders.py`
- Modify: `web/src/features/kaipan/kaipan-center.tsx`
- Modify: `web/src/pages/kaipan/index.tsx`
- Test: `tests/unit/services/test_market_snapshot_builders.py`
- Test: `web/src/pages/kaipan/index.test.tsx`

- [ ] **Step 1: Write the failing test**

```python
def test_get_feng_k_list_section_uses_best_label(tmp_path):
    ...
    assert section.section_id == "strong_fengkou_best"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/services/test_market_snapshot_builders.py -q`
Expected: FAIL because section_id and label are still旧名。

- [ ] **Step 3: Write minimal implementation**

```python
class GetFengKListSectionBuilder:
    section_id: str = "strong_fengkou_best"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/services/test_market_snapshot_builders.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/services/market_snapshot_builders.py web/src/features/kaipan/kaipan-center.tsx web/src/pages/kaipan/index.tsx tests/unit/services/test_market_snapshot_builders.py web/src/pages/kaipan/index.test.tsx
git commit -m "feat(kaipan): recut fengk best section"
```

### Task 3: Docs and session sync

**Files:**
- Modify: `docs/kaipan.md`
- Modify: `daily-sessions/2026-05-18.md`
- Modify: `daily-report/2026-05-18.md`
- Modify: `docs/New-Web-Linked-TaskLists/New-Web-TaskList.md`

- [ ] **Step 1: Write the failing test**

```text
人工核对：文档、TaskList、日报与 session 中不再出现把 `get_feng_k_list` 说成 `GetFengKList` 的旧语义。
```

- [ ] **Step 2: Run test to verify it fails**

Run: `git diff --check`
Expected: PASS after文案对齐。

- [ ] **Step 3: Write minimal implementation**

```md
- 将 `GetFengKList` 相关说明改为 `GetFengKListBest`。
- 保留 `get_feng_k_list` 作为数据集/快照 id，不新增第二入口。
```

- [ ] **Step 4: Run test to verify it passes**

Run: `git diff --check`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/kaipan.md daily-sessions/2026-05-18.md daily-report/2026-05-18.md docs/New-Web-Linked-TaskLists/New-Web-TaskList.md
git commit -m "docs(kaipan): align fengk best naming"
```
