import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { AuthProvider } from '@/features/auth/auth-context';
import { DashboardLayout } from './dashboard-layout';

vi.mock('@/components/layout/sidebar', () => ({
  Sidebar: () => <aside>一级导航</aside>,
}));

vi.mock('@/components/layout/topbar', () => ({
  Topbar: ({ title }: { title: string }) => <header>{title}</header>,
}));

vi.mock('@/components/layout/status-strip', () => ({
  StatusStrip: ({
    title,
    description,
    kind,
  }: {
    title: string;
    description: string;
    kind?: 'canonical' | 'compat';
  }) => (
    <div>
      <span>{title}</span>
      <span>{description}</span>
      <span>{kind}</span>
    </div>
  ),
}));

vi.mock('@/components/layout/section-nav', () => ({
  SectionNav: ({ parentId }: { parentId: string }) => (
    <nav aria-label={`二级导航：${parentId}`}>二级导航：{parentId}</nav>
  ),
}));

function renderLayout(pathname: string) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter
        initialEntries={[pathname]}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <AuthProvider
          initialPrincipal={{
            role: 'viewer',
            api_key_label: 'Local Viewer',
            authenticated: true,
            source: 'api_key',
          }}
        >
          <Routes>
            <Route element={<DashboardLayout />}>
              <Route path="*" element={<div>页面内容</div>} />
            </Route>
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('DashboardLayout', () => {
  it('derives formal route metadata and section navigation from route config', () => {
    renderLayout('/rules/review');

    expect(screen.getAllByText('待审核规则')).toHaveLength(2);
    expect(screen.getByText('审核从文章中提取的候选规则。')).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: '二级导航：rules' })).toBeInTheDocument();
    expect(screen.getByText('canonical')).toBeInTheDocument();
  });

  it('does not render section navigation for a compatibility route without a formal parent', () => {
    renderLayout('/jobs');

    expect(screen.getAllByText('运行记录')).toHaveLength(2);
    expect(screen.getByText('compat')).toBeInTheDocument();
    expect(screen.queryByText(/二级导航：/)).not.toBeInTheDocument();
  });
});
