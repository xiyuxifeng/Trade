import { afterEach, describe, expect, it, vi } from 'vitest';
import { getRulePoolRule, listRulePool, reviewRulePoolBatch, reviewRulePoolRule } from './rule-pool';

describe('rule pool api client', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it('calls canonical rule-pool endpoints and forwards the API key', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ status: 'success', count: 0, total: 0, skip: 0, limit: 10, items: [] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ status: 'success', item: { rule_id: 'rule-1' } }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ status: 'ok', rule_id: 'rule-1' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ status: 'ok', updated_count: 1 }),
      });

    vi.stubGlobal('fetch', fetchMock);
    window.localStorage.setItem('trade-strategy-ai.apiKey', 'demo-key');

    await listRulePool({ status: 'pending', skip: 0, limit: 10 });
    await getRulePoolRule('rule-1');
    await reviewRulePoolRule('rule-1', { decision: 'approve', force: true, reviewed_by: 'web' });
    await reviewRulePoolBatch({ decision: 'reject', status: 'pending', limit: 25, force: true, reviewed_by: 'web' });

    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/ui/v1/rule-pool?status=pending&skip=0&limit=10', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/ui/v1/rule-pool/rule-1', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(3, '/api/ui/v1/rule-pool/rule-1/review', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(4, '/api/ui/v1/rule-pool/review-batch', expect.any(Object));
  });
});

