import { beforeEach, describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen, waitFor } from '@testing-library/react';
import { AlertDetailPage } from './AlertDetailPage';
import { renderWithRouter } from '@/test/test-utils';
import { acknowledgeAlert, getAlertHistory, resolveAlert } from '@/lib/api/alerts';

vi.mock('@/lib/api/alerts', () => ({
  acknowledgeAlert: vi.fn(),
  getAlertHistory: vi.fn(),
  resolveAlert: vi.fn(),
}));

const mockedGetAlertHistory = vi.mocked(getAlertHistory);
const mockedAcknowledgeAlert = vi.mocked(acknowledgeAlert);
const mockedResolveAlert = vi.mocked(resolveAlert);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('AlertDetailPage', () => {
  it('renders an alert detail page with acknowledge and resolve actions', async () => {
    const user = userEvent.setup();

    mockedGetAlertHistory.mockResolvedValue({
      id: 'alert-record-1',
      alert_id: 'alert-1',
      level: 'CRITICAL',
      title: '数据库离线',
      message: '主数据库连接失败。',
      channel: 'dingtalk',
      tags: ['database', 'critical'],
      status: 'pending',
      aggregated_count: 3,
      aggregation_key: 'database:connection',
      sent_at: '2026-05-16T09:01:00Z',
      acknowledged_at: null,
      resolved_at: null,
      alert_metadata: { source: 'health-check' },
      created_at: '2026-05-16T09:02:00Z',
    });
    mockedAcknowledgeAlert.mockResolvedValue({ status: 'ok', id: 'alert-record-1', new_status: 'acknowledged' });
    mockedResolveAlert.mockResolvedValue({ status: 'ok', id: 'alert-record-1', new_status: 'resolved' });

    renderWithRouter([{ path: '/alerts/:recordId', element: <AlertDetailPage /> }], ['/alerts/alert-record-1']);

    expect(await screen.findByText('告警详情')).toBeInTheDocument();
    expect(screen.getByText((content) => content.includes('alert-record-1'))).toBeInTheDocument();
    expect(screen.getByText('数据库离线')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '确认告警' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '解决告警' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '返回告警中心' })).toHaveAttribute('href', '/alerts');

    await user.click(screen.getByRole('button', { name: '确认告警' }));
    await waitFor(() => {
      expect(mockedAcknowledgeAlert).toHaveBeenCalledWith('alert-record-1', 'web');
    });

    await user.click(screen.getByRole('button', { name: '解决告警' }));
    await waitFor(() => {
      expect(mockedResolveAlert).toHaveBeenCalledWith('alert-record-1', 'web');
    });
  });
});
