import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider, createMemoryRouter } from 'react-router-dom';
import { AuthProvider } from '@/features/auth/auth-context';
import { DashboardLayout } from '@/layouts/dashboard-layout';
import { OverviewPage } from '@/pages/overview';
import { JobsPage } from '@/pages/jobs';
import { JobDetailPage } from '@/pages/jobs/JobDetailPage';
import { WorkflowsPage } from '@/pages/workflows';
import { ArtifactsPage } from '@/pages/artifacts';
import { ReportsPage } from '@/pages/reports';
import { SettingsPage } from '@/pages/settings';
import { OpsPage } from '@/pages/ops';
import type { CurrentPrincipal } from '@/types/auth';
import {
  getSystemStatus,
} from '@/lib/api/system';
import { createJob, getJob, getJobLogs, listJobs, cancelJob } from '@/lib/api/jobs';
import { listWorkflows, runWorkflow } from '@/lib/api/workflows';
import { downloadArtifact, getArtifact, listArtifacts } from '@/lib/api/artifacts';
import {
  downloadDailyReportHtml,
  downloadEvaluationHtml,
  getDailyReport,
  getEvaluationReport,
  listDailyReports,
  listEvaluationReports,
} from '@/lib/api/reports';
import {
  getSettingsConfig,
  getSettingsSchema,
  listSettingsBackups,
  restoreSettingsBackup,
  saveSettings,
  validateSettingsDraft,
} from '@/lib/api/settings';

vi.mock('@/lib/api/system', () => ({
  getSystemStatus: vi.fn(),
}));

vi.mock('@/lib/api/jobs', () => ({
  cancelJob: vi.fn(),
  createJob: vi.fn(),
  getJob: vi.fn(),
  getJobLogs: vi.fn(),
  listJobs: vi.fn(),
}));

vi.mock('@/lib/api/workflows', () => ({
  listWorkflows: vi.fn(),
  runWorkflow: vi.fn(),
}));

vi.mock('@/lib/api/artifacts', () => ({
  downloadArtifact: vi.fn(),
  getArtifact: vi.fn(),
  listArtifacts: vi.fn(),
}));

vi.mock('@/lib/api/reports', () => ({
  downloadDailyReportHtml: vi.fn(),
  downloadEvaluationHtml: vi.fn(),
  getDailyReport: vi.fn(),
  getEvaluationReport: vi.fn(),
  listDailyReports: vi.fn(),
  listEvaluationReports: vi.fn(),
}));

vi.mock('@/lib/api/settings', () => ({
  getSettingsConfig: vi.fn(),
  getSettingsSchema: vi.fn(),
  listSettingsBackups: vi.fn(),
  restoreSettingsBackup: vi.fn(),
  saveSettings: vi.fn(),
  validateSettingsDraft: vi.fn(),
}));

const mockedGetSystemStatus = vi.mocked(getSystemStatus);
const mockedListJobs = vi.mocked(listJobs);
const mockedGetJob = vi.mocked(getJob);
const mockedGetJobLogs = vi.mocked(getJobLogs);
const mockedCreateJob = vi.mocked(createJob);
const mockedCancelJob = vi.mocked(cancelJob);
const mockedListWorkflows = vi.mocked(listWorkflows);
const mockedRunWorkflow = vi.mocked(runWorkflow);
const mockedListArtifacts = vi.mocked(listArtifacts);
const mockedGetArtifact = vi.mocked(getArtifact);
const mockedDownloadArtifact = vi.mocked(downloadArtifact);
const mockedListDailyReports = vi.mocked(listDailyReports);
const mockedListEvaluationReports = vi.mocked(listEvaluationReports);
const mockedGetDailyReport = vi.mocked(getDailyReport);
const mockedGetEvaluationReport = vi.mocked(getEvaluationReport);
const mockedDownloadDailyReportHtml = vi.mocked(downloadDailyReportHtml);
const mockedDownloadEvaluationHtml = vi.mocked(downloadEvaluationHtml);
const mockedGetSettingsConfig = vi.mocked(getSettingsConfig);
const mockedGetSettingsSchema = vi.mocked(getSettingsSchema);
const mockedListSettingsBackups = vi.mocked(listSettingsBackups);
const mockedValidateSettingsDraft = vi.mocked(validateSettingsDraft);
const mockedSaveSettings = vi.mocked(saveSettings);
const mockedRestoreSettingsBackup = vi.mocked(restoreSettingsBackup);

