import type { ReactElement } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { DashboardPage } from '@/pages/dashboard';
import { AuthProvider } from '@/features/auth/auth-context';
import {
  AUDITED_LEGACY_PATHS,
  canonicalRoutes,
  compatibilityRoutes,
  primaryNavigation,
  resolveLegacyRoute,
  resolveRoute,
  routeConfig,
} from './route-config';

const expectedLegacyMetadata = {
  '/login': ['/login', 'notice', '长期保留', false, 'canonical'],
  '/': ['/', 'notice', '长期保留', false, 'canonical'],
  '/dashboard': ['/', 'redirect', 'Stage 1', true, 'compat'],
  '/jobs': ['/system/jobs', 'redirect', 'Post-delivery Task 2', true, 'compat'],
  '/jobs/:jobId': ['/system/jobs/:jobId', 'redirect', 'Post-delivery Task 2', true, 'compat'],
  '/profiles': ['/system/configuration', 'redirect', 'Stage 11', true, 'compat'],
  '/profiles/import': ['/system/configuration/import', 'redirect', 'Stage 11', true, 'compat'],
  '/profiles/:profileId': ['/system/configuration/:profileId', 'redirect', 'Stage 12', true, 'compat'],
  '/profiles/:profileId/edit': ['/system/configuration/:profileId/edit', 'redirect', 'Stage 12', true, 'compat'],
  '/profiles/:profileId/snapshots/:snapshotId': ['/system/configuration/:profileId/snapshots/:snapshotId', 'redirect', 'Stage 12', true, 'compat'],
  '/workflows': ['/system/runs', 'redirect', 'Stage 11', true, 'compat'],
  '/workflows/pre-market': ['/daily/pre-market', 'redirect', 'Stage 9', true, 'compat'],
  '/workflows/pre-market/run': ['/daily/pre-market', 'redirect', 'Stage 9', true, 'compat'],
  '/workflows/after-close': ['/daily/after-close', 'redirect', 'Stage 10', true, 'compat'],
  '/workflows/after-close/run': ['/daily/after-close', 'redirect', 'Stage 10', true, 'compat'],
  '/workflows/:workflowId/run': ['/system/runs', 'redirect', 'Stage 12', true, 'compat'],
  '/articles': ['/research/articles', 'redirect', 'Stage 1', true, 'compat'],
  '/articles/run': ['/research/add', 'redirect', 'Stage 3', true, 'compat'],
  '/articles/list': ['/research/articles', 'redirect', 'Stage 3', true, 'compat'],
  '/articles/quality': ['/research/results', 'redirect', 'Stage 3', true, 'compat'],
  '/articles/results': ['/research/results', 'redirect', 'Stage 4', true, 'compat'],
  '/alerts': ['/system/runs', 'redirect', 'Stage 11', true, 'compat'],
  '/backtest': ['/rules/backtests', 'redirect', 'Stage 6', true, 'compat'],
  '/backtest/regime': ['/rules/results', 'redirect', 'Stage 12', true, 'compat'],
  '/backtest/candidates': ['/strategies/candidates', 'redirect', 'Stage 8', true, 'compat'],
  '/rule-pool': ['/rules/review', 'redirect', 'Stage 4', true, 'compat'],
  '/rule-pool/:ruleId': ['/rules/library', 'redirect', 'Stage 12', true, 'compat'],
  '/artifacts': ['/system/runs', 'redirect', 'Stage 12', true, 'compat'],
  '/artifacts/:artifactId': ['/system/runs', 'redirect', 'Stage 12', true, 'compat'],
  '/market': ['/system/data', 'redirect', 'Stage 5', true, 'compat'],
  '/market/snapshots': ['/system/data', 'redirect', 'Stage 12', true, 'compat'],
  '/market/datasets': ['/system/data', 'redirect', 'Stage 12', true, 'compat'],
  '/market/kaipan': ['/system/data', 'redirect', 'Stage 5', true, 'compat'],
  '/market/ohlcv': ['/system/data', 'redirect', 'Stage 5', true, 'compat'],
  '/strategies': ['/strategies', 'notice', '长期保留', false, 'canonical'],
  '/persona': ['/authors', 'redirect', 'Stage 7', true, 'compat'],
  '/strategies/pre-market': ['/daily/pre-market', 'redirect', 'Stage 9', true, 'compat'],
  '/strategies/after-close': ['/daily/after-close', 'redirect', 'Stage 10', true, 'compat'],
  '/system': ['/system/status', 'notice', '长期保留', false, 'canonical'],
  '/system/audit': ['/system/audit', 'notice', '长期保留', false, 'canonical'],
  '/system/users': ['/system/users', 'notice', '长期保留', false, 'canonical'],
  '/system/health': ['/system/health', 'notice', '长期保留', false, 'canonical'],
  '/system/db-migrate': ['/system/db-migrate', 'notice', '长期保留', false, 'canonical'],
  '/system/backup': ['/system/backup', 'notice', '长期保留', false, 'canonical'],
  '/admin': ['/system/status', 'redirect', 'Stage 12', true, 'compat'],
  '/admin/audit': ['/system/audit', 'redirect', 'Stage 12', true, 'compat'],
  '/system/restore': ['/system/backup', 'redirect', 'Stage 12', true, 'compat'],
  '/settings': ['/system/configuration', 'redirect', 'Stage 12', true, 'compat'],
  '*': ['*', 'notice', '长期保留', false, 'canonical'],
} as const;

