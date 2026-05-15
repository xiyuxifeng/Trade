import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  API_KEY_STORAGE_KEY,
  ApiError,
  buildApiHeaders,
  fetchBlob,
  fetchJson,
  fetchRootJson,
  fetchRootText,
  fetchText,
} from './http';

describe('http api client', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal('fetch', vi.fn());
    window.localStorage.clear();
  });

  it('injects the stored api key into shared headers', () => {
    window.localStorage.setItem(API_KEY_STORAGE_KEY, 'demo-key');

    const headers = buildApiHeaders({ Accept: 'application/json' });
    expect(headers.get('X-API-Key')).toBe('demo-key');
    expect(headers.get('Accept')).toBe('application/json');
  });

  it('sends the stored api key with fetchJson requests', async () => {
    window.localStorage.setItem(API_KEY_STORAGE_KEY, 'demo-key');
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: 'ok' }),
    } as Response);

    await fetchJson('/system/status');

    const [url, init] = vi.mocked(fetch).mock.calls[0] ?? [];
    expect(url).toBe('/api/ui/v1/system/status');
    expect((init?.headers as Headers).get('Accept')).toBe('application/json');
    expect((init?.headers as Headers).get('X-API-Key')).toBe('demo-key');
  });

  it('supports root api json and text requests through the same client', async () => {
    window.localStorage.setItem(API_KEY_STORAGE_KEY, 'demo-key');
    vi.mocked(fetch)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ count: 0 }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () => '# Report',
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        blob: async () => new Blob(['artifact']),
      } as Response);

    await fetchRootJson('/reports/daily?skip=0');
    await fetchRootText('/reports/daily/2026-05-09/html');
    await fetchBlob('/artifacts/artifact-1/download');

    const [jsonUrl, jsonInit] = vi.mocked(fetch).mock.calls[0] ?? [];
    expect(jsonUrl).toBe('/reports/daily?skip=0');
    expect((jsonInit?.headers as Headers).get('Accept')).toBe('application/json');
    expect((jsonInit?.headers as Headers).get('X-API-Key')).toBe('demo-key');

    const [textUrl, textInit] = vi.mocked(fetch).mock.calls[1] ?? [];
    expect(textUrl).toBe('/reports/daily/2026-05-09/html');
    expect((textInit?.headers as Headers).get('Accept')).toContain('text/');

    const [blobUrl, blobInit] = vi.mocked(fetch).mock.calls[2] ?? [];
    expect(blobUrl).toBe('/api/ui/v1/artifacts/artifact-1/download');
    expect((blobInit?.headers as Headers).get('Accept')).toBe('*/*');
  });

  it('maps api errors into a unified error shape', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      status: 403,
      statusText: 'Forbidden',
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        message: 'forbidden',
        detail: { reason: 'role_missing' },
        request_id: 'req-123',
      }),
    } as Response);

    await expect(fetchJson('/system/status')).rejects.toMatchObject({
      name: 'ApiError',
      status: 403,
      message: 'forbidden',
      detail: { reason: 'role_missing' },
      requestId: 'req-123',
    });
  });

  it('falls back to status text for non-json errors', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      headers: new Headers({ 'content-type': 'text/plain' }),
      text: async () => 'boom',
    } as Response);

    await expect(fetchText('/reports/daily/2026-05-09/html')).rejects.toMatchObject({
      name: 'ApiError',
      status: 500,
      message: 'Internal Server Error',
    });
  });
});
