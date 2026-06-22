import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';

import { renderWithRouter } from '@/test/test-utils';
import { createJob, listJobs } from '@/lib/api/jobs';
import { getAfterCloseReview, getPreMarketReadiness, getTradingDayPlan, listAfterCloseProposals } from '@/lib/api/daily';
import { listBenchmarkOptions } from '@/lib/api/market';
import { listProfiles } from '@/lib/api/profiles';
import { TodayAfterClosePage, TodayOverviewPage, TodayPreMarketPage } from './index';

vi.mock('@/lib/api/jobs', () => ({
  listJobs: vi.fn(),
  createJob: vi.fn(),
}));
vi.mock('@/lib/api/daily', () => ({
  getPreMarketReadiness: vi.fn(),
  getTradingDayPlan: vi.fn(),
  getAfterCloseReview: vi.fn(),
  listAfterCloseProposals: vi.fn(),
}));
vi.mock('@/lib/api/market', () => ({
  listBenchmarkOptions: vi.fn(),
}));
vi.mock('@/lib/api/profiles', () => ({
  listProfiles: vi.fn(),
}));

const mockedListJobs = vi.mocked(listJobs);
const mockedCreateJob = vi.mocked(createJob);
const mockedGetPreMarketReadiness = vi.mocked(getPreMarketReadiness);
const mockedGetTradingDayPlan = vi.mocked(getTradingDayPlan);
const mockedGetAfterCloseReview = vi.mocked(getAfterCloseReview);
const mockedListAfterCloseProposals = vi.mocked(listAfterCloseProposals);
const mockedListBenchmarkOptions = vi.mocked(listBenchmarkOptions);
const mockedListProfiles = vi.mocked(listProfiles);

function buildProfile(profileId = 'profile-daily-1') {
  return {
    profile_id: profileId,
    name: '今日画像',
    environment: 'production',
    version: 7,
    sections: {},
    secret_refs: {},
    validation_status: 'validated',
    created_by: 'tester',
    created_at: '2026-06-13T00:00:00Z',
    updated_at: '2026-06-13T00:00:00Z',
    archived_at: null,
  };
}

function buildSnapshotJob() {
  return {
    id: 'snapshot-build-daily-1',
    job_type: 'snapshot-build',
    status: 'success',
    params: {
      profile_id: 'profile-daily-1',
      date: '2026-06-13',
      benchmark_symbol: '000300.SH',
    },
    result: null,
    error: null,
    artifacts: [],
    created_by: 'web',
    idempotency_key: null,
    retry_count: 0,
    max_retries: 0,
    retry_backoff_seconds: 0,
    timeout_seconds: null,
    cancel_requested: false,
    cancel_requested_at: null,
    worker_id: null,
    lock_token: null,
    lock_acquired_at: null,
    heartbeat_at: null,
    scheduled_at: null,
    started_at: '2026-06-13T01:00:00Z',
    finished_at: '2026-06-13T01:05:00Z',
    audit_events: [],
    created_at: '2026-06-13T01:00:00Z',
    updated_at: '2026-06-13T01:05:00Z',
  };
}

function buildRunPreMarketJob() {
  return {
    id: 'run-pre-market-daily-1',
    job_type: 'run-pre-market',
    status: 'success',
    params: {
      profile_id: 'profile-daily-1',
      as_of_date: '2026-06-13',
      benchmark_symbol: '000300.SH',
    },
    result: {
      as_of_date: '2026-06-13',
      summary: ['盘前信号已整理', '今日关注清单已生成'],
    },
    error: null,
    artifacts: [],
    created_by: 'web',
    idempotency_key: null,
    retry_count: 0,
    max_retries: 0,
    retry_backoff_seconds: 0,
    timeout_seconds: null,
    cancel_requested: false,
    cancel_requested_at: null,
    worker_id: null,
    lock_token: null,
    lock_acquired_at: null,
    heartbeat_at: null,
    scheduled_at: null,
    started_at: '2026-06-13T02:00:00Z',
    finished_at: '2026-06-13T02:15:00Z',
    audit_events: [],
    created_at: '2026-06-13T02:00:00Z',
    updated_at: '2026-06-13T02:15:00Z',
  };
}

