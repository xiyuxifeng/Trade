import { describe, expect, it } from 'vitest';
import { screen } from '@testing-library/react';
import { SystemDataPage, SystemPage } from './index';
import { renderWithRouter } from '@/test/test-utils';

describe('SystemPage', () => {
  it('renders the management hub and entry cards for admin principals', async () => {
    renderWithRouter([{ path: '/system', element: <SystemPage /> }], ['/system'], {
      initialPrincipal: {
        role: 'admin',
        api_key_label: 'Local Admin',
        authenticated: true,
        source: 'api_key',
      },
    });

    expect(await screen.findByRole('heading', { name: '系统管理' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /权限与审计/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /用户管理/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /系统健康检查/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /数据库迁移/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /数据备份与恢复/ })).toBeInTheDocument();
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
