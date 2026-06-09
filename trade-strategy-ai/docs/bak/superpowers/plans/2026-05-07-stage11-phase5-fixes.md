# Stage 11 Phase 5 Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 收口 Stage 11 E2E 冒烟、归档非核心文档、补齐 Stage 8 A 股风控设计说明，使代码、测试和文档状态一致。

**Architecture:** 先修测试链路的真实导入/异步契约问题，确保 E2E smoke 可以稳定收集并执行；再把 `docs/` 根目录的非核心文档按 TaskList 口径归档；最后把 A 股风控约束抽象成独立设计文档，作为 `metrics_calculator` 与回测评分的说明层。

**Tech Stack:** Python, pytest, Typer, Markdown.

---

### Task 1: Stabilize Stage 11 E2E smoke

**Files:**
- Modify: `src/backup/service.py`
- Modify: `tests/integration/test_pipeline_s7_008.py`
- Test: `tests/e2e/test_full_flow.py`
- Test: `tests/integration/test_pipeline_s7_008.py`

- [x] **Step 1: Fix the failing import path**

`src/backup/service.py` should import the real model export used by `src.models.__init__` instead of the missing `MarketData` symbol.

- [x] **Step 2: Align async mocks with the service contract**

Use `AsyncMock` for `strategy_library_service.get_current_released_version()` in the Stage 11 pre-market integration test so the test awaits a real async callable.

- [x] **Step 3: Run the focused E2E smoke**

Run: `pytest -q tests/e2e/test_full_flow.py tests/integration/test_pipeline_s7_008.py -q`
Expected: PASS.

### Task 2: Archive non-core docs for NTL-S0-005

**Files:**
- Keep: `docs/UserManual.md`
- Move: `docs/Deprecated/api.md`
- Move: `docs/bak/crawl.md`
- Move: `docs/bak/db-struct.md`
- Move: `docs/bak/kaipan.md`
- Move: `docs/bak/kaipan_CLI.md`
- Move: `docs/bak/trader-memory-schema.md`

- [x] **Step 1: Move the non-core docs into `docs/bak/` and `docs/Deprecated/`**

Keep `Project.md`, `Plan.md`, `需求.md`, `TaskList.md`, `Kaipan-Interface-Mapping.md`, and `UserManual.md` at the docs root; archive the rest into `docs/bak/` or `docs/Deprecated/` as appropriate.

- [x] **Step 2: Re-scan the root docs directory**

Confirm the root only contains the current keepers plus directory entries like `bak/`, `Deprecated/`, `review/`, and `superpowers/`.

### Task 3: Add Stage 8 A-share risk-control design doc

**Files:**
- Create: `docs/superpowers/specs/2026-05-07-stage8-a-share-risk-control-design.md`

- [x] **Step 1: Write the design document**

Describe the `TradeConstraint` model, `board_type` inference, limit-price logic, price-cage logic, and the current test coverage boundaries.

- [x] **Step 2: Self-review for consistency**

Make sure the doc matches the current implementation: ETF is T+0 with 10% limits, convertible bonds are T+0 with no limit, and the remaining gap is still non-matching execution simulation.

- [x] **Step 3: Keep the doc concise and reviewable**

The document should be specific enough to explain the implemented behavior without duplicating the entire module code.
