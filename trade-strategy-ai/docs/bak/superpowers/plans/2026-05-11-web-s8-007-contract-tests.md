# WEB-S8-007 Contract Test Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a lightweight contract test layer that detects UI API path, method, and payload drift between the backend OpenAPI schema and the Web client.

**Architecture:** Keep the contract surface small and explicit. The backend test will pin the critical `/api/ui/v1` routes and their request/response envelopes. The frontend test will pin the exported API client functions to the exact paths, methods, query strings, and JSON payloads that the Web app relies on. No code generation is introduced in this stage.

**Tech Stack:** Python `pytest`, FastAPI OpenAPI, TypeScript `vitest`, existing Web API client modules.

---

### Task 1: Pin the backend UI OpenAPI contract

**Files:**
- Create: `trade-strategy-ai/tests/api/test_ui_openapi_contract.py`

- [ ] **Step 1: Write the failing test**

```python
"""UI OpenAPI 契约测试。"""

from __future__ import annotations

from api.main import app


def test_ui_openapi_exposes_critical_contract_paths() -> None:
    """UI 层关键路由必须稳定暴露。"""
    paths = set(app.openapi()["paths"])

    assert "/api/ui/v1/system/status" in paths
    assert "/api/ui/v1/auth/me" in paths
    assert "/api/ui/v1/jobs" in paths
    assert "/api/ui/v1/jobs/{job_id}" in paths
    assert "/api/ui/v1/jobs/{job_id}/logs" in paths
    assert "/api/ui/v1/workflows" in paths
    assert "/api/ui/v1/workflows/{workflow_id}" in paths
    assert "/api/ui/v1/workflows/{workflow_id}/run" in paths
    assert "/api/ui/v1/artifacts" in paths
    assert "/api/ui/v1/artifacts/{artifact_id}" in paths
    assert "/api/ui/v1/artifacts/{artifact_id}/download" in paths
    assert "/api/ui/v1/reports/daily" in paths
    assert "/api/ui/v1/reports/daily/{date}" in paths
    assert "/api/ui/v1/reports/evaluation" in paths
    assert "/api/ui/v1/reports/evaluation/{date}" in paths
    assert "/api/ui/v1/settings/config" in paths
    assert "/api/ui/v1/settings/schema" in paths
    assert "/api/ui/v1/settings/validate" in paths
    assert "/api/ui/v1/settings/save" in paths
    assert "/api/ui/v1/settings/backups" in paths
    assert "/api/ui/v1/settings/restore" in paths
    assert "/api/ui/v1/market/symbols" in paths
    assert "/api/ui/v1/market/ohlcv" in paths
```

- [ ] **Step 2: Run the test to verify it fails first**

Run: `pytest -q trade-strategy-ai/tests/api/test_ui_openapi_contract.py`
Expected: FAIL until the file exists and the assertions are in place.

- [ ] **Step 3: Minimal implementation**

Use the existing `api.main.app` OpenAPI export directly; no new runtime code is needed.

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest -q trade-strategy-ai/tests/api/test_ui_openapi_contract.py`
Expected: PASS.

### Task 2: Pin the Web API client contract

**Files:**
- Create: `trade-strategy-ai/web/src/lib/api/contract.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { API_KEY_STORAGE_KEY } from './http';
import { getSystemStatus } from './system';
import { listJobs, getJob, getJobLogs, cancelJob, createJob } from './jobs';
import { listWorkflows, getWorkflow, runWorkflow } from './workflows';
import { listArtifacts, getArtifact, downloadArtifact } from './artifacts';
import { listDailyReports, getDailyReport, listEvaluationReports, getEvaluationReport, downloadDailyReportHtml, downloadEvaluationHtml } from './reports';
import { getSettingsConfig, getSettingsSchema, validateSettingsDraft, saveSettings, listSettingsBackups, restoreSettingsBackup } from './settings';
import { getMarketSymbols, getOhlcv } from './market';
import { getCurrentPrincipal } from './auth';