const adminPrincipal: CurrentPrincipal = {
  role: 'admin',
  api_key_label: 'Local Admin',
  authenticated: true,
  source: 'api_key',
};

const viewerPrincipal: CurrentPrincipal = {
  role: 'viewer',
  api_key_label: 'Local Viewer',
  authenticated: true,
  source: 'api_key',
};

const systemStatus = {
  status: 'ok' as const,
  config_path: 'config/app.yaml',
  project_root: '/Users/wanghui/Documents/Claude/trade-strategy-ai',
  run_mode: 'web',
  database: { name: 'primary', status: 'ok' as const, latency_ms: 12, details: {} },
  directories: {
    config: { path: 'config', exists: true },
    data: { path: 'data', exists: true },
    logs: { path: 'logs', exists: true },
  },
  warnings: [] as string[],
};

const job1 = {
  id: 'job-1',
  job_type: 'run-pre-market',
  status: 'success',
  params: { date: '2026-05-10', config_path: 'config/app.yaml' },
  result: null,
  error: null,
  artifacts: [
    {
      kind: 'report',
      path: 'data/jobs/job-1/result.json',
      metadata: { source: 'web' },
    },
  ],
  created_by: 'web',
  idempotency_key: null,
  retry_count: 0,
  max_retries: 3,
  retry_backoff_seconds: 0,
  timeout_seconds: null,
  cancel_requested: false,
  cancel_requested_at: null,
  worker_id: null,
  lock_token: null,
  lock_acquired_at: null,
  heartbeat_at: null,
  scheduled_at: null,
  started_at: '2026-05-10T08:00:00Z',
  finished_at: '2026-05-10T08:05:00Z',
  audit_events: [
    {
      id: 'audit-job-1',
      job_id: 'job-1',
      operation: 'create',
      actor: 'web',
      source: 'ui',
      params_summary: { date: '2026-05-10' },
      payload: { request_context: { channel: 'ui' } },
      event_at: '2026-05-10T08:00:00Z',
      created_at: '2026-05-10T08:00:00Z',
      updated_at: '2026-05-10T08:05:00Z',
    },
  ],
  created_at: '2026-05-10T08:00:00Z',
  updated_at: '2026-05-10T08:05:00Z',
};

const job2 = {
  ...job1,
  id: 'job-2',
  status: 'running',
  started_at: '2026-05-10T09:00:00Z',
  finished_at: null,
  created_at: '2026-05-10T09:00:00Z',
  updated_at: '2026-05-10T09:02:00Z',
  audit_events: [
    {
      id: 'audit-job-2',
      job_id: 'job-2',
      operation: 'create',
      actor: 'web',
      source: 'ui',
      params_summary: { date: '2026-05-10' },
      payload: { request_context: { channel: 'ui' } },
      event_at: '2026-05-10T09:00:00Z',
      created_at: '2026-05-10T09:00:00Z',
      updated_at: '2026-05-10T09:02:00Z',
    },
  ],
};

const rerunJob = {
  ...job1,
  id: 'job-3',
  status: 'pending',
  started_at: '2026-05-10T09:30:00Z',
  finished_at: null,
  created_at: '2026-05-10T09:30:00Z',
  updated_at: '2026-05-10T09:30:00Z',
  audit_events: [],
};

