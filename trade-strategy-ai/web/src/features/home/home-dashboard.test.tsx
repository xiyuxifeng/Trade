import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import type { SystemDashboardResponse } from '@/types/system';
import { HomeDashboard } from './home-dashboard';

function dashboard(overrides: Partial<SystemDashboardResponse> = {}): SystemDashboardResponse {
  return {
    status: 'partial',
    generated_at: '2026-06-13T02:00:00Z',
    business_date: '2026-06-13',
    is_trading_day: false,
    latest_trading_day: '2026-06-12',
    next_action: {
      id: 'repair_data',
      label: '补齐缺失数据',
      target_path: '/system/data',
    },
    business_status: {
      data_readiness: businessStatus('blocked', null, '今日数据缺失', '/system/data'),
      premarket: businessStatus('pending', false, '今日盘前尚未完成', '/daily/pre-market'),
      postmarket: businessStatus('complete', true, '最近交易日盘后已完成', '/daily/after-close'),
      pending_rules: businessStatus('ready', 3, '有 3 条规则待审核', '/rules/review'),
      profile_proposals: businessStatus('unavailable', null, '画像建议能力尚未建立', '/authors'),
      strategy_proposals: businessStatus('unavailable', null, '策略建议能力尚未建立', '/strategies'),
      current_strategy: businessStatus('ready', '策略 2026.06', '当前策略版本', '/strategies'),
      market_state: businessStatus('partial', '震荡', '当前市场状态置信度不足', '/daily/overview'),
      failed_runs: businessStatus('ready', 1, '有 1 项失败运行', '/system/runs'),
    },
    health: { overall: 'warning', issues: [] },
    worker: { status: 'warning', heartbeat_at: null, heartbeat_age_minutes: null, current_job_id: null },
    failed_jobs: [],
    duration_summary: { average_seconds: null, p95_seconds: null, recent_jobs: [] },
    freshness: { sources: [] },
    alerts: { critical: 0, warning: 0, latest: [] },
    traces: [],
    ...overrides,
  };
}

function businessStatus(status: 'ready' | 'pending' | 'complete' | 'blocked' | 'partial' | 'unavailable', value: string | number | boolean | null, label: string, targetPath: string) {
  return {
    status,
    value,
    label,
    detail: label,
    source: 'test',
    updated_at: null,
    target_path: targetPath,
    unavailable_reason: status === 'unavailable' ? label : null,
  };
}

describe('HomeDashboard', () => {
  it('shows one primary action and the nine truthful business states', () => {
    render(<MemoryRouter><HomeDashboard dashboard={dashboard()} /></MemoryRouter>);

    expect(screen.getAllByRole('link', { name: '补齐缺失数据' })).toHaveLength(1);
    expect(screen.getAllByText('画像建议能力尚未建立').length).toBeGreaterThan(0);
    expect(screen.getAllByText('策略建议能力尚未建立').length).toBeGreaterThan(0);
    expect(screen.getByText(/部分状态暂不可用/)).toBeInTheDocument();
    expect(screen.getAllByTestId('home-business-status')).toHaveLength(9);
    expect(screen.queryByText('最近 Job')).not.toBeInTheDocument();
    expect(screen.queryByText('Artifact')).not.toBeInTheDocument();
    expect(screen.queryByText('Worker')).not.toBeInTheDocument();
  });

  it('does not turn unavailable values into zero', () => {
    render(<MemoryRouter><HomeDashboard dashboard={dashboard()} /></MemoryRouter>);

    expect(screen.queryByText('画像建议能力尚未建立：0')).not.toBeInTheDocument();
    expect(screen.getAllByText('有 1 项失败运行').length).toBeGreaterThan(0);
  });
});
