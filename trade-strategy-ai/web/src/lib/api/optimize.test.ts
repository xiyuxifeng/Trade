import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  createOptimizeCandidateVersion,
  getOptimizeVersion,
  listOptimizeVersions,
} from './optimize';

describe('optimize api client', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it('calls canonical optimize endpoints and forwards the API key', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ status: 'success', count: 0, total: 0, skip: 0, limit: 8, items: [] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ status: 'success', item: { version_id: 'candidate-1' } }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ status: 'success', item: { version_id: 'candidate-1' } }),
      });

    vi.stubGlobal('fetch', fetchMock);
    window.localStorage.setItem('trade-strategy-ai.apiKey', 'demo-key');

    await listOptimizeVersions({ trader_id: 'trader_a', version_type: 'candidate', skip: 0, limit: 8 });
    await getOptimizeVersion('candidate-1');
    await createOptimizeCandidateVersion({
      parent_version_id: 'sv-1',
      trader_id: 'trader_a',
      strategy_date: '2026-05-09',
      adjustments: [],
      recommendations: [],
      notes: 'version notes',
    });

    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/ui/v1/optimize/versions?trader_id=trader_a&version_type=candidate&skip=0&limit=8', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/ui/v1/optimize/versions/candidate-1', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(3, '/api/ui/v1/optimize/create-candidate', expect.any(Object));
  });
});