describe('UI API client contract', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal('fetch', vi.fn());
    window.localStorage.clear();
    window.localStorage.setItem(API_KEY_STORAGE_KEY, 'demo-key');
  });

  it('keeps the critical UI API paths and methods stable', async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: true, json: async () => ({}) } as Response);

    await Promise.all([
      getSystemStatus(),
      getCurrentPrincipal(),
      listJobs({ skip: 0, limit: 10 }),
      getJob('job-1'),
      getJobLogs('job-1'),
      cancelJob('job-1', 'test'),
      createJob({ job_type: 'run-pre-market', params: { date: '2026-05-10' } } as never),
      listWorkflows(),
      getWorkflow('install-config'),
      runWorkflow('install-config', { confirmed: true } as never),
      listArtifacts({ skip: 0, limit: 10 }),
      getArtifact('artifact-1'),
      downloadArtifact('artifact-1'),
      listDailyReports(),
      getDailyReport('2026-05-10'),
      listEvaluationReports(),
      getEvaluationReport('2026-05-10'),
      downloadDailyReportHtml('2026-05-10'),
      downloadEvaluationHtml('2026-05-10'),
      getSettingsConfig('config/app.yaml'),
      getSettingsSchema('config/app.yaml'),
      validateSettingsDraft({ config_path: 'config/app.yaml', draft: {} } as never),
      saveSettings({ config_path: 'config/app.yaml', draft: {}, confirmed: true } as never),
      listSettingsBackups('config/app.yaml'),
      restoreSettingsBackup({ config_path: 'config/app.yaml', backup_path: 'data/backups/app.yaml', confirmed: true } as never),
      getMarketSymbols(),
      getOhlcv({ symbol: '000001.SZ' }),
    ]);

    const urls = vi.mocked(fetch).mock.calls.map(([url]) => url);
    expect(urls).toContain('/api/ui/v1/system/status');
    expect(urls).toContain('/api/ui/v1/auth/me');
    expect(urls).toContain('/api/ui/v1/jobs?skip=0&limit=10');
    expect(urls).toContain('/api/ui/v1/jobs/job-1');
    expect(urls).toContain('/api/ui/v1/jobs/job-1/logs');
    expect(urls).toContain('/api/ui/v1/jobs/job-1/cancel');
    expect(urls).toContain('/api/ui/v1/jobs');
    expect(urls).toContain('/api/ui/v1/workflows');
    expect(urls).toContain('/api/ui/v1/workflows/install-config');
    expect(urls).toContain('/api/ui/v1/workflows/install-config/run');
    expect(urls).toContain('/api/ui/v1/artifacts?skip=0&limit=10');
    expect(urls).toContain('/api/ui/v1/artifacts/artifact-1');
    expect(urls).toContain('/api/ui/v1/artifacts/artifact-1/download');
    expect(urls).toContain('/api/ui/v1/reports/daily?skip=0&limit=50');
    expect(urls).toContain('/api/ui/v1/reports/daily/2026-05-10');
    expect(urls).toContain('/api/ui/v1/reports/evaluation?skip=0&limit=50');
    expect(urls).toContain('/api/ui/v1/reports/evaluation/2026-05-10');
    expect(urls).toContain('/api/ui/v1/reports/daily/2026-05-10/html');
    expect(urls).toContain('/api/ui/v1/reports/evaluation/2026-05-10/html');
    expect(urls).toContain('/api/ui/v1/settings/config?configPath=config%2Fapp.yaml');
    expect(urls).toContain('/api/ui/v1/settings/schema?configPath=config%2Fapp.yaml');
    expect(urls).toContain('/api/ui/v1/settings/validate');
    expect(urls).toContain('/api/ui/v1/settings/save');
    expect(urls).toContain('/api/ui/v1/settings/backups?configPath=config%2Fapp.yaml');
    expect(urls).toContain('/api/ui/v1/settings/restore');
    expect(urls).toContain('/api/ui/v1/market/symbols');
    expect(urls).toContain('/api/ui/v1/market/ohlcv?symbol=000001.SZ');
  });
});
```

- [ ] **Step 2: Run the test to verify it fails first**

Run: `./node_modules/.bin/vitest run src/lib/api/contract.test.ts`
Expected: FAIL until the test file exists and the API call expectations are correct.

- [ ] **Step 3: Minimal implementation**

No production code changes are required. If a client path is wrong, fix the client module itself instead of relaxing the assertion.

- [ ] **Step 4: Run the test to verify it passes**

Run: `./node_modules/.bin/vitest run src/lib/api/contract.test.ts`
Expected: PASS.

### Task 3: Update task status

**Files:**
- Modify: `trade-strategy-ai/docs/Web-TaskList.md`

- [ ] **Step 1: Mark `WEB-S8-007` complete**

Update the completion line for `WEB-S8-007` to describe the new backend OpenAPI regression test and Web client contract test.

- [ ] **Step 2: Run the relevant verification commands**

Run:
`pytest -q trade-strategy-ai/tests/api/test_ui_openapi_contract.py`
`./node_modules/.bin/vitest run src/lib/api/contract.test.ts`

Expected: both pass.

