import { describe, expect, it } from 'vitest';
import { screen } from '@testing-library/react';
import { AdminPage } from './index';
import { renderWithRouter } from '@/test/test-utils';

describe('AdminPage', () => {
  it('renders the admin hub for admin principals', async () => {
    renderWithRouter(
      [{ path: '/admin', element: <AdminPage /> }],
      ['/admin'],
      {
        initialPrincipal: {
          role: 'admin',
          api_key_label: 'Local Admin',
          authenticated: true,
          source: 'api_key',
        },
      },
    );

    expect(await screen.findByRole('heading', { name: '管理入口' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '权限与审计' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '配置管理' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '系统管理' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '返回总览' })).toBeInTheDocument();
  });
});
