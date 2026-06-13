import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { getSystemDashboard } from '@/lib/api/system';
import { HomePage } from '.';

vi.mock('@/lib/api/system', () => ({
  getSystemDashboard: vi.fn(),
}));

describe('HomePage', () => {
  it('renders the business dashboard instead of the legacy tool overview', async () => {
    vi.mocked(getSystemDashboard).mockResolvedValue({
      status: 'ok',
      generated_at: '2026-06-13T02:00:00Z',
      business_date: '2026-06-13',
      is_trading_day: false,
      latest_trading_day: '2026-06-12',
      next_action: { id: 'view_status', label: '查看今日状态', target_path: '/daily/overview' },
      business_status: {},
      health: { overall: 'healthy', issues: [] },
      worker: { status: 'warning', heartbeat_at: null, heartbeat_age_minutes: null, current_job_id: null },
      failed_jobs: [],
      duration_summary: { average_seconds: null, p95_seconds: null, recent_jobs: [] },
      freshness: { sources: [] },
      alerts: { critical: 0, warning: 0, latest: [] },
      traces: [],
    });
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter><HomePage /></MemoryRouter>
      </QueryClientProvider>,
    );

    expect(await screen.findByRole('heading', { name: '今日决策首页' })).toBeInTheDocument();
    expect(screen.getByText('从文章到盘后的业务流程')).toBeInTheDocument();
    expect(screen.queryByText('从文章到复盘的主工作台')).not.toBeInTheDocument();
  });
});