function buildAfterCloseJob() {
  return {
    id: 'run-after-close-daily-1',
    job_type: 'run-after-close',
    status: 'success',
    params: {
      profile_id: 'profile-daily-1',
      as_of_date: '2026-06-13',
      force: false,
      export_html: true,
    },
    result: {
      as_of_date: '2026-06-13',
      evaluations_count: 1,
      result: {
        result_id: 'after-close-1',
        as_of_date: '2026-06-13',
        evaluations: [
          {
            idea_id: 'idea-1',
            symbol: '000001.SZ',
            entry_price: 10,
            current_price: 10.5,
            return_pct: 0.05,
            status: 'ok',
            partial_data: false,
            fallback_reason: null,
            notes: ['收盘后复盘已完成'],
          },
        ],
        summary: ['1 条复盘记录'],
        evidence_pack_refs: ['pack-daily-1'],
        failure_categories: [],
        postmortem_notes: ['收盘后复盘已完成'],
        ranking_features: { return_pct: 0.05 },
      },
      html_path: 'after-close-daily-1.html',
    },
    error: null,
    artifacts: [],
    created_by: 'web',
    idempotency_key: null,
    retry_count: 0,
    max_retries: 0,
    retry_backoff_seconds: 0,
    timeout_seconds: null,
    cancel_requested: false,
    cancel_requested_at: null,
    worker_id: null,
    lock_token: null,
    lock_acquired_at: null,
    heartbeat_at: null,
    scheduled_at: null,
    started_at: '2026-06-13T18:00:00Z',
    finished_at: '2026-06-13T18:20:00Z',
    audit_events: [],
    created_at: '2026-06-13T18:00:00Z',
    updated_at: '2026-06-13T18:20:00Z',
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  mockedListProfiles.mockResolvedValue({
    count: 1,
    total: 1,
    skip: 0,
    limit: 50,
    items: [buildProfile()],
  } as never);
  mockedListBenchmarkOptions.mockResolvedValue({
    count: 1,
    items: [{ symbol: '000300.SH', code: '000300', market: 'SH', name: '沪深300', security_type: 'index' }],
  } as never);
  mockedListJobs.mockResolvedValue({
    count: 1,
    total: 1,
    skip: 0,
    limit: 20,
    items: [],
  } as never);
  mockedGetPreMarketReadiness.mockResolvedValue({
    state: 'ready',
    readiness_status: 'ready',
    trade_date: '2026-06-13',
    slot: '09-25',
    summary_title: '可以继续',
    happened: '正式盘前依赖齐备。',
    affected: '可以继续正式盘前流程。',
    repair_guidance: '无需修复。',
    can_proceed: true,
    can_proceed_in_degraded_mode: false,
    checks: [],
    traceability: {
      trade_date: '2026-06-13',
      strategy_version_id: 'strategy-version-1',
      dataset_snapshot_id: 'dataset-snapshot-1',
      market_snapshot_id: 'market-snapshot-1',
      market_state_id: 'market-state-1',
      rule_applicability_profile_ids: ['applicability-1'],
      author_validated_profile_version_id: 'author-profile-1',
      data_quality_state: 'ready',
    },
    repair_actions: [],
    warnings: [],
  } as never);
  mockedGetTradingDayPlan.mockResolvedValue({
    state: 'ready',
    plan_status: 'ready',
    generated: true,
    trade_date: '2026-06-21',
    happened: '已生成每日运行计划。',
    affected: '可以继续查看今天的正式盘后结果。',
    repair_guidance: '无需修复。',
    trading_day_plan_id: 'plan-1',
    daily_strategy_instance_id: 'instance-1',
    daily_rule_selection_id: 'selection-1',
    revision_no: 1,
    strategy_version_id: 'strategy-version-1',
    instance_lifecycle_state: 'generated',
    plan_lifecycle_state: 'approved',
    approval_state: 'approved',
    market_judgment: { state: 'ready', summary: '强势上行', details: [] },
    enabled_rules: [],
    reduced_rules: [],
    suspended_rules: [],
    candidate_symbols: [],
    candidate_symbols_state: { state: 'ready', summary: '已完成', details: [] },
    signals: [],
    entry_conditions: { state: 'ready', summary: '已完成', details: [] },
    invalidation_conditions: { state: 'ready', summary: '已完成', details: [] },
    stop_loss_take_profit: { state: 'ready', summary: '已完成', details: [] },
    suggested_position: { state: 'ready', summary: '已完成', details: [] },
    risk_warnings: { state: 'ready', summary: '已完成', details: [] },
    confidence: { state: 'ready', summary: '已完成', details: [] },
  } as never);
  mockedGetAfterCloseReview.mockResolvedValue({
    state: 'unavailable',
    generated: false,
    trading_day_plan_id: 'plan-1',
    trade_date: '2026-06-21',
    signal_outcome_state: 'unavailable',
    attribution_state: 'unavailable',
    signal_results: [],
    attribution: { state: 'unavailable', signals: [] },
    evidence: {},
    happened: '正式盘后复盘尚未生成。',
    affected: '当前只能查看盘前预测，实际结果、差异和建议操作暂不可用。',
    repair_guidance: '请先完成正式盘后结果评估；如果今天已经完成，请刷新页面后重试。',
  } as never);
  mockedListAfterCloseProposals.mockResolvedValue({
    state: 'empty',
    count: 0,
    items: [],
    happened: '暂无建议。',
    affected: '当前不会显示建议动作。',
    repair_guidance: '稍后再试。',
  } as never);
});