const workflow = {
  workflow_id: 'install-config',
  title: '安装与配置',
  description: '完成项目初始化、数据库迁移和基础数据导入。',
  job_type: 'init-project',
  permissions: 'operator',
  job_definition: {
    job_type: 'init-project',
    title: '初始化项目',
    description: '执行初始化并完成最小可运行状态。',
    summary: '初始化项目',
    permission: 'operator',
    risk: 'high',
    can_retry: false,
    can_run_concurrently: false,
    concurrency_group: 'project-init',
    requires_confirmation: true,
    runnable: true,
    params_schema: {
      description: '初始化项目参数',
      allow_additional_fields: false,
      fields: {
        config_path: {
          type: 'path',
          description: '配置文件路径',
          required: true,
          enum: [],
        },
      },
    },
  },
  steps: [
    {
      step_id: 'init-project',
      title: '初始化项目',
      description: '执行初始化并完成最小可运行状态。',
      required_job_type: 'init-project',
      parameters: ['config_path'],
      param_schema: {
        description: '初始化项目参数',
        allow_additional_fields: false,
        fields: {
          config_path: {
            type: 'path',
            description: '配置文件路径',
            required: true,
            enum: [],
          },
        },
      },
      risk: 'high',
      requires_confirmation: true,
    },
  ],
};

const artifacts = [
  {
    artifact_id: 'artifact-1',
    name: 'daily_report.html',
    title: 'daily_report.html',
    path: 'data/artifacts/daily_report.html',
    kind: 'html',
    source: 'job',
    exists: true,
    size_bytes: 2048,
    modified_at: '2026-05-10T08:10:00Z',
    previewable: true,
    job_id: 'job-1',
    job_type: 'run-after-close',
    storage_ref: {
      source: 'file',
      logical_id: 'data/artifacts/daily_report.html',
      relative_path: 'data/artifacts/daily_report.html',
      uri: null,
      metadata: { source: 'job', format: 'html' },
    },
    metadata: { source: 'job', format: 'html' },
    preview: '<html><body><h1>Daily report preview</h1></body></html>',
    download_name: 'daily_report.html',
  },
  {
    artifact_id: 'artifact-2',
    name: 'result.json',
    title: 'result.json',
    path: 'data/artifacts/result.json',
    kind: 'json',
    source: 'job',
    exists: true,
    size_bytes: 512,
    modified_at: '2026-05-10T08:12:00Z',
    previewable: false,
    job_id: 'job-1',
    job_type: 'run-after-close',
    storage_ref: {
      source: 'file',
      logical_id: 'data/artifacts/result.json',
      relative_path: 'data/artifacts/result.json',
      uri: null,
      metadata: { source: 'job', format: 'json' },
    },
    metadata: { source: 'job', format: 'json' },
    preview: '{"status":"ok"}',
    download_name: 'result.json',
  },
] as const;

const dailyReportList = [
  { as_of_date: '2026-05-10', file_path: '/tmp/daily_report_2026-05-10.json', file_size: 640 },
];

const evaluationReportList = [
  { as_of_date: '2026-05-10', file_path: '/tmp/evaluation_2026-05-10.json', file_size: 768 },
];

const dailyReportDetail = {
  status: 'success',
  report: {
    report_id: '11111111-1111-1111-1111-111111111111',
    as_of_date: '2026-05-10',
    generated_at: '2026-05-10T08:00:00Z',
    ideas: [],
    highlights: ['盘前策略已更新'],
    risks: ['成交量偏弱'],
    strategy_version_ids: ['sv-001'],
    market_universe_snapshot: { symbols: ['AAA'] },
  },
};

const evaluationReportDetail = {
  status: 'success',
  result: {
    result_id: '22222222-2222-2222-2222-222222222222',
    as_of_date: '2026-05-10',
    generated_at: '2026-05-10T15:00:00Z',
    evaluations: [],
    evidence_pack_refs: ['pack-1'],
    failure_categories: ['slippage'],
    ranking_features: { pnl: -1.2 },
    postmortem_notes: ['盘后考核确认回撤扩大'],
    summary: ['盘后考核完成'],
  },
};

const settingsSections = [
  { key: 'timezone', title: 'Timezone', summary: '时区', type: 'value', editable: true },
  { key: 'database', title: 'Database', summary: '数据库', type: 'object', editable: true },
  { key: 'api', title: 'API', summary: 'API 服务', type: 'object', editable: true },
];

