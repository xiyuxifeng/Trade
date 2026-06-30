import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  buildBacktestReproducibilityParams,
  buildBacktestRunParams,
  buildBacktestValidateRulesParams,
  downloadBacktestReport,
  downloadBacktestValidationReport,
  checkFormalBacktestDependencies,
  createRulePoolBacktestBatchRun,
  createFormalBacktestRun,
  executeFormalBacktestRun,
  generateFormalApplicabilityProfileDraft,
  getBacktestResult,
  getFormalBacktestResult,
  getFormalBacktestRun,
  mergeRulePoolBacktestBatchRun,
  listBacktestResults,
  reviewFormalApplicabilityProfile,
  startRulePoolBacktestBatch,
} from './backtests';

describe('backtests api client', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it('calls the root backtest_results endpoint and sends the stored API key', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        status: 'success',
        count: 0,
        total: 0,
        skip: 0,
        limit: 10,
        items: [],
      }),
    });
    vi.stubGlobal('fetch', fetchMock);
    window.localStorage.setItem('trade-strategy-ai.apiKey', 'demo-key');

    await listBacktestResults({ skip: 0, limit: 10 });

    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe('/backtest_results/?skip=0&limit=10');
    expect((init?.headers as Headers).get('Accept')).toBe('application/json');
    expect((init?.headers as Headers).get('X-API-Key')).toBe('demo-key');
  });

  it('loads a backtest result and markdown reports from the root API', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          status: 'success',
        item: {
          request_trader_id: 'trader_a',
          request_date_from: '2026-05-01',
          request_date_to: '2026-05-05',
          benchmark_symbol: '000300.SH',
          result_version: '1.0',
          summary: {
            total_days: 5,
              total_trades: 3,
              valid_trades: 2,
              skipped_trades: 1,
              win_rate: 0.67,
              avg_return_pct: 0.12,
            },
            records: [],
          },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        text: async () => '# Backtest Report',
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        text: async () => '# Rule Validation Report',
      });
    vi.stubGlobal('fetch', fetchMock);

    await getBacktestResult('result-1');
    await downloadBacktestReport('result-1');
    await downloadBacktestValidationReport('result-1');

    expect(fetchMock).toHaveBeenNthCalledWith(1, '/backtest_results/result-1', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/backtest_results/result-1/report', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(3, '/backtest_results/result-1/validate_rules', expect.any(Object));
  });

  it('builds canonical backtest job params for all backtest job types', () => {
    const submission = {
      profileId: 'default',
      traderId: 'trader_a',
      dateFrom: '2026-05-01',
      dateTo: '2026-05-05',
      strategyVersionId: 'sv-1',
      benchmarkSymbol: '000300.SH',
      mode: 'full' as const,
      symbols: ['000001.SZ'],
      useSnapshotOnly: true,
      scoringProfile: 'stage5',
    };

    expect(buildBacktestRunParams(submission)).toEqual({
      profile_id: 'default',
      trader_id: 'trader_a',
      date_from: '2026-05-01',
      date_to: '2026-05-05',
      strategy_version_id: 'sv-1',
      benchmark_symbol: '000300.SH',
      mode: 'full',
      symbols: ['000001.SZ'],
      use_snapshot_only: true,
      scoring_profile: 'stage5',
    });
    expect(buildBacktestValidateRulesParams(submission)).toEqual({
      profile_id: 'default',
      trader_id: 'trader_a',
      date_from: '2026-05-01',
      date_to: '2026-05-05',
      strategy_version_id: 'sv-1',
      benchmark_symbol: '000300.SH',
      mode: 'full',
      symbols: ['000001.SZ'],
      use_snapshot_only: true,
      scoring_profile: 'stage5',
    });
    expect(buildBacktestReproducibilityParams(submission)).toEqual({
      profile_id: 'default',
      trader_id: 'trader_a',
      date_from: '2026-05-01',
      date_to: '2026-05-05',
      strategy_version_id: 'sv-1',
      benchmark_symbol: '000300.SH',
      mode: 'full',
      symbols: ['000001.SZ'],
      use_snapshot_only: true,
      scoring_profile: 'stage5',
    });
  });

  it('uses the formal rules backtest API instead of raw job submission', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          business_state: '可运行',
          canonical_state: 'runnable',
          can_create_run: true,
          requested_level: 'level_1',
          effective_level: 'level_1',
          coverage: {},
          unavailable_reasons: [],
          limitations: [],
          next_actions: [],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => ({
          run_id: 'run-1',
          status: 'dependency_checked',
          snapshot_only: true,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          run_id: 'run-1',
          status: 'dependency_checked',
          snapshot_only: true,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          result_id: 'result-1',
          run_id: 'run-1',
          status: 'completed_valid',
          market_state_model_version: 'market-state-v1',
          market_state_source_version: 'features-v1',
          per_market_state_metrics: [],
          sample_state_counts: {},
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          result_id: 'result-1',
          run_id: 'run-1',
          status: 'completed_valid',
          market_state_model_version: 'market-state-v1',
          market_state_source_version: 'features-v1',
          per_market_state_metrics: [],
          sample_state_counts: {},
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => ({
          profile_id: 'profile-1',
          review_status: 'draft',
          recommendation_status: 'recommended',
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          profile_id: 'profile-1',
          review_status: 'approved',
          recommendation_status: 'recommended',
        }),
      });
    vi.stubGlobal('fetch', fetchMock);

    const selection = {
      rule_version_id: '00000000-0000-0000-0000-000000000001',
      date_from: '2026-04-01',
      date_to: '2026-04-10',
      universe: { symbols: ['000001.SZ'] },
      benchmark_symbol: '000300.SH',
      mode: 'full' as const,
      requested_level: 'level_1' as const,
      profile_id: 'context-only',
    };

    await checkFormalBacktestDependencies(selection);
    await createFormalBacktestRun({ selection, reason: '验证规则' });
    await getFormalBacktestRun('run-1');
    await executeFormalBacktestRun('run-1');
    await getFormalBacktestResult('run-1');
    await generateFormalApplicabilityProfileDraft('run-1', { result_id: 'result-1', reason: '生成草稿' });
    await reviewFormalApplicabilityProfile('profile-1', { review_status: 'approved', reason: '证据充分' });

    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/ui/v1/rules/backtests/dependency-check', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/ui/v1/rules/backtests/runs', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(3, '/api/ui/v1/rules/backtests/runs/run-1', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(4, '/api/ui/v1/rules/backtests/runs/run-1/execute', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(5, '/api/ui/v1/rules/backtests/runs/run-1/result', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(6, '/api/ui/v1/rules/backtests/runs/run-1/applicability-profiles', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(7, '/api/ui/v1/rules/backtests/applicability-profiles/profile-1/review', expect.any(Object));
    const urls = fetchMock.mock.calls.map(([url]) => String(url));
    expect(urls.some((url) => url.includes('/api/ui/v1/jobs'))).toBe(false);
    expect(urls.some((url) => url.includes('/backtest_results'))).toBe(false);
    expect(urls.some((url) => url.includes('/rule-pool'))).toBe(false);
  });

  it('supports rule pool batch runs and rule_ids params', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => ({ batch_run_id: 'batch-run-1', selected_rule_count: 2, batches: [] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ batch_run_id: 'batch-run-1', batches: [{ batch_index: 1, job_id: 'job-1' }] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ batch_run_id: 'batch-run-1', status: 'merged', merged_result_id: 'merged-batch-run-1' }),
      });
    vi.stubGlobal('fetch', fetchMock);

    await createRulePoolBacktestBatchRun({
      ruleIds: ['rule-1', 'rule-2'],
      batchSize: 30,
      startDate: '2026-01-01',
      endDate: '2026-06-30',
      minConfidence: 0.7,
      marketRegimeVersion: 'market-regime-v3',
      profileId: 'default',
    });
    await startRulePoolBacktestBatch('batch-run-1', 1);
    await mergeRulePoolBacktestBatchRun('batch-run-1');

    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/ui/v1/rules/backtests/batch-runs', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({
        rule_ids: ['rule-1', 'rule-2'],
        batch_size: 30,
        start_date: '2026-01-01',
        end_date: '2026-06-30',
        min_confidence: 0.7,
        market_regime_version: 'market-regime-v3',
        profile_id: 'default',
      }),
    }));
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/ui/v1/rules/backtests/batch-runs/batch-run-1/batches/1/start', expect.objectContaining({ method: 'POST' }));
    expect(fetchMock).toHaveBeenNthCalledWith(3, '/api/ui/v1/rules/backtests/batch-runs/batch-run-1/merge', expect.objectContaining({ method: 'POST' }));
  });
});
