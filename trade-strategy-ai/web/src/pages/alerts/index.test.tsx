import dayjs from 'dayjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen, waitFor } from '@testing-library/react';
import { AlertsPage } from './index';
import { renderWithRouter } from '@/test/test-utils';
import { acknowledgeAlert, getAlertHistory, listAlertHistory, resolveAlert, sendTestAlert } from '@/lib/api/alerts';

vi.mock('@/lib/api/alerts', () => ({
  acknowledgeAlert: vi.fn(),
  getAlertHistory: vi.fn(),
  listAlertHistory: vi.fn(),
  resolveAlert: vi.fn(),
  sendTestAlert: vi.fn(),
}));

const mockedAcknowledgeAlert = vi.mocked(acknowledgeAlert);
const mockedGetAlertHistory = vi.mocked(getAlertHistory);
const mockedListAlertHistory = vi.mocked(listAlertHistory);
const mockedResolveAlert = vi.mocked(resolveAlert);
const mockedSendTestAlert = vi.mocked(sendTestAlert);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('AlertsPage', () => {
  it('loads alert history and supports acknowledge, resolve, and test alert actions', async () => {
    const user = userEvent.setup();

    mockedListAlertHistory.mockResolvedValue({
      count: 1,
      total: 1,
      items: [
        {
          id: 'record-1',
          alert_id: 'alert-1',
          level: 'CRITICAL',
          title: 'Database offline',
          message: 'Primary database connection failed.',
          channel: 'dingtalk',
          tags: ['database', 'critical'],
          status: 'pending',
          aggregated_count: 3,
          aggregation_key: 'database:connection',
          sent_at: '2026-05-09T09:30:00Z',
          acknowledged_at: null,
          resolved_at: null,
          alert_metadata: { source: 'health-check' },
          created_at: '2026-05-09T09:32:00Z',
        },
      ],
    });
    mockedGetAlertHistory.mockResolvedValue({
      id: 'record-1',
      alert_id: 'alert-1',
      level: 'CRITICAL',
      title: 'Database offline',
      message: 'Primary database connection failed.',
      channel: 'dingtalk',
      tags: ['database', 'critical'],
      status: 'pending',
      aggregated_count: 3,
      aggregation_key: 'database:connection',
      sent_at: '2026-05-09T09:30:00Z',
      acknowledged_at: null,
      resolved_at: null,
      alert_metadata: { source: 'health-check' },
      created_at: '2026-05-09T09:32:00Z',
    });
    mockedAcknowledgeAlert.mockResolvedValue({ status: 'ok', id: 'record-1', new_status: 'acknowledged' });
    mockedResolveAlert.mockResolvedValue({ status: 'ok', id: 'record-1', new_status: 'resolved' });
    mockedSendTestAlert.mockResolvedValue({ status: 'ok', message: '测试告警已发送' });

    renderWithRouter([{ path: '/alerts', element: <AlertsPage /> }], ['/alerts']);

    await waitFor(() => {
      expect(mockedListAlertHistory).toHaveBeenCalled();
    });

    expect(await screen.findByText('告警中心')).toBeInTheDocument();
    expect(await screen.findByText('Database offline')).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: '摘要' })).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: '原始数据' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '查看详情' })).toHaveAttribute('href', '/alerts/record-1');

    await waitFor(() => {
      expect(mockedGetAlertHistory).toHaveBeenCalledWith('record-1');
    });

    await user.click(screen.getByRole('button', { name: '确认 (Acknowledge)' }));
    await waitFor(() => {
      expect(mockedAcknowledgeAlert).toHaveBeenCalledWith('record-1', 'web');
    });

    await user.click(screen.getByRole('button', { name: '解决 (Resolve)' }));
    await waitFor(() => {
      expect(mockedResolveAlert).toHaveBeenCalledWith('record-1', 'web');
    });

    await user.click(screen.getByRole('button', { name: '发送测试告警' }));
    expect(await screen.findByText('发送测试告警？')).toBeInTheDocument();
    await user.click(screen.getAllByRole('button', { name: '发送测试告警' })[1]);

    await waitFor(() => {
      expect(mockedSendTestAlert).toHaveBeenCalled();
    });
  });

  it('shows the empty state and resets filters', async () => {
    const user = userEvent.setup();
    const today = dayjs().format('YYYY-MM-DD');
    const thirtyDaysAgo = dayjs().subtract(30, 'day').format('YYYY-MM-DD');

    mockedListAlertHistory.mockResolvedValue({
      count: 0,
      total: 0,
      items: [],
    });

    renderWithRouter([{ path: '/alerts', element: <AlertsPage /> }], ['/alerts']);

    await waitFor(() => {
      expect(mockedListAlertHistory).toHaveBeenCalled();
    });

    expect(await screen.findByText('当前筛选范围内暂无告警历史。')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: '重置过滤器' })).toHaveLength(2);

    await user.type(screen.getByLabelText('标签'), 'snapshot');
    await user.click(screen.getAllByRole('button', { name: '重置过滤器' })[1]);

    expect(screen.getByLabelText('状态')).toHaveValue('');
    expect(screen.getByLabelText('级别')).toHaveValue('');
    expect(screen.getByLabelText('标签')).toHaveValue('');
    expect(screen.getByLabelText('开始日期')).toHaveValue(thirtyDaysAgo);
    expect(screen.getByLabelText('结束日期')).toHaveValue(today);
  });
});
