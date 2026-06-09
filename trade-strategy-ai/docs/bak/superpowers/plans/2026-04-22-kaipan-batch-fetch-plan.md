# Kaipan Batch Fetch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone batch script that fetches the recent 30 trading days of Kaipan data with actionable logs, records, and summary output for `NTL-S0-011`.

**Architecture:** Keep the batch runner in `scripts/kaipan_batch_fetch.py` and reuse `KaipanProvider.fetch_custom()` for every request. The script should own date selection, job planning, paging, logging, and output files, while the provider stays responsible for HTTP, retry, and raw JSON persistence. The default run should cover the 8 core interfaces required by `NTL-S0-011`, with auxiliary interfaces behind an explicit flag.

**Tech Stack:** Python, `argparse`, `logging`, `pandas`, `AkShare` fallback, existing `KaipanProvider`, JSONL/JSON file outputs, `pytest`.

---

### Task 1: Align the default job set with `NTL-S0-011`

**Files:**
- Modify: `scripts/kaipan_batch_fetch.py`
- Test: `tests/unit/scripts/test_kaipan_batch_fetch.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_jobs_defaults_to_eight_core_interfaces():
    jobs = build_jobs(include_auxiliary=False, morning_pid_types=(0,), max_pages=2)
    assert [job.name for job in jobs] == [
        "board_strength",
        "industry_ranking",
        "concept_fengkou",
        "theme_detail",
        "stock_sector_v2",
        "strong_fengkou",
        "interval_stats_stock",
        "morning_bidding_list_pid0",
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/scripts/test_kaipan_batch_fetch.py::test_build_jobs_defaults_to_eight_core_interfaces -v`
Expected: FAIL because the current default job set still includes extra interfaces.

- [ ] **Step 3: Write minimal implementation**

Update `build_jobs()` so the default run includes only the 8 core interfaces. Move `limit_up_reason`, `pre_market_bid`, `pre_market_stats`, `limit_up_info`, and `lhb_list` behind `include_auxiliary=True`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/scripts/test_kaipan_batch_fetch.py::test_build_jobs_defaults_to_eight_core_interfaces -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/kaipan_batch_fetch.py tests/unit/scripts/test_kaipan_batch_fetch.py
git commit -m "feat: align kaipan batch fetch jobs with ntl-s0-011"
```

### Task 2: Add deterministic date selection tests

**Files:**
- Modify: `scripts/kaipan_batch_fetch.py`
- Test: `tests/unit/scripts/test_kaipan_batch_fetch.py`

- [ ] **Step 1: Write the failing test**

```python
def test_get_recent_trading_dates_falls_back_to_weekdays(monkeypatch):
    monkeypatch.setattr("scripts.kaipan_batch_fetch._load_recent_trading_dates_from_akshare", lambda **kwargs: None)
    dates = get_recent_trading_dates(end_date=date(2026, 4, 22), count=5)
    assert dates == [
        date(2026, 4, 16),
        date(2026, 4, 17),
        date(2026, 4, 20),
        date(2026, 4, 21),
        date(2026, 4, 22),
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/scripts/test_kaipan_batch_fetch.py::test_get_recent_trading_dates_falls_back_to_weekdays -v`
Expected: FAIL if fallback behavior is not covered.

- [ ] **Step 3: Write minimal implementation**

Keep the weekday fallback and make sure the helper returns the exact requested count in ascending order.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/scripts/test_kaipan_batch_fetch.py::test_get_recent_trading_dates_falls_back_to_weekdays -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/kaipan_batch_fetch.py tests/unit/scripts/test_kaipan_batch_fetch.py
git commit -m "test: cover kaipan trading date fallback"
```

### Task 3: Verify the batch runner and output contract

**Files:**
- Modify: `scripts/kaipan_batch_fetch.py`
- Test: `tests/unit/scripts/test_kaipan_batch_fetch.py`

- [ ] **Step 1: Write the failing test**

```python
def test_run_batch_fetch_dry_run_writes_summary(tmp_path, monkeypatch):
    # monkeypatch config loading and trading-date selection
    # assert summary.json is written and includes the planned job names
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/scripts/test_kaipan_batch_fetch.py -v`
Expected: FAIL until the dry-run summary contract is asserted.

- [ ] **Step 3: Write minimal implementation**

Ensure dry-run emits `summary.json`, logs the plan, and records the requested trading-date range without making HTTP requests.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/scripts/test_kaipan_batch_fetch.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/kaipan_batch_fetch.py tests/unit/scripts/test_kaipan_batch_fetch.py
git commit -m "test: validate kaipan batch runner output"
```
