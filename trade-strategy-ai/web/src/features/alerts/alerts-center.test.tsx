import { beforeEach, describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { cleanup, screen, waitFor } from '@testing-library/react';
import { renderWithRouter } from '@/test/test-utils';
import { AlertsPage } from '@/pages/alerts';
import { acknowledgeAlert, getAlertingStatus, listAlertHistory, resolveAlert, sendTestAlert } from '@/lib/api/alerts';
import type { AlertHistoryItem } from '@/types/alerts';

vi.mock('@/lib/api/alerts', () => ({
  acknowledgeAlert: vi.fn(),
  getAlertHistory: vi.fn(),
  getAlertingStatus: vi.fn(),
  listAlertHistory: vi.fn(),
  resolveAlert: vi.fn(),
  sendTestAlert: vi.fn(),
}));

const mockedListAlertHistory = vi.mocked(listAlertHistory);
const mockedGetAlertingStatus = vi.mocked(getAlertingStatus);
const mockedAcknowledgeAlert = vi.mocked(acknowledgeAlert);
const mockedResolveAlert = vi.mocked(resolveAlert);
const mockedSendTestAlert = vi.mocked(sendTestAlert);

function makeAlert(overrides: Partial<AlertHistoryItem> = {}): AlertHistoryItem {
  return {
    id: 'alert-1',
    alert_id: 'alert-1',
    level: 'CRITICAL',
    title: 'Pipeline 失败：pipeline-run',
    message: 'Pipeline 执行失败：boom',
    channel: 'dingtalk',
    tags: ['pipeline', 'failed'],
    status: 'sent',
    aggregated_count: 1,
    aggregation_key: null,
    sent_at: '2026-05-09T08:05:00Z',
    acknowledged_at: null,
    resolved_at: null,
    alert_metadata: { rule_name: 'pipeline_failure', job_type: 'pipeline-run' },
    created_at: '2026-05-09T08:00:00Z',
    ...overrides,
  };
}

beforeEach(() => {
  vi.restoreAllMocks();
  cleanup();
  window.localStorage.clear();
});

describe('AlertsPage', () => {
  it('renders alert status summary and history', async () => {
    mockedGetAlertingStatus.mockResolvedValue({
      enabled: true,
      channel: 'dingtalk',
      min_level: 'WARNING',
      console_output: true,
      aggregation_window_minutes: 60,
      aggregation_max_count: 100,
      webhook_configured: true,
      channel_configured: true,
    });
    mockedListAlertHistory.mockResolvedValue({
      count: 1,
      total: 1,
      items: [makeAlert()],
    });

    renderWithRouter([{ path: '/alerts', element: <AlertsPage /> }], ['/alerts']);

    expect(await screen.findByRole('heading', { name: '告警中心' })).toBeInTheDocument();
    expect(await screen.findByText('Pipeline 失败：pipeline-run')).toBeInTheDocument();
    expect(screen.getByText('已就绪')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '发送测试告警' })).toBeEnabled();
  });

  it('can acknowledge, resolve and open detail dialog', async () => {
    const user = userEvent.setup();
    mockedGetAlertingStatus.mockResolvedValue({
      enabled: true,
      channel: 'dingtalk',
      min_level: 'WARNING',
      console_output: true,
      aggregation_window_minutes: 60,
      aggregation_max_count: 100,
      webhook_configured: true,
      channel_configured: true,
    });
    mockedListAlertHistory.mockResolvedValue({
      count: 1,
      total: 1,
      items: [makeAlert()],
    });
    mockedAcknowledgeAlert.mockResolvedValue({ status: 'ok', id: 'alert-1', new_status: 'acknowledged' });
    mockedResolveAlert.mockResolvedValue({ status: 'ok', id: 'alert-1', new_status: 'resolved' });
    mockedSendTestAlert.mockResolvedValue({ status: 'ok', message: '测试告警已发送' });

    renderWithRouter([{ path: '/alerts', element: <AlertsPage /> }], ['/alerts']);

    expect(await screen.findByRole('heading', { name: '告警中心' })).toBeInTheDocument();
    expect(await screen.findByText('Pipeline 失败：pipeline-run')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '确认' }));
    await user.click(screen.getByRole('button', { name: '解决' }));
    await user.click(screen.getByRole('button', { name: '详情' }));

    await waitFor(() => {
      expect(mockedAcknowledgeAlert).toHaveBeenCalledWith('alert-1', expect.any(String));
      expect(mockedResolveAlert).toHaveBeenCalledWith('alert-1', expect.any(String));
    });
    expect(await screen.findByText('告警详情')).toBeInTheDocument();
    expect(screen.getAllByText('Pipeline 失败：pipeline-run')).toHaveLength(2);
  });
});
