import { cleanup, render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '@/features/auth/auth-context';

vi.mock('@/pages/articles', () => ({
  ArticleLibraryPage: () => <div data-testid="article-list">真实文章列表</div>,
  ArticleAddPage: () => <div data-testid="article-add">真实文章导入</div>,
  ArticleExtractionResultsPage: () => <div data-testid="article-results">真实提取结果</div>,
  ArticleListPage: () => <div data-testid="article-list">真实文章列表</div>,
  ArticleRunPage: () => <div data-testid="article-add">真实文章导入</div>,
  ArticleResultsPage: () => <div data-testid="article-results">真实提取结果</div>,
}));

vi.mock('@/pages/rule-pool', () => ({
  RulePoolPage: ({ productMode }: { productMode?: boolean }) =>
    productMode ? <div data-testid="rule-pool-product">真实规则列表</div> : <div data-testid="rule-pool">兼容规则列表</div>,
}));

vi.mock('@/pages/backtest', () => ({
  BacktestPage: ({ productMode }: { productMode?: boolean }) =>
    productMode ? <div data-testid="backtest-product">真实回测能力</div> : <div data-testid="backtest">兼容回测能力</div>,
}));

vi.mock('@/pages/backtest/RegimeBacktestReportPage', () => ({
  RegimeBacktestReportPage: ({ productMode }: { productMode?: boolean }) =>
    productMode ? <div data-testid="regime-backtest-product">真实分市场状态结果</div> : <div data-testid="regime-backtest">兼容分市场状态结果</div>,
}));

vi.mock('@/pages/backtest/CandidatesPage', () => ({
  CandidatesPage: ({ productMode }: { productMode?: boolean }) =>
    productMode ? <div data-testid="strategy-candidates-product">真实候选版本</div> : <div data-testid="strategy-candidates">兼容候选版本</div>,
}));

vi.mock('@/pages/persona', () => ({
  PersonaPage: ({ productMode }: { productMode?: boolean }) =>
    productMode ? <div data-testid="persona-product">现有画像能力</div> : <div data-testid="persona">兼容画像能力</div>,
}));

vi.mock('@/features/system-status/system-status-panel', () => ({
  SystemStatusPanel: ({ productMode }: { productMode?: boolean }) =>
    productMode ? <div data-testid="system-status-product">真实系统状态</div> : <div data-testid="system-status">兼容系统状态</div>,
}));

vi.mock('@/lib/api/profiles', () => ({
  listProfiles: vi.fn().mockResolvedValue({
    count: 1,
    total: 1,
    skip: 0,
    limit: 50,
    items: [{
      profile_id: 'profile-1',
      name: '正式配置',
      environment: 'production',
      version: 1,
      sections: {},
      secret_refs: {},
      validation_status: 'validated',
      created_by: 'test',
      created_at: '2026-06-13T00:00:00Z',
      updated_at: '2026-06-13T00:00:00Z',
      archived_at: null,
    }],
  }),
}));

vi.mock('@/lib/api/authors', () => ({
  listAuthorProfiles: vi.fn().mockResolvedValue({
    state: 'empty',
    items: [],
    count: 0,
  }),
}));

vi.mock('@/lib/api/strategies', () => ({
  listStrategies: vi.fn().mockResolvedValue({
    state: 'empty',
    current_strategy: null,
    items: [],
    count: 0,
  }),
  listStrategyRevisionProposals: vi.fn().mockResolvedValue({
    state: 'empty',
    items: [],
    count: 0,
  }),
  getStrategyRevisionProposal: vi.fn().mockResolvedValue({
    proposal_id: 'proposal-0',
    proposal_type: 'strategy_revision',
    lifecycle_state: 'draft',
    lifecycle_label: '草稿',
    rationale: '暂无',
    trigger_type: 'manual',
    confidence: null,
    evidence_state: 'unavailable',
    evidence_label: '证据暂不可用',
    affected_strategy_version: {
      strategy_version_id: 'version-0',
      strategy_id: 'strategy-0',
      business_key: 'cn-swing-core',
      title: '空状态建议',
      version_no: 0,
      lifecycle_state: 'draft',
      lifecycle_label: '草稿',
      validation_summary: null,
      current_status: { is_current: false, current_version_id: null, previous_current_version_id: null },
    },
    base_version_id: null,
    accepted_draft_version_id: null,
    proposed_changes: {},
    evidence: {},
    available_actions: ['start_review', 'reject', 'generate_draft'],
    partial_reasons: [],
    limitations: [],
  }),
  getStrategyDraftOptions: vi.fn().mockResolvedValue({
    rule_options: [],
    author_profile_options: { method: [], rule: [], validated: [] },
    dataset_options: [],
    market_snapshot_options: [],
    rule_applicability_options: [],
  }),
  compareStrategyVersion: vi.fn(),
  createStrategyDraft: vi.fn(),
  diffStrategyVersion: vi.fn(),
  reviewStrategyRevisionProposal: vi.fn(),
  acceptStrategyRevisionProposalToDraft: vi.fn(),
  rollbackStrategyVersion: vi.fn(),
  submitStrategyReview: vi.fn(),
  publishStrategy: vi.fn(),
  validateStrategyVersion: vi.fn(),
}));

vi.mock('@/lib/api/system', () => ({
  getSystemDashboard: vi.fn().mockResolvedValue({
    status: 'partial',
    generated_at: '2026-06-13T00:00:00Z',
    health: { overall: 'warning', issues: [] },
    worker: {
      status: 'warning',
      heartbeat_at: null,
      heartbeat_age_minutes: null,
      current_job_id: null,
    },
    failed_jobs: [],
    duration_summary: {
      average_seconds: null,
      p95_seconds: null,
      recent_jobs: [],
    },
    freshness: {
      sources: [{
        source: 'saved-data',
        entity_type: '历史行情',
        last_updated: '2026-06-12T00:00:00Z',
        freshness_hours: 24,
        is_stale: true,
      }],
    },
    alerts: {
      critical: 1,
      warning: 2,
      latest: [],
    },
    traces: [],
  }),
  getSystemDataReadiness: vi.fn().mockResolvedValue({
    profile_id: 'default',
    market: 'CN',
    timezone: 'Asia/Shanghai',
    status: 'partial',
    summary: '盘后数据链路尚未全部完成，当前只能判定为部分就绪。',
    phase: 'post_close',
    target_trade_date: '2026-06-13',
    latest_update_at: '2026-06-13T09:25:00Z',
    latest_successful_update_at: '2026-06-13T09:25:00Z',
    repair_available: true,
    repair_plan: {
      status: 'needs_repair',
      steps: [{
        action: 'refresh_post_close_kaipan',
        label: '补齐盘后市场数据',
        reason: '今日盘后 Kaipan 快照缺失或非 ready。',
        target_trade_date: '2026-06-13',
      }],
    },
    facts: {
      latest_ohlcv_trade_date: '2026-06-13',
      latest_indicator_trade_date: '2026-06-13',
      dataset_snapshot_status: 'ready',
      pre_market_snapshot_status: 'ready',
      post_close_snapshot_status: 'missing',
      market_state_status: 'partial',
      missing_coverages: ['盘后市场数据'],
      unavailable_reasons: [],
    },
  }),
  getSystemDataSchedule: vi.fn().mockResolvedValue({
    timezone: 'Asia/Shanghai',
    entries: [{
      key: 'post_close_kaipan',
      label: '盘后 Kaipan 更新',
      window_start: '17:30',
      window_end: '17:30',
      dependency_order: ['refresh_post_close_kaipan', 'recompute_market_state'],
    }],
  }),
  listSystemDataOperations: vi.fn().mockResolvedValue({
    count: 1,
    items: [{
      operation_id: 'op-1',
      label: '补齐缺失数据',
      action: 'repair',
      status: 'failed',
      target_trade_date: '2026-06-13',
      created_at: '2026-06-13T17:31:00Z',
      updated_at: '2026-06-13T17:32:00Z',
      cancel_requested: false,
    }],
  }),
  createSystemDataOperation: vi.fn().mockResolvedValue({
    created: true,
    operation: {
      operation_id: 'op-2',
      label: '补齐缺失数据',
      action: 'repair',
      status: 'pending',
      target_trade_date: '2026-06-13',
      created_at: '2026-06-13T17:33:00Z',
      updated_at: '2026-06-13T17:33:00Z',
      cancel_requested: false,
    },
  }),
  cancelSystemDataOperation: vi.fn().mockResolvedValue({ operation: { operation_id: 'op-1' } }),
  retrySystemDataOperation: vi.fn().mockResolvedValue({ operation: { operation_id: 'op-1' } }),
  resumeSystemDataOperation: vi.fn().mockResolvedValue({ operation: { operation_id: 'op-1' } }),
}));

import {
  ResearchAddPage,
  ResearchArticlesPage,
  ResearchResultsPage,
} from './research';
import {
  RulesBacktestsPage,
  RulesLibraryPage,
  RulesReviewPage,
  RulesResultsPage,
} from './rules';
import { AuthorsPage } from './authors';
import {
  StrategyCandidatesPage,
  StrategyOverviewPage,
} from './strategies';
import {
  SystemConfigurationPage,
  SystemDataPage,
  SystemRunsPage,
  SystemStatusPage,
} from './system';

afterEach(cleanup);

function renderPage(element: ReactNode, role: 'viewer' | 'admin' = 'viewer') {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider
        initialPrincipal={{
          role,
          api_key_label: null,
          authenticated: true,
          source: 'session',
          username: role,
        }}
      >
        <MemoryRouter>{element}</MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe('formal product entry pages', () => {
  it.each([
    [<ResearchArticlesPage />, 'article-list'],
    [<ResearchAddPage />, 'article-add'],
    [<ResearchResultsPage />, 'article-results'],
    [<RulesLibraryPage />, 'rule-pool-product'],
    [<RulesBacktestsPage />, 'formal-backtest-product'],
    [<RulesResultsPage />, 'formal-backtest-results-product'],
    [<SystemStatusPage />, 'system-status-product'],
  ])('mounts the existing real capability', async (page, testId) => {
    renderPage(page);
    expect(await screen.findByTestId(testId)).toBeInTheDocument();
  });

  it('keeps strategies candidates as a compatibility notice page', async () => {
    renderPage(<StrategyCandidatesPage />);
    expect(await screen.findByRole('heading', { name: '候选版本' })).toBeInTheDocument();
    expect(screen.getByText('该页面仅保留兼容入口，正式策略流程已迁移到“策略中心”。')).toBeInTheDocument();
  });

  it('connects result and system pages to truthful real capability summaries', async () => {
    renderPage(<RulesResultsPage />);
    expect(screen.getByTestId('formal-backtest-results-product')).toBeInTheDocument();
    cleanup();

    renderPage(<SystemDataPage />);
    expect(await screen.findByText('补齐盘后市场数据')).toBeInTheDocument();
    expect(screen.getByText('盘后 Kaipan 更新')).toBeInTheDocument();
    cleanup();

    renderPage(<SystemRunsPage />);
    expect(await screen.findByText('失败处理')).toBeInTheDocument();
    expect(screen.getByText('严重告警')).toBeInTheDocument();
    expect(screen.getByText('一般提醒')).toBeInTheDocument();
  });

  it('does not invent author profile or strategy version counts', async () => {
    renderPage(<AuthorsPage />);
    expect(await screen.findAllByText('暂无正式画像版本')).toHaveLength(2);
    expect(screen.getByText('新证据会先生成草稿或修订建议，不会自动覆盖已发布画像。')).toBeInTheDocument();
    expect(screen.queryByText(/共 \d+ 个正式画像/)).not.toBeInTheDocument();
    expect(screen.queryByTestId('persona-product')).not.toBeInTheDocument();
    cleanup();

    renderPage(<StrategyOverviewPage />);
    expect(await screen.findByRole('heading', { name: '策略中心' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '保存策略草稿' })).toBeInTheDocument();
    expect(screen.getAllByText(/暂无正式策略版本|当前还没有正式策略版本/).length).toBeGreaterThan(0);
    expect(await screen.findByText('当前还没有正式的策略优化建议。', {}, { timeout: 3000 })).toBeInTheDocument();
    expect(screen.queryByText(/共 \d+ 个正式策略/)).not.toBeInTheDocument();
  });

  it('does not require the administrator technical-details slot for formal rule review entry', async () => {
    renderPage(<RulesReviewPage />);
    expect(screen.queryByText('管理员查看技术细节')).not.toBeInTheDocument();
    expect(await screen.findByRole('heading', { name: '规则审核工作台' })).toBeInTheDocument();
  });

  it('connects system configuration to saved records without exposing technical fields', async () => {
    renderPage(<SystemConfigurationPage />);
    expect(await screen.findByText('正式配置')).toBeInTheDocument();
    expect(screen.getByText('校验状态：已校验')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '查看现有配置' })).toHaveAttribute('href', '/profiles');
  });
});
