import { afterEach, describe, expect, it, vi } from 'vitest';
import { listTraderOptions } from './traders';

describe('traders api client', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it('calls the trader options endpoint with the requested source', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        status: 'success',
        count: 2,
        items: ['trader_a', 'trader_b'],
      }),
    });
    vi.stubGlobal('fetch', fetchMock);

    await listTraderOptions({ source: 'strategy' });

    expect(fetchMock).toHaveBeenCalledWith('/api/ui/v1/traders?source=strategy', expect.any(Object));
  });
});
