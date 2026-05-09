import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  acknowledgeAlert,
  listAlertHistory,
  resolveAlert,
  sendTestAlert,
} from '@/lib/api/alerts';
import { API_KEY_STORAGE_KEY } from '@/lib/api/http';

describe('alerts api client', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal('fetch', vi.fn());
    window.localStorage.clear();
  });

  it('calls the root alerts endpoint and forwards the stored API key', async () => {
    window.localStorage.setItem(API_KEY_STORAGE_KEY, 'demo-key');
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ count: 0, total: 0, items: [] }),
    } as Response);

    await listAlertHistory({ status: 'pending', tag: 'snapshot', skip: 10, limit: 20 });

    const [url, init] = vi.mocked(fetch).mock.calls[0] ?? [];
    expect(url).toBe('/alerts/history?status=pending&tag=snapshot&skip=10&limit=20');
    expect((init?.headers as Headers).get('Accept')).toBe('application/json');
    expect((init?.headers as Headers).get('X-API-Key')).toBe('demo-key');
  });

  it('posts acknowledge, resolve and test alert requests', async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'ok', id: 'record-1', new_status: 'acknowledged' }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'ok', id: 'record-1', new_status: 'resolved' }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'ok', message: '测试告警已发送' }),
      } as Response);

    await acknowledgeAlert('record-1', 'tester');
    await resolveAlert('record-1', 'tester');
    await sendTestAlert();

    expect(fetch).toHaveBeenNthCalledWith(
      1,
      '/alerts/record-1/acknowledge',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ acknowledged_by: 'tester' }),
      }),
    );
    expect(fetch).toHaveBeenNthCalledWith(
      2,
      '/alerts/record-1/resolve',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ resolved_by: 'tester' }),
      }),
    );
    expect(fetch).toHaveBeenNthCalledWith(
      3,
      '/alerts/test',
      expect.objectContaining({
        method: 'POST',
      }),
    );
  });
});
