import { describe, expect, it } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { screen, render } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { AuthProvider } from '@/features/auth/auth-context';
import { Sidebar } from './sidebar';

describe('Sidebar', () => {
  it('keeps the system management entry available to viewer principals', () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <AuthProvider
            initialPrincipal={{
              role: 'viewer',
              api_key_label: 'Local Viewer',
              authenticated: true,
              source: 'api_key',
            }}
          >
            <Sidebar />
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByRole('link', { name: /系统管理/ })).toHaveAttribute('href', '/system');
    expect(screen.getByRole('link', { name: /系统管理/ })).not.toHaveAttribute('aria-disabled');
    expect(screen.getByText('交易策略助手')).toBeInTheDocument();
    expect(screen.getByText('研究、验证与每日决策')).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: '主要功能' })).toBeInTheDocument();
    expect(screen.queryByText('trade-strategy-ai')).not.toBeInTheDocument();
    expect(screen.queryByText('Web control console')).not.toBeInTheDocument();
  });
});
