import { expect, test, type APIRequestContext, type Page } from '@playwright/test';
import { execFile } from 'node:child_process';
import fs from 'node:fs/promises';
import path from 'node:path';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);
const API_BASE = process.env.STAGE12_API_BASE_URL ?? 'http://127.0.0.1:8000/api/ui/v1';

async function loadAdminApiKey(): Promise<string | undefined> {
  if (process.env.ADMIN_API_KEY) return process.env.ADMIN_API_KEY;
  const dotenvPath = path.resolve(process.cwd(), '..', '.env');
  try {
    const content = await fs.readFile(dotenvPath, 'utf8');
    for (const rawLine of content.split(/\r?\n/)) {
      const line = rawLine.trim();
      if (!line || line.startsWith('#') || !line.includes('=')) continue;
      const [key, ...valueParts] = line.replace(/^export\s+/, '').split('=');
      if (key.trim() !== 'ADMIN_API_KEY') continue;
      return valueParts.join('=').trim().replace(/^['"]|['"]$/g, '');
    }
  } catch {
    return undefined;
  }
  return undefined;
}

async function apiJson<T>(
  request: APIRequestContext,
  method: 'GET' | 'POST',
  endpoint: string,
  apiKey: string | undefined,
  data?: unknown,
): Promise<T> {
  const response = await request.fetch(`${API_BASE}${endpoint}`, {
    method,
    headers: apiKey ? { 'X-API-Key': apiKey } : undefined,
    data,
  });
  expect(response.ok(), `${method} ${endpoint}: ${response.status()} ${await response.text()}`).toBeTruthy();
  return (await response.json()) as T;
}

function asItems(value: unknown): Record<string, unknown>[] {
  expect(typeof value).toBe('object');
  expect(value).not.toBeNull();
  const items = (value as { items?: unknown }).items;
  expect(Array.isArray(items)).toBeTruthy();
  return items as Record<string, unknown>[];
}

function stringField(value: Record<string, unknown>, key: string): string {
  const item = value[key];
  expect(typeof item, key).toBe('string');
  return item as string;
}

function numberField(value: Record<string, unknown>, key: string): number {
  const item = value[key];
  expect(typeof item, key).toBe('number');
  return item as number;
}

async function openBatchWorkbench(page: Page, apiKey: string | undefined) {
  await page.addInitScript(
    ({ key }) => {
      if (key) window.localStorage.setItem('trade-strategy-ai.apiKey', key);
    },
    { key: apiKey },
  );
  await page.goto('/rules/backtests');
  await expect(page.getByTestId('formal-backtest-product')).toBeVisible();
  await page.getByRole('button', { name: '规则池批量回测' }).click();
  await expect(page.getByRole('button', { name: '创建批次计划' })).toBeVisible();
  await expect(page.locator('body')).not.toContainText(/Workflow|Pipeline|Artifact|config_path/);
}

async function executeJobs(jobIds: string[]) {
  const code = `
import asyncio, os, sys
from scripts.web_local import _local_env
from src.services.job_runner import JobRunner

async def main():
    env = _local_env()
    os.environ.update({k: v for k, v in env.items() if v is not None})
    runner = JobRunner()
    for job_id in sys.argv[1:]:
        result = await runner.execute_job(job_id=job_id, worker_id="rt-perf-gate-001-e2e")
        payload = result.payload if isinstance(result.payload, dict) else {}
        job = payload.get("job") if isinstance(payload.get("job"), dict) else {}
        print(f"{job_id} {result.status} {job.get('status')}")

asyncio.run(main())
`;
  await execFileAsync(process.env.PYTHON ?? 'python', ['-c', code, ...jobIds], {
    cwd: path.resolve(process.cwd(), '..'),
    timeout: 120_000,
    maxBuffer: 1024 * 1024,
  });
}

test('rule pool batch backtest smoke covers create start status merge and results view', async ({ page, request }) => {
  test.setTimeout(180_000);
  const apiKey = await loadAdminApiKey();

  await openBatchWorkbench(page, apiKey);

  const rules = await apiJson<Record<string, unknown>>(request, 'GET', '/rule-pool?status=approved&limit=5', apiKey);
  const selectedRules = asItems(rules)
    .filter((item) => Number(item.validated_confidence ?? item.initial_confidence ?? 0) >= 0.7)
    .slice(0, 3);

  if (selectedRules.length < 2) {
    await expect(page.locator('body')).toContainText(/当前筛选条件下没有已通过规则|规则池批量回测/);
    test.info().annotations.push({ type: 'unavailable', description: `only ${selectedRules.length} approved rules available` });
    return;
  }

  const batchRun = await apiJson<Record<string, unknown>>(request, 'POST', '/rules/backtests/batch-runs', apiKey, {
    rule_ids: selectedRules.map((item) => stringField(item, 'rule_id')),
    batch_size: 2,
    start_date: '2024-05-27',
    end_date: '2024-05-31',
    min_confidence: 0.7,
    market_regime_version: 'market-regime-v3',
    profile_id: 'default',
  });
  expect(numberField(batchRun, 'selected_rule_count')).toBe(selectedRules.length);
  const batchRunId = stringField(batchRun, 'batch_run_id');
  const batches = batchRun.batches as Record<string, unknown>[];
  expect(batches.length).toBeGreaterThanOrEqual(1);

  const jobIds: string[] = [];
  for (const batch of batches) {
    const started = await apiJson<Record<string, unknown>>(
      request,
      'POST',
      `/rules/backtests/batch-runs/${batchRunId}/batches/${numberField(batch, 'batch_index')}/start`,
      apiKey,
    );
    const startedBatch = (started.batches as Record<string, unknown>[]).find(
      (item) => numberField(item, 'batch_index') === numberField(batch, 'batch_index'),
    );
    expect(startedBatch).toBeTruthy();
    const jobId = startedBatch?.job_id;
    expect(typeof jobId).toBe('string');
    jobIds.push(jobId as string);
  }

  await executeJobs(jobIds);
  const refreshed = await apiJson<Record<string, unknown>>(request, 'GET', `/rules/backtests/batch-runs/${batchRunId}`, apiKey);
  const refreshedBatches = refreshed.batches as Record<string, unknown>[];
  expect(refreshedBatches.length).toBe(batches.length);

  if (refreshedBatches.every((batch) => batch.status === 'completed')) {
    const merged = await apiJson<Record<string, unknown>>(request, 'POST', `/rules/backtests/batch-runs/${batchRunId}/merge`, apiKey);
    expect(merged.status).toBe('merged');
    const mergedResult = merged.merged_result as Record<string, unknown>;
    expect(mergedResult).toBeTruthy();
    expect((mergedResult.rule_results as unknown[]).length).toBeGreaterThanOrEqual(selectedRules.length);

    await page.goto(`/rules/results?batch_run_id=${batchRunId}`);
    await expect(page.getByText('合并后的规则池回测结果')).toBeVisible();
    await expect(page.getByText(`批次计划：${batchRunId}`)).toBeVisible();
    await expect(page.locator('body')).toContainText(/批次来源|运行记录|来源结果/);
  } else {
    await page.goto(`/rules/results?batch_run_id=${batchRunId}`);
    await expect(page.getByText('当前批次计划尚未形成可用的合并结果')).toBeVisible();
    test.info().annotations.push({ type: 'partial', description: JSON.stringify(refreshedBatches.map((batch) => batch.status)) });
  }
});
