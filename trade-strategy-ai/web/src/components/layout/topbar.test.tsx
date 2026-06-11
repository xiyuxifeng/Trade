import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { AuthProvider } from '@/features/auth/auth-context';
import { Topbar } from './topbar';

describe('Topbar', () => {
  it('uses Chinese navigation and role labels', () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <AuthProvider
            initialPrincipal={{
              role: 'viewer',
              username: 'alice',
              api_key_label: null,
              authenticated: true,
              source: 'session',
            }}
          >
            <Topbar title="首页" onMenuClick={vi.fn()} />
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByRole('button', { name: /打开导航/ })).toBeInTheDocument();
    expect(screen.getByText('只读用户')).toBeInTheDocument();
    expect(screen.queryByText('Menu')).not.toBeInTheDocument();
    expect(screen.queryByText('viewer')).not.toBeInTheDocument();
  });
});
