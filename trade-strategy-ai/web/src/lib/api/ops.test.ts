import { beforeEach, describe, expect, it, vi } from 'vitest';
import { API_KEY_STORAGE_KEY } from './http';
import { listRecoveryBackups, createRecoveryBackup, restoreRecoveryBackup, recoverStaleJobs } from './ops';

describe('Ops API client contract', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal('fetch', vi.fn());
    const storage = new Map<string, string>();
    const localStorage = {
      clear: () => storage.clear(),
      getItem: (key: string) => storage.get(key) ?? null,
      removeItem: (key: string) => storage.delete(key),
      setItem: (key: string, value: string) => {
        storage.set(key, value);
      },
    };
    vi.stubGlobal('window', { localStorage } as never);
    localStorage.setItem(API_KEY_STORAGE_KEY, 'demo-key');
  });

  it('keeps the recovery endpoints and payloads stable', async () => {
    vi.mocked(fetch).mockImplementation(async () =>
      new Response('{}', {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    );

    await listRecoveryBackups();
    await createRecoveryBackup({ include_processed: true });
    await restoreRecoveryBackup({
      backup_path: '/project/data/backups/20260511-080000',
      include_processed: true,
      confirmed: true,
    });
    await recoverStaleJobs({ stale_before_minutes: 12 });

    const calls = vi.mocked(fetch).mock.calls.map(([url, init]) => ({
      url: String(url),
      method: init?.method ?? 'GET',
      headers: init?.headers instanceof Headers ? init.headers : new Headers(init?.headers),
      body: init?.body,
    }));

    const findCall = (url: string, method = 'GET') =>
      calls.find((call) => call.url === url && call.method === method);

    const expectJsonBody = (url: string, method: string, expected: Record<string, unknown>) => {
      const call = findCall(url, method);
      expect(call).toBeTruthy();
      expect(call?.headers.get('Content-Type')).toBe('application/json');
      expect(JSON.parse(String(call?.body))).toEqual(expected);
    };

    expect(findCall('/api/ui/v1/ops/backups')).toBeTruthy();
    expectJsonBody('/api/ui/v1/ops/backup', 'POST', { include_processed: true });
    expectJsonBody('/api/ui/v1/ops/restore', 'POST', {
      backup_path: '/project/data/backups/20260511-080000',
      include_processed: true,
      confirmed: true,
    });
    expectJsonBody('/api/ui/v1/ops/recover-stale', 'POST', { stale_before_minutes: 12 });

    for (const call of calls) {
      expect(call.headers.get('X-API-Key')).toBe('demo-key');
    }
  });
});
