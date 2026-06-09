# Stage 11 Phase 1-3 Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 Phase 1/2/3 的 Stage 11 问题，恢复 E2E 冒烟、补齐文章分类落库与扩展字段、打通分层提取和规则自动入池。

**Architecture:** 先修最小回归面，再补数据底座，最后把提取链路接到规则池。分类结果与扩展字段由抽取流程持久化，分层提取依赖 `article_type` 和 `ArticleMetadata` 扩展字段，规则入池依赖提取结果与自动审核状态。

**Tech Stack:** Python, SQLAlchemy AsyncSession, Pydantic, pytest, Typer, Alembic.

---

### Task 1: Fix E2E regression signature drift

**Files:**
- Modify: `tests/e2e/test_full_flow.py`
- Modify: `cli/main.py`

- [ ] **Step 1: Write the failing assertion update**

Update the E2E test to expect `total_limit=4` when `_e2e_regression_async()` calls `extract_and_store_metadata()`.

- [ ] **Step 2: Run the focused test**

Run: `pytest -q tests/e2e/test_full_flow.py -q`
Expected: PASS after the assertion is updated.

- [ ] **Step 3: Keep the public callsite stable**

If needed, preserve backwards compatibility in `cli/main.py` by allowing the existing named parameter style to remain unchanged for callers outside the test.

---

### Task 2: Persist article classification results

**Files:**
- Modify: `src/agents/data_agent/skills/extract_article_metadata.py`
- Modify: `src/rule_pool/models.py`
- Modify: `src/rule_pool/repository.py`
- Test: `tests/unit/rule_pool/test_repository.py`
- Test: `tests/unit/models/test_article_metadata_extended.py`

- [ ] **Step 1: Add repository coverage**

Add tests that prove an `ArticleClassification` row can be created, fetched, and converted through the repository.

- [ ] **Step 2: Implement classification persistence**

Persist the `classify_article()` result after successful classification, instead of only writing `meta.article_type`.

- [ ] **Step 3: Keep metadata and classification aligned**

Write `article_type`, `confidence`, and the classifier reasons to the persisted classification row and keep the in-memory metadata in sync.

- [ ] **Step 4: Run repository tests**

Run: `pytest -q tests/unit/rule_pool/test_repository.py tests/unit/models/test_article_metadata_extended.py`
Expected: PASS.

---

### Task 3: Fill article metadata extension fields

**Files:**
- Modify: `src/agents/data_agent/skills/extract_article_metadata.py`
- Modify: `tests/unit/models/test_article_metadata_extended.py`
- Test: `tests/integration/test_pipeline_s7_008.py`

- [ ] **Step 1: Write the failing field population test**

Add assertions that `ArticleMetadata.extraction_version`, `standalone_rule_ids`, `derived_rule_ids`, and `trade_sample_ids` are populated during article processing.

- [ ] **Step 2: Populate the fields in the extractor**

Set `meta.extraction_version = version` and initialize the rule/sample ID lists from the extracted content.

- [ ] **Step 3: Run the metadata tests**

Run: `pytest -q tests/unit/models/test_article_metadata_extended.py`
Expected: PASS.

---

### Task 4: Split extraction by article type and auto-enqueue rules

**Files:**
- Modify: `src/agents/data_agent/skills/extract_article_metadata.py`
- Modify: `src/rule_pool/repository.py`
- Modify: `src/rule_pool/schemas.py`
- Modify: `src/rule_pool/models.py`
- Test: `tests/unit/rule_pool/test_repository.py`
- Test: `tests/integration/test_pipeline_s7_008.py`

- [ ] **Step 1: Add failing behavior tests**

Add tests that verify `rule` and `mixed` articles can produce rule IDs and that `rule_pool` rows are created from extracted rules.

- [ ] **Step 2: Implement type-aware extraction hooks**

Add deterministic post-processing based on `meta.article_type` so `rule`, `record`, and `mixed` articles can populate different metadata fields.

- [ ] **Step 3: Auto-create rule pool rows**

Create `RulePoolItem` records from extracted rules and persist them through `RulePoolRepository.create_rule()`.

- [ ] **Step 4: Run the focused tests**

Run: `pytest -q tests/unit/rule_pool/test_repository.py tests/integration/test_pipeline_s7_008.py`
Expected: PASS.

