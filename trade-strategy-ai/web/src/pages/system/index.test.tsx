import { describe, expect, it } from 'vitest';
import { screen } from '@testing-library/react';
import { SystemDataPage, SystemPage } from './index';
import { renderWithRouter } from '@/test/test-utils';

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
});
