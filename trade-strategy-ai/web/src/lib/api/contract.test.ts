import { beforeEach, describe, expect, it, vi } from 'vitest';
import { API_KEY_STORAGE_KEY } from './http';
import { getCurrentPrincipal } from './auth';
import { getSystemStatus } from './system';
import { createJob, getJob, getJobLogs, cancelJob, listJobs } from './jobs';
import { listWorkflows, getWorkflow, runWorkflow } from './workflows';
import { getArticlePipeline, runArticlePipeline } from './pipelines';
import { listArtifacts, getArtifact, downloadArtifact } from './artifacts';
import {
  downloadDailyReportHtml,
  downloadEvaluationHtml,
  getDailyReport,
  getEvaluationReport,
  listDailyReports,
  listEvaluationReports,
} from './reports';
import {
  getSettingsConfig,
  getSettingsSchema,
  listSettingsBackups,
  restoreSettingsBackup,
  saveSettings,
  validateSettingsDraft,
} from './settings';
import { listRecoveryBackups, createRecoveryBackup, restoreRecoveryBackup, recoverStaleJobs } from './ops';
import { listDataAudits } from './data-audits';
import {
  getMarketDataset,
  getMarketSnapshot,
  getMarketSnapshotQuality,
  getMarketSnapshotSection,
  getOhlcv,
  listMarketDatasets,
  listMarketSnapshotSections,
  listMarketSnapshots,
  listSymbols,
} from './market';

