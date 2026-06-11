import type { ReactElement } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { DashboardPage } from '@/pages/dashboard';
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
  '/jobs': ['/system/runs', 'notice', 'Stage 12', true, 'compat'],
  '/jobs/:jobId': ['/jobs/:jobId', 'notice', '长期保留', false, 'compat'],
  '/profiles': ['/system/configuration', 'notice', 'Stage 11', true, 'compat'],
  '/profiles/import': ['/system/configuration', 'notice', 'Stage 11', true, 'compat'],
  '/profiles/:profileId': ['/system/configuration', 'notice', 'Stage 11', true, 'compat'],
  '/profiles/:profileId/edit': ['/system/configuration', 'notice', 'Stage 11', true, 'compat'],
  '/profiles/:profileId/snapshots/:snapshotId': ['/system/configuration', 'notice', 'Stage 11', true, 'compat'],
  '/workflows': ['/system/runs', 'notice', 'Stage 11', true, 'compat'],
  '/workflows/pre-market': ['/daily/pre-market', 'redirect', 'Stage 9', true, 'compat'],
  '/workflows/pre-market/run': ['/daily/pre-market', 'redirect', 'Stage 9', true, 'compat'],
  '/workflows/after-close': ['/daily/after-close', 'redirect', 'Stage 10', true, 'compat'],
  '/workflows/after-close/run': ['/daily/after-close', 'redirect', 'Stage 10', true, 'compat'],
  '/workflows/:workflowId/run': ['/system/runs', 'notice', 'Stage 11', true, 'compat'],
  '/articles': ['/research/articles', 'redirect', 'Stage 1', true, 'compat'],
  '/articles/run': ['/research/add', 'notice', 'Stage 3', true, 'compat'],
  '/articles/list': ['/research/articles', 'notice', 'Stage 3', true, 'compat'],
  '/articles/quality': ['/research/results', 'notice', 'Stage 3', true, 'compat'],
  '/articles/results': ['/research/results', 'notice', 'Stage 4', true, 'compat'],
  '/alerts': ['/system/runs', 'notice', 'Stage 11', true, 'compat'],
  '/backtest': ['/rules/backtests', 'notice', 'Stage 6', true, 'compat'],
  '/backtest/regime': ['/rules/results', 'notice', 'Stage 6', true, 'compat'],
  '/backtest/candidates': ['/strategies/candidates', 'notice', 'Stage 8', true, 'compat'],
  '/rule-pool': ['/rules/review', 'notice', 'Stage 4', true, 'compat'],
  '/rule-pool/:ruleId': ['/rules/library', 'notice', 'Stage 4', true, 'compat'],
  '/artifacts': ['/system/runs', 'notice', 'Stage 12', true, 'compat'],
  '/artifacts/:artifactId': ['/system/runs', 'notice', 'Stage 12', true, 'compat'],
  '/market': ['/system/data', 'notice', 'Stage 5', true, 'compat'],
  '/market/snapshots': ['/system/data', 'notice', 'Stage 11', true, 'compat'],
  '/market/datasets': ['/rules/backtests', 'notice', 'Stage 11', true, 'compat'],
  '/market/kaipan': ['/system/data', 'notice', 'Stage 5', true, 'compat'],
  '/market/ohlcv': ['/system/data', 'notice', 'Stage 5', true, 'compat'],
  '/strategies': ['/strategies', 'notice', '长期保留', false, 'canonical'],
  '/persona': ['/authors', 'notice', 'Stage 7', true, 'compat'],
  '/strategies/pre-market': ['/daily/pre-market', 'notice', 'Stage 9', true, 'compat'],
  '/strategies/after-close': ['/daily/after-close', 'notice', 'Stage 10', true, 'compat'],
  '/system': ['/system/status', 'redirect', '长期保留', false, 'canonical'],
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
      '/strategies/candidates',
      '/daily',
      '/daily/overview',
      '/daily/pre-market',
      '/daily/after-close',
      '/system',
      '/system/status',
      '/system/configuration',
      '/system/data',
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

  it('uses an honest migration notice instead of mounting legacy engineering pages at new formal routes', () => {
    const route = resolveRoute('/research/articles');
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          {route?.element}
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByRole('heading', { name: '文章库入口迁移中' })).toBeInTheDocument();
    expect(screen.getByText(/当前真实能力仍在兼容入口中/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '前往当前可用入口' })).toHaveAttribute('href', '/articles/list');
    expect(screen.getByRole('link', { name: '返回研究中心' })).toHaveAttribute('href', '/research');
  });

  it('uses the migration entry component for every new formal page in Task 1', () => {
    const migrationPaths = [
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
      '/system/data',
      '/system/runs',
    ];
    const migrationEntryType = (resolveRoute('/research/articles')?.element as ReactElement).type;

    for (const path of migrationPaths) {
      expect((resolveRoute(path)?.element as ReactElement).type, path).toBe(migrationEntryType);
    }
  });

  it('renders the existing real dashboard at the canonical home route', () => {
    expect((resolveRoute('/')?.element as ReactElement).type).toBe(DashboardPage);
  });

  it('keeps system overview routes open to all authenticated roles in metadata', () => {
    expect(resolveRoute('/system')?.minRole).toBeUndefined();
    expect(resolveRoute('/system/status')?.minRole).toBeUndefined();
    expect(resolveRoute('/system/configuration')?.minRole).toBeUndefined();
    expect(resolveRoute('/system/data')?.minRole).toBeUndefined();
    expect(resolveRoute('/system/runs')?.minRole).toBeUndefined();
    expect(resolveRoute('/system/audit')?.minRole).toBe('admin');
    expect(resolveRoute('/system/users')?.minRole).toBe('admin');
    expect(resolveRoute('/system/db-migrate')?.minRole).toBe('admin');
    expect(resolveRoute('/system/backup')?.minRole).toBe('admin');
  });
});
