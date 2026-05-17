import { describe, expect, it } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { screen, render } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { AuthProvider } from '@/features/auth/auth-context';
import { Sidebar } from './sidebar';

describe('Sidebar', () => {
  it('disables admin-only management navigation for viewer principals', () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
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

    expect(screen.getByRole('link', { name: /管理中心/ })).toHaveAttribute(
      'aria-disabled',
      'true',
    );
    expect(screen.getByText('viewer')).toBeInTheDocument();
  });
});
