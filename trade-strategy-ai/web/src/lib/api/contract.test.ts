import { beforeEach, describe, expect, it, vi } from 'vitest';
import { API_KEY_STORAGE_KEY } from './http';
import { getCurrentPrincipal } from './auth';
import { getSystemStatus } from './system';
import { createJob, getJob, getJobDefinition, getJobLogs, cancelJob, pauseJob, resumeJob, retryJob, listJobs, listJobDefinitions } from './jobs';
import { listWorkflows, getWorkflow, runWorkflow } from './workflows';
import {
  getArticlePipeline,
  getArticlePipelineScheduleStatus,
  runArticlePipeline,
  runArticlePipelineStep,
  startArticlePipelineSchedule,
  stopArticlePipelineSchedule,
} from './pipelines';
import { listArtifacts, listArtifactFilterOptions, getArtifact, downloadArtifact } from './artifacts';
import { listArticleFilterOptions, listArticles } from './articles';
import {
  archiveProfile,
  getProfile,
  getProfileEdit,
  getProfileSnapshot,
  importProfile,
  listProfiles,
  updateProfile,
  validateProfileUpdate,
} from './profiles';
import {
  downloadDailyReportHtml,
  downloadEvaluationHtml,
  getDailyReport,
  getEvaluationReport,
  listDailyReports,
  listEvaluationReports,
} from './reports';
import { listRecoveryBackups, listRecoveryBackupTargets, createRecoveryBackup, restoreRecoveryBackup, recoverStaleJobs } from './ops';
import { listDataAudits } from './data-audits';
import {
  getMarketDataset,
  getMarketSnapshot,
  getMarketSnapshotQuality,
  getMarketSnapshotSection,
  getOhlcv,
  getOhlcvSchedulerStatus,
  listMarketDatasets,
  listMarketSnapshotSections,
  listMarketSnapshots,
  listSymbols,
  runOhlcvScheduler,
  stopOhlcvScheduler,
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
    await listJobDefinitions();
    await getJobDefinition('pipeline-run');
    await getJob('job-1');
    await getJobLogs('job-1');
    await cancelJob('job-1', 'test');
    await pauseJob('job-1', 'test');
    await resumeJob('job-1');
    await retryJob('job-1', 'test');
    await createJob({ job_type: 'run-pre-market', params: { date: '2026-05-10' } } as never);
    await listWorkflows();
    await getWorkflow('pipeline');
    await runWorkflow('pipeline', { confirmed: true } as never);
    await getArticlePipeline();
    await getArticlePipelineScheduleStatus();
    await listArticles({
      page: 2,
      page_size: 20,
      author_id: 'author-1',
      source: 'tgb',
      trader_id: 'trader-1',
      published_after: '2026-05-01T00:00:00Z',
      published_before: '2026-05-10T23:59:59Z',
    });
    await listArticleFilterOptions({
      author_id: 'author-1',
      source: 'tgb',
      trader_id: 'trader-1',
      published_after: '2026-05-01T00:00:00Z',
      published_before: '2026-05-10T23:59:59Z',
    });
    await runArticlePipeline({
      params: { profile_id: 'default' },
      created_by: 'web',
      confirmed: false,
    } as never);
    await runArticlePipelineStep('crawl', {
      params: { profile_id: 'default', force: false },
      created_by: 'web',
      confirmed: false,
    } as never);
    await startArticlePipelineSchedule({
      profile_id: 'default',
      schedule_time: '07:30',
      force: true,
    } as never);
    await stopArticlePipelineSchedule({
      profile_id: 'default',
    } as never);
    await listProfiles({ skip: 0, limit: 10 });
    await getProfile('default');
    await getProfileEdit('default');
    await validateProfileUpdate('default', { name: '默认配置', environment: 'production', sections: {} } as never);
    await updateProfile('default', {
      name: '默认配置',
      environment: 'production',
      sections: {},
      confirmed: true,
    } as never);
    await archiveProfile('default', { archived_by: 'web' });
    await importProfile({ profile_id: 'default', config_path: 'config/app.yaml', created_by: 'web' });
    await getProfileSnapshot('default', 'snapshot-1');
    await listArtifacts({ skip: 0, limit: 10 });
    await listArtifactFilterOptions();
    await getArtifact('artifact-1');
    await downloadArtifact('artifact-1');
    await listDailyReports();
    await getDailyReport('2026-05-10');
    await listEvaluationReports();
    await getEvaluationReport('2026-05-10');
    await downloadDailyReportHtml('2026-05-10');
    await downloadEvaluationHtml('2026-05-10');
    await listRecoveryBackups();
    await listRecoveryBackupTargets();
    await createRecoveryBackup({ profile_id: 'profile-1', include_processed: true } as never);
    await restoreRecoveryBackup({
      profile_id: 'profile-1',
      backup_id: '20260511-080000',
      include_processed: true,
      confirmed: true,
    } as never);
    await recoverStaleJobs({ stale_before_minutes: 12 } as never);
    await listDataAudits({ entity_type: 'backup', limit: 10 });
    await listSymbols('000001', 50);
    await getOhlcv('000001.SZ', '2026-05-01', '2026-05-10');
    await getOhlcvSchedulerStatus('default');
    await runOhlcvScheduler('default');
    await stopOhlcvScheduler('default');
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
    expect(findCall('/api/ui/v1/jobs/definitions')).toBeTruthy();
    expect(findCall('/api/ui/v1/jobs/definitions/pipeline-run')).toBeTruthy();
    expect(findCall('/api/ui/v1/jobs/job-1')).toBeTruthy();
    expect(findCall('/api/ui/v1/jobs/job-1/logs')).toBeTruthy();
    expectJsonBody('/api/ui/v1/jobs/job-1/cancel', 'POST', { reason: 'test' });
    expectJsonBody('/api/ui/v1/jobs/job-1/pause', 'POST', { reason: 'test' });
    expect(findCall('/api/ui/v1/jobs/job-1/resume', 'POST')).toBeTruthy();
    expectJsonBody('/api/ui/v1/jobs/job-1/retry', 'POST', { reason: 'test' });
    expectJsonBody('/api/ui/v1/jobs', 'POST', {
      job_type: 'run-pre-market',
      params: { date: '2026-05-10' },
    });
    expect(findCall('/api/ui/v1/workflows')).toBeTruthy();
    expect(findCall('/api/ui/v1/workflows/pipeline')).toBeTruthy();
    expectJsonBody('/api/ui/v1/workflows/pipeline/run', 'POST', { confirmed: true });
    expect(findCall('/api/ui/v1/ops/backup-targets')).toBeTruthy();
    expectJsonBody('/api/ui/v1/ops/backup', 'POST', { profile_id: 'profile-1', include_processed: true });
    expectJsonBody('/api/ui/v1/ops/restore', 'POST', {
      profile_id: 'profile-1',
      backup_id: '20260511-080000',
      include_processed: true,
      confirmed: true,
    });
    expect(findCall('/api/ui/v1/pipelines/article_pipeline')).toBeTruthy();
    expect(findCall('/api/ui/v1/pipelines/article_pipeline/schedule/status')).toBeTruthy();
    expect(calls.some((call) => call.url.startsWith('/api/ui/v1/market/ohlcv/status'))).toBe(true);
    expect(calls.some((call) => call.url.startsWith('/api/ui/v1/market/ohlcv/run') && call.method === 'POST')).toBe(true);
    expect(calls.some((call) => call.url.startsWith('/api/ui/v1/market/ohlcv/stop') && call.method === 'POST')).toBe(true);
    expect(findCall('/articles?page=2&page_size=20&author_id=author-1&source=tgb&trader_id=trader-1&published_after=2026-05-01T00%3A00%3A00Z&published_before=2026-05-10T23%3A59%3A59Z')).toBeTruthy();
    expect(findCall('/articles/filter-options?author_id=author-1&source=tgb&trader_id=trader-1&published_after=2026-05-01T00%3A00%3A00Z&published_before=2026-05-10T23%3A59%3A59Z')).toBeTruthy();
    expectJsonBody('/api/ui/v1/pipelines/article_pipeline/run', 'POST', {
      params: { profile_id: 'default' },
      created_by: 'web',
      confirmed: false,
    });
    expectJsonBody('/api/ui/v1/pipelines/article_pipeline/steps/crawl/run', 'POST', {
      params: { profile_id: 'default', force: false },
      created_by: 'web',
      confirmed: false,
    });
    expectJsonBody('/api/ui/v1/pipelines/article_pipeline/schedule/start', 'POST', {
      profile_id: 'default',
      schedule_time: '07:30',
      force: true,
    });
    expectJsonBody('/api/ui/v1/pipelines/article_pipeline/schedule/stop', 'POST', {
      profile_id: 'default',
    });
    expect(findCall('/api/ui/v1/artifacts?skip=0&limit=10')).toBeTruthy();
    expect(findCall('/api/ui/v1/artifacts/filter-options')).toBeTruthy();
    expect(findCall('/api/ui/v1/artifacts/artifact-1')).toBeTruthy();
    expect(findCall('/api/ui/v1/artifacts/artifact-1/download')).toBeTruthy();
    expect(findCall('/api/ui/v1/profiles?skip=0&limit=10')).toBeTruthy();
    expect(findCall('/api/ui/v1/profiles/default')).toBeTruthy();
    expect(findCall('/api/ui/v1/profiles/default/edit')).toBeTruthy();
    expectJsonBody('/api/ui/v1/profiles/default/validate', 'POST', {
      name: '默认配置',
      environment: 'production',
      sections: {},
    });
    expectJsonBody('/api/ui/v1/profiles/default', 'PUT', {
      name: '默认配置',
      environment: 'production',
      sections: {},
      confirmed: true,
    });
    expectJsonBody('/api/ui/v1/profiles/default/archive', 'POST', { archived_by: 'web' });
    expectJsonBody('/api/ui/v1/profiles/import', 'POST', {
      profile_id: 'default',
      config_path: 'config/app.yaml',
      created_by: 'web',
    });
    expect(findCall('/api/ui/v1/profiles/default/snapshots/snapshot-1')).toBeTruthy();
    expect(findCall('/reports/daily?skip=0&limit=50')).toBeTruthy();
    expect(findCall('/reports/daily/2026-05-10')).toBeTruthy();
    expect(findCall('/reports/evaluation?skip=0&limit=50')).toBeTruthy();
    expect(findCall('/reports/evaluation/2026-05-10')).toBeTruthy();
    expect(findCall('/reports/daily/2026-05-10/html')).toBeTruthy();
    expect(findCall('/reports/evaluation/2026-05-10/html')).toBeTruthy();
    expect(findCall('/api/ui/v1/ops/backups')).toBeTruthy();
    expect(findCall('/api/ui/v1/ops/backup-targets')).toBeTruthy();
    expectJsonBody('/api/ui/v1/ops/backup', 'POST', { profile_id: 'profile-1', include_processed: true });
    expectJsonBody('/api/ui/v1/ops/restore', 'POST', {
      profile_id: 'profile-1',
      backup_id: '20260511-080000',
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