const settingsConfig = {
  timezone: 'Asia/Shanghai',
  database: { url: 'postgresql://trade:***@localhost:5432/trade_strategy_ai', echo: false },
  api: { timeout_seconds: 300 },
};

const settingsBackups = [
  {
    path: '/tmp/backups/app.20260510-080000.yaml',
    name: 'app.20260510-080000.yaml',
    size_bytes: 2048,
    modified_at: '2026-05-10T08:00:00Z',
  },
];

beforeAll(() => {
  if (!window.URL.createObjectURL) {
    Object.defineProperty(window.URL, 'createObjectURL', {
      configurable: true,
      value: vi.fn(() => 'blob:artifact'),
    });
  }
  if (!window.URL.revokeObjectURL) {
    Object.defineProperty(window.URL, 'revokeObjectURL', {
      configurable: true,
      value: vi.fn(),
    });
  }
});

beforeEach(() => {
  vi.clearAllMocks();

  mockedGetSystemStatus.mockResolvedValue(systemStatus);
  mockedListJobs.mockResolvedValue({ count: 2, total: 2, skip: 0, limit: 50, items: [job1, job2] });
  mockedGetJob.mockImplementation(async (jobId: string) => {
    const selected = jobId === 'job-2' ? job2 : jobId === 'job-3' ? rerunJob : jobId === 'job-4' ? { ...rerunJob, id: 'job-4' } : job1;
    return {
      job: selected,
      job_dir: `/tmp/${jobId}`,
      log_path: `/tmp/${jobId}/job.log`,
      params_path: `/tmp/${jobId}/params.json`,
      result_path: `/tmp/${jobId}/result.json`,
      artifacts_path: `/tmp/${jobId}/artifacts.json`,
    };
  });
  mockedGetJobLogs.mockImplementation(async (jobId: string) => ({
    job_id: jobId,
    log_path: `/tmp/${jobId}/job.log`,
    count: 1,
    items: [jobId === 'job-3' ? 'job queued from web' : 'job started'],
  }));
  mockedCreateJob.mockResolvedValue({
    created: true,
    job: rerunJob,
    job_dir: '/tmp/job-3',
    log_path: '/tmp/job-3/job.log',
    params_path: '/tmp/job-3/params.json',
    result_path: '/tmp/job-3/result.json',
    artifacts_path: '/tmp/job-3/artifacts.json',
  });
  mockedCancelJob.mockResolvedValue({
    job: job1,
    job_dir: '/tmp/job-1',
    log_path: '/tmp/job-1/job.log',
    params_path: '/tmp/job-1/params.json',
    result_path: '/tmp/job-1/result.json',
    artifacts_path: '/tmp/job-1/artifacts.json',
  });

  mockedListWorkflows.mockResolvedValue({ count: 1, items: [workflow] });
  mockedRunWorkflow.mockResolvedValue({
    workflow,
    job: {
      id: 'job-4',
      job_type: 'init-project',
    },
  } as never);

  mockedListArtifacts.mockResolvedValue({
    count: 2,
    total: 2,
    skip: 0,
    limit: 50,
    items: [...artifacts],
  });
  mockedGetArtifact.mockImplementation(async (artifactId: string) =>
    artifactId === 'artifact-2'
      ? { ...artifacts[1], preview: artifacts[1].preview }
      : { ...artifacts[0], preview: artifacts[0].preview },
  );
  mockedDownloadArtifact.mockResolvedValue(new Blob(['artifact-1-binary']));

  mockedListDailyReports.mockResolvedValue({
    status: 'success',
    count: 1,
    total: 1,
    skip: 0,
    limit: 50,
    reports: dailyReportList,
  });
  mockedListEvaluationReports.mockResolvedValue({
    status: 'success',
    count: 1,
    total: 1,
    skip: 0,
    limit: 50,
    reports: evaluationReportList,
  });
  mockedGetDailyReport.mockResolvedValue(dailyReportDetail as never);
  mockedGetEvaluationReport.mockResolvedValue(evaluationReportDetail as never);
  mockedDownloadDailyReportHtml.mockResolvedValue('<html><body><h1>日报 HTML</h1></body></html>');
  mockedDownloadEvaluationHtml.mockResolvedValue('<html><body><h1>考核 HTML</h1></body></html>');

  mockedGetSettingsConfig.mockResolvedValue({
    config_path: 'config/app.yaml',
    config: settingsConfig,
    sections: settingsSections,
  });
  mockedGetSettingsSchema.mockResolvedValue({
    config_path: 'config/app.yaml',
    sections: settingsSections,
  });
  mockedListSettingsBackups.mockResolvedValue({
    config_path: 'config/app.yaml',
    count: 1,
    items: settingsBackups,
  });
  mockedValidateSettingsDraft.mockResolvedValue({
    config_path: 'config/app.yaml',
    diff: { timezone: { before: 'Asia/Shanghai', after: 'Asia/Tokyo' } },
    masked_config: settingsConfig,
  });
  mockedSaveSettings.mockResolvedValue({
    config_path: 'config/app.yaml',
    backup_path: '/tmp/backups/app.20260510-080001.yaml',
    config: { ...settingsConfig, timezone: 'Asia/Tokyo' },
    reload_required: true,
    reload_targets: ['web'],
    reload_message: '配置已重新加载',
  });
  mockedRestoreSettingsBackup.mockResolvedValue({
    config_path: 'config/app.yaml',
    backup_path: '/tmp/backups/app.20260510-080000.yaml',
    config: settingsConfig,
    reload_required: true,
    reload_targets: ['web'],
    reload_message: '配置已重新加载',
  });
});