describe('daily strategy pages', () => {
  it('does not present missing jobs or benchmark options as pending or available', async () => {
    mockedListBenchmarkOptions.mockResolvedValueOnce({
      count: 0,
      items: [],
    } as never);

    renderWithRouter([{ path: '/daily', element: <TodayOverviewPage /> }], ['/daily']);

    expect(await screen.findByRole('heading', { name: '今日总览' })).toBeInTheDocument();
    expect((await screen.findAllByText('当前不可用')).length).toBeGreaterThan(0);
    expect(screen.getByText('暂无可用基准')).toBeInTheDocument();
    expect(screen.queryByText('待处理')).not.toBeInTheDocument();
  });

  it('renders the daily overview in product mode with truthful partial state and no technical terms', async () => {
    mockedListBenchmarkOptions.mockRejectedValueOnce(new Error('benchmarks unavailable'));
    mockedListJobs.mockResolvedValueOnce({
      count: 1,
      total: 1,
      skip: 0,
      limit: 20,
      items: [buildSnapshotJob()],
    } as never);
    mockedListJobs.mockResolvedValueOnce({
      count: 1,
      total: 1,
      skip: 0,
      limit: 20,
      items: [buildAfterCloseJob()],
    } as never);

    renderWithRouter(
      [
        { path: '/daily', element: <TodayOverviewPage /> },
        { path: '/daily/pre-market', element: <TodayPreMarketPage /> },
        { path: '/daily/after-close', element: <TodayAfterClosePage /> },
      ],
      ['/daily'],
    );

    expect(await screen.findByRole('heading', { name: '今日总览' })).toBeInTheDocument();
    expect((await screen.findAllByText('部分完成')).length).toBeGreaterThan(0);
    expect(screen.getByText('今日盘前')).toBeInTheDocument();
    expect(screen.getByText('今日盘后')).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: '查看今日盘前' })[0]).toHaveAttribute('href', '/daily/pre-market');
    expect(screen.getAllByRole('link', { name: '查看今日盘后' })[0]).toHaveAttribute('href', '/daily/after-close');
    expect(screen.queryByText('Job')).not.toBeInTheDocument();
    expect(screen.queryByText('Workflow')).not.toBeInTheDocument();
    expect(screen.queryByText('Pipeline')).not.toBeInTheDocument();
    expect(screen.queryByText('Artifact')).not.toBeInTheDocument();
    expect(screen.queryByText('Provider')).not.toBeInTheDocument();
    expect(screen.queryByText('force=true')).not.toBeInTheDocument();
    expect(screen.queryByText('config_path')).not.toBeInTheDocument();
    expect(screen.queryByText('/jobs')).not.toBeInTheDocument();
    expect(screen.queryByText('/workflows')).not.toBeInTheDocument();
    expect(screen.queryByText('/artifacts')).not.toBeInTheDocument();
    expect(screen.queryByText('/market/')).not.toBeInTheDocument();
  });

  it('renders the formal daily pre-market readiness result without legacy execution actions', async () => {
    renderWithRouter([{ path: '/daily/pre-market', element: <TodayPreMarketPage /> }], ['/daily/pre-market']);

    expect(await screen.findByRole('heading', { name: '今日盘前' })).toBeInTheDocument();
    expect(screen.getByText('页面用途')).toBeInTheDocument();
    expect(await screen.findAllByText('可以继续')).not.toHaveLength(0);
    expect(await screen.findAllByText('正式盘前依赖齐备。')).not.toHaveLength(0);
    expect(await screen.findAllByText('可以继续正式盘前流程。')).not.toHaveLength(0);
    expect(screen.getByText('09-25')).toBeInTheDocument();
    expect(mockedGetPreMarketReadiness).toHaveBeenCalledWith('2026-06-22');
    expect(screen.queryByText('Job ID')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '整理今日盘前数据' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '开始盘前分析' })).not.toBeInTheDocument();
    expect(screen.queryByText('run-pre-market')).not.toBeInTheDocument();
    expect(screen.queryByText('snapshot-build')).not.toBeInTheDocument();
    expect(screen.queryByText('force')).not.toBeInTheDocument();
    expect(screen.queryByText('config_path')).not.toBeInTheDocument();
    expect(screen.queryByText('/jobs')).not.toBeInTheDocument();
    expect(screen.queryByText('/workflows')).not.toBeInTheDocument();
    expect(screen.queryByText('/artifacts')).not.toBeInTheDocument();
    expect(mockedCreateJob).not.toHaveBeenCalled();
  });
});
