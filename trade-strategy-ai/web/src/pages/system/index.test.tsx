import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { SystemDataPage, SystemPage } from './index';
import { renderWithRouter } from '@/test/test-utils';

vi.mock('@/lib/api/profiles', () => ({
  listProfiles: vi.fn(),
}));

vi.mock('@/lib/api/system', () => ({
  cancelSystemDataOperation: vi.fn(),
  createSystemDataOperation: vi.fn(),
  getSystemDashboard: vi.fn(),
  getSystemDataReadiness: vi.fn(),
  getSystemDataSchedule: vi.fn(),
  listSystemDataOperations: vi.fn(),
  resumeSystemDataOperation: vi.fn(),
  retrySystemDataOperation: vi.fn(),
}));

import { getSystemDataReadiness, getSystemDataSchedule, listSystemDataOperations } from '@/lib/api/system';

const mockedGetSystemDataReadiness = vi.mocked(getSystemDataReadiness);
const mockedGetSystemDataSchedule = vi.mocked(getSystemDataSchedule);
const mockedListSystemDataOperations = vi.mocked(listSystemDataOperations);

beforeEach(() => {
  mockedGetSystemDataReadiness.mockReset();
  mockedGetSystemDataSchedule.mockReset();
  mockedListSystemDataOperations.mockReset();
});