function renderWebApp(initialPrincipal: CurrentPrincipal) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  const router = createMemoryRouter(
    [
      {
        element: <DashboardLayout />,
        children: [
          { index: true, element: <OverviewPage /> },
          { path: 'jobs', element: <JobsPage /> },
          { path: 'jobs/:jobId', element: <JobDetailPage /> },
          { path: 'workflows', element: <WorkflowsPage /> },
          { path: 'workflows/:workflowId', element: <WorkflowsPage /> },
          { path: 'workflows/:workflowId/run', element: <WorkflowsPage /> },
          { path: 'artifacts', element: <ArtifactsPage /> },
          { path: 'reports', element: <ReportsPage /> },
          { path: 'settings', element: <SettingsPage /> },
          { path: 'ops', element: <OpsPage /> },
        ],
      },
    ],
    { initialEntries: ['/'] },
  );

  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider initialPrincipal={initialPrincipal}>
        <RouterProvider router={router} future={{ v7_startTransition: true }} />
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe('WEB-S8-006 acceptance', () => {
  it('covers the admin main chain across overview, jobs, workflows, artifacts, reports and settings', async () => {
    const user = userEvent.setup();
    renderWebApp(adminPrincipal);

    expect(await screen.findByRole('heading', { name: '运维概览' })).toBeInTheDocument();
    expect(screen.getByText('系统状态')).toBeInTheDocument();
    expect(screen.getByText('最近任务')).toBeInTheDocument();
    expect(screen.getByText('最近产物')).toBeInTheDocument();

    await user.click(screen.getAllByRole('link', { name: /^任务/ })[0]);
    expect(await screen.findByRole('heading', { name: '任务列表' })).toBeInTheDocument();
    await user.click(screen.getAllByRole('button', { name: '查看详情' })[0]);
    expect(await screen.findByRole('heading', { name: '任务详情' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '重新运行任务' }));
    expect(await screen.findByText('job-3')).toBeInTheDocument();

    await user.click(screen.getAllByRole('link', { name: /^工作流/ })[0]);
    expect(await screen.findByRole('heading', { name: '引导式操作' })).toBeInTheDocument();
    await user.click(screen.getAllByRole('button', { name: '运行入口' })[0]);
    await user.click(screen.getByRole('button', { name: '继续并确认' }));
    expect(await screen.findByRole('heading', { name: '确认高风险操作' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '确认提交' }));
    expect(await screen.findByRole('heading', { name: '任务详情' })).toBeInTheDocument();
    expect(await screen.findByText('job-4')).toBeInTheDocument();

    await user.click(screen.getAllByRole('link', { name: /^产物/ })[0]);
    expect(await screen.findByRole('heading', { name: '产物中心' })).toBeInTheDocument();
    await user.click(screen.getByText('daily_report.html'));
    expect(await screen.findByRole('heading', { name: '产物详情' })).toBeInTheDocument();
    expect(screen.getByTitle('HTML 预览')).toHaveAttribute('srcdoc', '<html><body><h1>Daily report preview</h1></body></html>');
    await user.click(screen.getByRole('button', { name: '下载' }));
    expect(mockedDownloadArtifact).toHaveBeenCalledWith('artifact-1');

    await user.click(screen.getAllByRole('link', { name: /^报告/ })[0]);
    expect(await screen.findByRole('heading', { name: '报告中心' })).toBeInTheDocument();
    expect(screen.getAllByText('盘前日报')[0]).toBeInTheDocument();
    expect(screen.getByTitle('HTML 预览')).toHaveAttribute('srcdoc', '<html><body><h1>日报 HTML</h1></body></html>');
    await user.click(screen.getAllByRole('button', { name: /盘后考核/ })[0]);
    expect(await screen.findByText('盘后考核完成')).toBeInTheDocument();
    await user.click(screen.getAllByRole('button', { name: 'JSON 详情' })[0]);
    expect(screen.getByTestId('evaluation-result-id')).toHaveTextContent('22222222-2222-2222-2222-222222222222');

    await user.click(screen.getAllByRole('link', { name: /^设置/ })[0]);
    expect(await screen.findByRole('heading', { name: '配置中心' })).toBeInTheDocument();
    const timezoneInput = screen.getByLabelText('Timezone');
    await user.clear(timezoneInput);
    await user.type(timezoneInput, 'Asia/Tokyo');
    await user.click(screen.getByRole('button', { name: '预览差异' }));
    expect(await screen.findByRole('heading', { name: 'Validation diff' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '保存配置' }));
    expect(await screen.findByRole('heading', { name: 'Confirm save' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Confirm save' }));
    expect(await screen.findByText(/已保存，备份路径/)).toBeInTheDocument();
    expect(mockedSaveSettings).toHaveBeenCalledWith({
      config_path: 'config/app.yaml',
      draft: { timezone: 'Asia/Tokyo' },
      confirmed: true,
    });
  });

  it('covers the auth and permission chain for viewer principals', async () => {
    const user = userEvent.setup();
    renderWebApp(viewerPrincipal);

    expect(await screen.findByRole('heading', { name: '运维概览' })).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: /^运维/ })[0]).toHaveAttribute('aria-disabled', 'true');

    await user.click(screen.getAllByRole('link', { name: /^任务/ })[0]);
    expect(await screen.findByRole('heading', { name: '任务列表' })).toBeInTheDocument();
    await user.click(screen.getAllByRole('button', { name: '查看详情' })[0]);
    expect(await screen.findByRole('heading', { name: '任务详情' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '重新运行任务' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '取消任务' })).toBeDisabled();

    await user.click(screen.getAllByRole('link', { name: /^工作流/ })[0]);
    expect(await screen.findByRole('heading', { name: '引导式操作' })).toBeInTheDocument();
    await user.click(screen.getAllByRole('button', { name: '运行入口' })[0]);
    expect(screen.getByRole('button', { name: '继续并确认' })).toBeDisabled();
    expect(screen.getByText('当前身份仅可查看参数，提交运行需要 operator 权限。')).toBeInTheDocument();

    await user.click(screen.getAllByRole('link', { name: /^设置/ })[0]);
    expect(await screen.findByRole('heading', { name: '配置中心' })).toBeInTheDocument();
    expect(screen.getByText('当前身份为 viewer，仅可查看和预览配置。')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '保存配置' })).toBeDisabled();
  });
});
