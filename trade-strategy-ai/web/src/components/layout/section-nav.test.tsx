import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { AuthProvider } from '@/features/auth/auth-context';
import { SectionNav } from './section-nav';

function renderSectionNav(parentId: string, pathname: string, role: 'viewer' | 'admin' = 'viewer') {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }} initialEntries={[pathname]}>
        <AuthProvider
          initialPrincipal={{
            role,
            api_key_label: 'Local User',
            authenticated: true,
            source: 'api_key',
          }}
        >
          <SectionNav parentId={parentId} />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('SectionNav', () => {
  it('renders the business section navigation and omits inaccessible items', () => {
    renderSectionNav('system', '/system/status', 'viewer');

    expect(screen.getByRole('navigation', { name: '业务分区导航' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '系统状态' })).toHaveAttribute('href', '/system/status');
    expect(screen.getByRole('link', { name: '系统状态' })).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('link', { name: '配置管理' })).toBeInTheDocument();
    expect(screen.getByText('数据与调度')).toBeInTheDocument();
    expect(screen.queryByText('用户管理')).not.toBeInTheDocument();
    expect(screen.queryByText('权限与审计')).not.toBeInTheDocument();
  });
});
