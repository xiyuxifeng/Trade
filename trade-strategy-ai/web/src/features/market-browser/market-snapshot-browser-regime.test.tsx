import { render, screen } from '@testing-library/react';
import { describe, it } from 'vitest';

import { MarketRegimePanel } from './market-regime-panel';

describe('MarketRegimePanel', () => {
  it('shows primary label, confidence, labels and evidence', () => {
    render(
      <MarketRegimePanel
        regime={{
          regime: {
            regime_id: 'snap-001:market-regime-v1',
            snapshot_id: 'snap-001',
            trade_date: '2026-05-16',
            market: 'CN',
            regime_version: 'market-regime-v1',
            source_feature_version: 'market-regime-features-v1',
            primary_label: 'strong_bull',
            labels: [
              {
                label: 'strong_bull',
                label_type: 'primary',
                score: 5.6,
                confidence: 0.86,
                status: 'active',
                evidence: [
                  {
                    feature_key: 'trend',
                    feature_value: { ret_20d: 0.11 },
                    source_section: 'overview',
                    source_field: 'trend',
                    contribution: 2.0,
                    note: '趋势分数',
                  },
                ],
                reason: 'combined_score=5.60',
              },
            ],
            confidence: 0.86,
            quality_status: 'ok',
            missing_reason: null,
            storage_ref: { snapshot_id: 'snap-001', regime_version: 'market-regime-v1' },
            created_at: '2026-05-16T08:09:00Z',
            updated_at: '2026-05-16T08:09:00Z',
          },
          features: [
            {
              feature_key: 'trend',
              raw_value: { ret_20d: 0.11 },
              normalized_value: 0.8,
              source_section: 'overview',
              source_field: 'trend',
              source_version: 'market-regime-features-v1',
              confidence: 0.9,
              weight: 0.3,
              missing_reason: null,
            },
          ],
          warnings: [],
        }}
        isLoading={false}
        errorState={null}
      />,
    );

    expect(screen.getByText('Market Regime')).toBeInTheDocument();
    expect(screen.getByText('Primary Label')).toBeInTheDocument();
    expect(screen.getByText('strong_bull', { selector: 'p.text-base.font-semibold.text-slate-950' })).toBeInTheDocument();
    expect(screen.getByText('0.86')).toBeInTheDocument();
    expect(screen.getByText('trend')).toBeInTheDocument();
  });
});