describe('UI API client contract', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal('fetch', vi.fn());
    const storage = new Map<string, string>();
    const localStorage = {
      clear: () => storage.clear(),
      getItem: (key: string) => storage.get(key) ?? null,
      removeItem: (key: string) => storage.delete(key),
      setItem: (key: string, value: string) => {
        storage.set(key, value);
      },
    };
    vi.stubGlobal('window', { localStorage } as never);
    localStorage.setItem(API_KEY_STORAGE_KEY, 'demo-key');
  });

  it('keeps the critical UI API paths, methods, and auth headers stable', async () => {
    vi.mocked(fetch).mockImplementation(async () =>
      new Response('{}', {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    );

    await getSystemStatus();
    await getCurrentPrincipal();
    await listJobs({ skip: 0, limit: 10 });
    await getJob('job-1');
    await getJobLogs('job-1');
    await cancelJob('job-1', 'test');
    await createJob({ job_type: 'run-pre-market', params: { date: '2026-05-10' } } as never);
    await listWorkflows();
    await getWorkflow('install-config');
    await runWorkflow('install-config', { confirmed: true } as never);
    await getArticlePipeline();
    await runArticlePipeline({
      params: { config_path: 'config/articles.yaml' },
      created_by: 'web',
      confirmed: false,
    } as never);
    await listArtifacts({ skip: 0, limit: 10 });
    await getArtifact('artifact-1');
    await downloadArtifact('artifact-1');
    await listDailyReports();
    await getDailyReport('2026-05-10');
    await listEvaluationReports();
    await getEvaluationReport('2026-05-10');
    await downloadDailyReportHtml('2026-05-10');
    await downloadEvaluationHtml('2026-05-10');
    await getSettingsConfig('config/app.yaml');
    await getSettingsSchema('config/app.yaml');
    await validateSettingsDraft({ config_path: 'config/app.yaml', draft: {} } as never);
    await saveSettings({ config_path: 'config/app.yaml', draft: {}, confirmed: true } as never);
    await listSettingsBackups('config/app.yaml');
    await restoreSettingsBackup({
      config_path: 'config/app.yaml',
      backup_path: 'data/backups/app.yaml',
      confirmed: true,
    } as never);
    await listRecoveryBackups();
    await createRecoveryBackup({ include_processed: true } as never);
    await restoreRecoveryBackup({
      backup_path: 'data/backups/app.yaml',
      include_processed: true,
      confirmed: true,
    } as never);
    await recoverStaleJobs({ stale_before_minutes: 12 } as never);
    await listDataAudits({ entity_type: 'backup', limit: 10 });
    await listSymbols('000001', 50);
    await getOhlcv('000001.SZ', '2026-05-01', '2026-05-10');
    await listMarketSnapshots({ tradeDate: '2026-05-16', market: 'cn', limit: 10, offset: 0 });
    await getMarketSnapshot('snapshot-001');
    await listMarketSnapshotSections('snapshot-001', 20, 0);
    await getMarketSnapshotSection('snapshot-001', 'overview', { limit: 10, offset: 0 });
    await listMarketDatasets({ tradeDate: '2026-05-16', market: 'cn', limit: 10, offset: 0 });
    await getMarketDataset('dataset-001', 10, 0);
    await getMarketSnapshotQuality('snapshot-001');

    const calls = vi.mocked(fetch).mock.calls.map(([url, init]) => ({
      url: String(url),
      method: init?.method ?? 'GET',
      headers: init?.headers instanceof Headers ? init.headers : new Headers(init?.headers),
      body: init?.body,
    }));

    const findCall = (url: string, method = 'GET') =>
      calls.find((call) => call.url === url && call.method === method);

    const expectJsonBody = (url: string, method: string, expected: Record<string, unknown>) => {
      const call = findCall(url, method);
      expect(call).toBeTruthy();
      expect(call?.headers.get('Content-Type')).toBe('application/json');
      expect(JSON.parse(String(call?.body))).toEqual(expected);
    };

    expect(findCall('/api/ui/v1/system/status')).toBeTruthy();
    expect(findCall('/api/ui/v1/auth/me')).toBeTruthy();
    expect(findCall('/api/ui/v1/jobs?skip=0&limit=10')).toBeTruthy();
    expect(findCall('/api/ui/v1/jobs/job-1')).toBeTruthy();
    expect(findCall('/api/ui/v1/jobs/job-1/logs')).toBeTruthy();
    expectJsonBody('/api/ui/v1/jobs/job-1/cancel', 'POST', { reason: 'test' });
    expectJsonBody('/api/ui/v1/jobs', 'POST', {
      job_type: 'run-pre-market',
      params: { date: '2026-05-10' },
    });
    expect(findCall('/api/ui/v1/workflows')).toBeTruthy();
    expect(findCall('/api/ui/v1/workflows/install-config')).toBeTruthy();
    expectJsonBody('/api/ui/v1/workflows/install-config/run', 'POST', { confirmed: true });
    expect(findCall('/api/ui/v1/pipelines/article_pipeline')).toBeTruthy();
    expectJsonBody('/api/ui/v1/pipelines/article_pipeline/run', 'POST', {
      params: { config_path: 'config/articles.yaml' },
      created_by: 'web',
      confirmed: false,
    });
    expect(findCall('/api/ui/v1/artifacts?skip=0&limit=10')).toBeTruthy();
    expect(findCall('/api/ui/v1/artifacts/artifact-1')).toBeTruthy();
    expect(findCall('/api/ui/v1/artifacts/artifact-1/download')).toBeTruthy();
    expect(findCall('/reports/daily?skip=0&limit=50')).toBeTruthy();
    expect(findCall('/reports/daily/2026-05-10')).toBeTruthy();
    expect(findCall('/reports/evaluation?skip=0&limit=50')).toBeTruthy();
    expect(findCall('/reports/evaluation/2026-05-10')).toBeTruthy();
    expect(findCall('/reports/daily/2026-05-10/html')).toBeTruthy();
    expect(findCall('/reports/evaluation/2026-05-10/html')).toBeTruthy();
    expect(findCall('/api/ui/v1/settings/config?config_path=config%2Fapp.yaml')).toBeTruthy();
    expect(findCall('/api/ui/v1/settings/schema?config_path=config%2Fapp.yaml')).toBeTruthy();
    expectJsonBody('/api/ui/v1/settings/validate', 'POST', { config_path: 'config/app.yaml', draft: {} });
    expectJsonBody('/api/ui/v1/settings/save', 'POST', { config_path: 'config/app.yaml', draft: {}, confirmed: true });
    expect(findCall('/api/ui/v1/settings/backups?config_path=config%2Fapp.yaml')).toBeTruthy();
    expectJsonBody('/api/ui/v1/settings/restore', 'POST', {
      config_path: 'config/app.yaml',
      backup_path: 'data/backups/app.yaml',
      confirmed: true,
    });
    expect(findCall('/api/ui/v1/ops/backups')).toBeTruthy();
    expectJsonBody('/api/ui/v1/ops/backup', 'POST', { include_processed: true });
    expectJsonBody('/api/ui/v1/ops/restore', 'POST', {
      backup_path: 'data/backups/app.yaml',
      include_processed: true,
      confirmed: true,
    });
    expectJsonBody('/api/ui/v1/ops/recover-stale', 'POST', { stale_before_minutes: 12 });
    expect(findCall('/api/ui/v1/data-audits?entity_type=backup&limit=10')).toBeTruthy();
    expect(findCall('/api/ui/v1/market/symbols?q=000001&limit=50')).toBeTruthy();
    expect(findCall('/api/ui/v1/market/ohlcv?symbol=000001.SZ&start_date=2026-05-01&end_date=2026-05-10')).toBeTruthy();
    expect(findCall('/api/ui/v1/market/snapshots?trade_date=2026-05-16&market=cn&limit=10&offset=0')).toBeTruthy();
    expect(findCall('/api/ui/v1/market/snapshots/snapshot-001')).toBeTruthy();
    expect(findCall('/api/ui/v1/market/snapshots/snapshot-001/sections?limit=20&offset=0')).toBeTruthy();
    expect(findCall('/api/ui/v1/market/snapshots/snapshot-001/sections/overview?limit=10&offset=0')).toBeTruthy();
    expect(findCall('/api/ui/v1/market/datasets?trade_date=2026-05-16&market=cn&limit=10&offset=0')).toBeTruthy();
    expect(findCall('/api/ui/v1/market/datasets/dataset-001?limit=10&offset=0')).toBeTruthy();
    expect(findCall('/api/ui/v1/market/snapshots/snapshot-001/quality')).toBeTruthy();

    for (const call of calls) {
      expect(call.headers.get('X-API-Key')).toBe('demo-key');
    }
  });
});