describe('route config', () => {
  it('exposes exactly seven product navigation entries', () => {
    expect(primaryNavigation.map((item) => [item.label, item.path])).toEqual([
      ['首页', '/'],
      ['研究中心', '/research'],
      ['规则与回测', '/rules'],
      ['作者画像', '/authors'],
      ['策略中心', '/strategies'],
      ['每日交易', '/daily'],
      ['系统管理', '/system'],
    ]);
  });

  it('does not expose developer terms in primary navigation', () => {
    const text = JSON.stringify(primaryNavigation);

    for (const term of ['Job', 'Workflow', 'Pipeline', 'Artifact', 'Provider', 'Schema', 'CLI']) {
      expect(text).not.toContain(term);
    }
  });

  it('defines the Stage 1 canonical entry behavior', () => {
    expect(resolveRoute('/')?.label).toBe('首页');
    expect(resolveLegacyRoute('/dashboard')?.legacy).toMatchObject({
      targetPath: '/',
      mode: 'redirect',
    });
    expect(resolveLegacyRoute('/articles')?.legacy).toMatchObject({
      targetPath: '/research/articles',
      mode: 'redirect',
    });
    expect(resolveRoute('/strategies')?.label).toBe('策略中心');
    expect(resolveRoute('/missing-page')?.label).toBe('页面未找到');
  });

  it('classifies all 49 audited paths exactly once with explicit expected metadata', () => {
    expect(AUDITED_LEGACY_PATHS).toHaveLength(49);
    expect(Object.keys(expectedLegacyMetadata)).toHaveLength(49);

    for (const path of AUDITED_LEGACY_PATHS) {
      expect(routeConfig.filter((route) => route.path === path), path).toHaveLength(1);

      const configured = resolveLegacyRoute(path);
      const [targetPath, mode, retireStage, retirementRequired, kind] = expectedLegacyMetadata[path];
      expect(configured?.kind, path).toBe(kind);
      expect(configured?.legacy, path).toMatchObject({
        targetPath,
        mode,
        retireStage,
        retirementRequired,
      });
      expect(configured?.legacy?.retireCondition, path).toBeTruthy();
    }
  });

  it('derives canonical and compatibility routes only from explicit kind', () => {
    expect(canonicalRoutes).toEqual(routeConfig.filter((route) => route.kind === 'canonical'));
    expect(compatibilityRoutes).toEqual(routeConfig.filter((route) => route.kind === 'compat'));
    expect(resolveRoute('/jobs/job-1')?.kind).toBe('compat');
  });

  it('marks every formal product route canonical', () => {
    const formalPaths = [
      '/login',
      '/',
      '/research',
      '/research/articles',
      '/research/add',
      '/research/results',
      '/rules',
      '/rules/review',
      '/rules/library',
      '/rules/backtests',
      '/rules/results',
      '/authors',
      '/strategies',
      '/daily',
      '/daily/overview',
      '/daily/pre-market',
      '/daily/after-close',
      '/system',
      '/system/status',
      '/system/configuration',
      '/system/configuration/import',
      '/system/configuration/:profileId',
      '/system/configuration/:profileId/edit',
      '/system/configuration/:profileId/snapshots/:snapshotId',
      '/system/data',
      '/system/jobs',
      '/system/jobs/:jobId',
      '/system/jobs/new',
      '/system/runs',
      '/system/audit',
      '/system/users',
      '/system/health',
      '/system/db-migrate',
      '/system/backup',
      '*',
    ];

    for (const path of formalPaths) {
      const route = path === '*' ? routeConfig.find((item) => item.path === path) : resolveRoute(path);
      expect(route?.kind, path).toBe('canonical');
    }
  });

  it('keeps pre-market and after-close strategy legacy paths compatibility-only until their stages', () => {
    expect(resolveRoute('/strategies/candidates')?.kind).toBe('canonical');
    expect(resolveRoute('/strategies/pre-market')?.kind).toBe('compat');
    expect(resolveRoute('/strategies/pre-market')?.legacy?.retireStage).toBe('Stage 9');
    expect(resolveRoute('/strategies/pre-market')?.renderMode).toBe('redirect');
    expect(resolveRoute('/strategies/after-close')?.kind).toBe('compat');
    expect(resolveRoute('/strategies/after-close')?.legacy?.retireStage).toBe('Stage 10');
    expect(resolveRoute('/strategies/after-close')?.renderMode).toBe('redirect');
  });

  it('redirects every retired legacy candidate to a formal product or System Management entry', () => {
    for (const path of [
      '/jobs',
      '/jobs/:jobId',
      '/profiles',
      '/profiles/import',
      '/profiles/:profileId',
      '/profiles/:profileId/edit',
      '/profiles/:profileId/snapshots/:snapshotId',
      '/workflows',
      '/workflows/:workflowId/run',
      '/articles/run',
      '/articles/list',
      '/articles/quality',
      '/articles/results',
      '/alerts',
      '/backtest',
      '/backtest/regime',
      '/backtest/candidates',
      '/rule-pool',
      '/rule-pool/:ruleId',
      '/artifacts',
      '/artifacts/:artifactId',
      '/market',
      '/market/snapshots',
      '/market/datasets',
      '/market/kaipan',
      '/market/ohlcv',
      '/persona',
      '/strategies/pre-market',
      '/strategies/after-close',
    ]) {
      expect(resolveRoute(path)?.renderMode, path).toBe('redirect');
      expect(resolveRoute(path)?.legacy?.mode, path).toBe('redirect');
    }
  });

  it('mounts the formal business contract at new product routes', () => {
    const route = resolveRoute('/research/articles');
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider
          initialPrincipal={{
            role: 'viewer',
            api_key_label: null,
            authenticated: true,
            source: 'session',
            username: 'viewer',
          }}
        >
          <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
            {route?.element}
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>,
    );

    expect(screen.getByRole('heading', { name: '文章库' })).toBeInTheDocument();
    expect(screen.queryByText('正式业务页面')).not.toBeInTheDocument();
    for (const heading of ['页面用途', '输入', '处理状态', '输出']) {
      expect(screen.getByText(heading)).toBeInTheDocument();
    }
    expect(screen.queryByText('下一步')).not.toBeInTheDocument();
  });

  it('uses concrete page components for every formal page in Session B', () => {
    const formalPagePaths = [
      '/system',
      '/research/articles',
      '/research/add',
      '/research/results',
      '/rules/review',
      '/rules/library',
      '/rules/backtests',
      '/rules/results',
      '/authors',
      '/strategies',
      '/strategies/candidates',
      '/daily/overview',
      '/daily/pre-market',
      '/daily/after-close',
      '/system/status',
      '/system/configuration',
      '/system/configuration/import',
      '/system/configuration/:profileId',
      '/system/configuration/:profileId/edit',
      '/system/configuration/:profileId/snapshots/:snapshotId',
      '/system/data',
      '/system/jobs',
      '/system/jobs/:jobId',
      '/system/jobs/new',
      '/system/runs',
    ];
    for (const path of formalPagePaths) {
      const elementType = (resolveRoute(path)?.element as ReactElement).type;
      expect(typeof elementType, path).toBe('function');
    }
  });

  it('renders the existing real dashboard at the canonical home route', () => {
    expect((resolveRoute('/')?.element as ReactElement).type).toBe(DashboardPage);
  });

  it('keeps system overview routes open to all authenticated roles in metadata', () => {
    expect(resolveRoute('/system')?.minRole).toBeUndefined();
    expect(resolveRoute('/system/status')?.minRole).toBeUndefined();
    expect(resolveRoute('/system/configuration')?.minRole).toBeUndefined();
    expect(resolveRoute('/system/configuration/import')?.minRole).toBe('operator');
    expect(resolveRoute('/system/configuration/default')?.minRole).toBeUndefined();
    expect(resolveRoute('/system/configuration/default/edit')?.minRole).toBe('operator');
    expect(resolveRoute('/system/configuration/default/snapshots/snapshot-1')?.minRole).toBeUndefined();
    expect(resolveRoute('/system/data')?.minRole).toBeUndefined();
    expect(resolveRoute('/system/jobs')?.minRole).toBeUndefined();
    expect(resolveRoute('/system/jobs/job-1')?.minRole).toBeUndefined();
    expect(resolveRoute('/system/jobs/new')?.minRole).toBe('operator');
    expect(resolveRoute('/system/runs')?.minRole).toBeUndefined();
    expect(resolveRoute('/system/audit')?.minRole).toBe('admin');
    expect(resolveRoute('/system/users')?.minRole).toBe('admin');
    expect(resolveRoute('/system/db-migrate')?.minRole).toBe('admin');
    expect(resolveRoute('/system/backup')?.minRole).toBe('admin');
  });

  it('keeps legacy job paths pointed at formal job management, not runs and alerts', () => {
    expect(resolveLegacyRoute('/jobs')?.legacy).toMatchObject({
      targetPath: '/system/jobs',
      mode: 'redirect',
    });
    expect(resolveLegacyRoute('/jobs/:jobId')?.legacy).toMatchObject({
      targetPath: '/system/jobs/:jobId',
      mode: 'redirect',
    });
    expect(resolveRoute('/system/jobs')?.kind).toBe('canonical');
    expect(resolveRoute('/system/jobs/job-1')?.kind).toBe('canonical');
    expect(resolveRoute('/system/jobs/new')?.kind).toBe('canonical');
  });
});