describe('SystemPage', () => {
  it('renders the grouped system management hub for admin principals', async () => {
    renderWithRouter([{ path: '/system', element: <SystemPage /> }], ['/system'], {
      initialPrincipal: {
        role: 'admin',
        api_key_label: 'Local Admin',
        authenticated: true,
        source: 'api_key',
      },
    });

    expect(await screen.findByRole('heading', { name: '系统管理' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '七类系统管理入口' })).toBeInTheDocument();
    for (const group of [
      'Profile 配置',
      '数据源',
      '数据与调度',
      '任务运行',
      '失败与告警',
      '数据库与备份',
      '权限与审计',
    ]) {
      expect(screen.getAllByRole('heading', { name: group }).length).toBeGreaterThan(0);
    }
    expect(screen.getByRole('button', { name: '打开 数据库与备份' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '打开 权限与审计' })).toBeInTheDocument();
  });

  it('shows only status and repair entry points for viewer principals', async () => {
    const { container } = renderWithRouter([{ path: '/system', element: <SystemPage /> }], ['/system'], {
      initialPrincipal: {
        role: 'viewer',
        api_key_label: 'Local Viewer',
        authenticated: true,
        source: 'api_key',
      },
    });

    expect(await screen.findByRole('heading', { name: '系统管理' })).toBeInTheDocument();
    for (const entry of ['系统状态', '配置管理', '数据与调度', '运行与告警']) {
      expect(screen.getByRole('button', { name: `进入 ${entry}` })).toBeInTheDocument();
    }
    expect(screen.queryByRole('heading', { name: '七类系统管理入口' })).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: '数据库与备份' })).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: '权限与审计' })).not.toBeInTheDocument();
    for (const term of [
      'Jo' + 'b',
      'Work' + 'flow',
      'Pipe' + 'line',
      'Arti' + 'fact',
      'Pro' + 'vider',
      'config_' + 'path',
      'prompt_' + 'run_' + 'id',
      'run_' + 'id',
    ]) {
      expect(container.textContent).not.toContain(term);
    }
  });

  it('shows the full hub but keeps admin-only actions unavailable for operator principals', async () => {
    renderWithRouter([{ path: '/system', element: <SystemPage /> }], ['/system'], {
      initialPrincipal: {
        role: 'operator',
        api_key_label: 'Local Operator',
        authenticated: true,
        source: 'api_key',
      },
    });

    expect(await screen.findByRole('heading', { name: '系统管理' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '七类系统管理入口' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '数据库与备份' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '权限与审计' })).toBeInTheDocument();
    expect(screen.getAllByText('仅管理员可以进入此分类。')).toHaveLength(2);
    expect(screen.queryByRole('button', { name: '打开 数据库与备份' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '打开 权限与审计' })).not.toBeInTheDocument();
  });

  it('uses Chinese business wording on the data scheduling page shell', async () => {
    const { container } = renderWithRouter(
      [{ path: '/system/data', element: <SystemDataPage availability="error" /> }],
      ['/system/data'],
      {
        initialPrincipal: {
          role: 'viewer',
          api_key_label: 'Viewer',
          authenticated: true,
          source: 'api_key',
        },
      },
    );

    expect(await screen.findByRole('heading', { name: '数据与调度' })).toBeInTheDocument();
    expect(container.textContent).not.toContain('readiness');
  });

  it('shows /market/datasets under the system data compatibility mapping', async () => {
    mockedGetSystemDataReadiness.mockResolvedValue({
      status: 'ready',
      target_trade_date: '2026-06-22',
      phase: 'post_close',
      latest_successful_update_at: '2026-06-22T10:00:00Z',
      summary: '正式数据已就绪。',
      repair_available: false,
      facts: {
        latest_ohlcv_trade_date: '2026-06-22',
        latest_indicator_trade_date: '2026-06-22',
        dataset_snapshot_status: 'ready',
        pre_market_snapshot_status: 'ready',
        post_close_snapshot_status: 'ready',
        market_state_status: 'ready',
        unavailable_reasons: [],
        missing_coverages: [],
      },
      repair_plan: {
        steps: [],
      },
    } as never);
    mockedGetSystemDataSchedule.mockResolvedValue({
      timezone: 'Asia/Shanghai',
      entries: [],
    } as never);
    mockedListSystemDataOperations.mockResolvedValue({
      items: [],
      total: 0,
      limit: 20,
      offset: 0,
    } as never);

    renderWithRouter(
      [{ path: '/system/data', element: <SystemDataPage /> }],
      ['/system/data'],
      {
        initialPrincipal: {
          role: 'viewer',
          api_key_label: 'Viewer',
          authenticated: true,
          source: 'api_key',
        },
      },
    );

    expect(await screen.findByText('数据源兼容入口')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '回测数据版本详情' })).toHaveAttribute('href', '/market/datasets');
  });

  it.each([
    ['invalid', '状态无效', '正式数据存在无效状态，不能继续依赖。', '先修复无效状态，再重新进入当前页面。'],
    ['conflict', '数据冲突', '正式数据之间存在冲突，需要先修复再继续。', '先确认冲突来源并完成修复，再继续后续操作。'],
    ['insufficient_coverage', '覆盖不足', '覆盖范围不足，不能把结果当成正式就绪。', '先查看受限原因，再补齐缺失依赖或联系管理员处理。'],
    ['failed', '执行失败', '最近一次正式操作失败，需要人工处理。', '查看失败原因后重新处理。'],
  ] as const)('maps readiness status %s to truthful product-page error copy', async (status, title, impact, repair) => {
    mockedGetSystemDataReadiness.mockResolvedValue({
      status,
      target_trade_date: '2026-06-22',
      phase: 'post_close',
      latest_successful_update_at: '2026-06-22T10:00:00Z',
      summary: '测试摘要。',
      repair_available: false,
      facts: {
        latest_ohlcv_trade_date: '2026-06-22',
        latest_indicator_trade_date: '2026-06-22',
        dataset_snapshot_status: 'ready',
        pre_market_snapshot_status: 'ready',
        post_close_snapshot_status: 'ready',
        market_state_status: 'ready',
        unavailable_reasons: [],
        missing_coverages: [],
      },
      repair_plan: {
        steps: [],
      },
    } as never);
    mockedGetSystemDataSchedule.mockResolvedValue({
      timezone: 'Asia/Shanghai',
      entries: [],
    } as never);
    mockedListSystemDataOperations.mockResolvedValue({
      items: [],
      total: 0,
      limit: 20,
      offset: 0,
    } as never);

    renderWithRouter(
      [{ path: '/system/data', element: <SystemDataPage /> }],
      ['/system/data'],
      {
        initialPrincipal: {
          role: 'viewer',
          api_key_label: 'Viewer',
          authenticated: true,
          source: 'api_key',
        },
      },
    );

    expect(await screen.findAllByText(title)).not.toHaveLength(0);
    expect(screen.getByText('发生了什么')).toBeInTheDocument();
    expect(screen.getAllByText('测试摘要。').length).toBeGreaterThan(0);
    expect(screen.getByText(impact)).toBeInTheDocument();
    expect(screen.getByText(repair)).toBeInTheDocument();
  });
});
