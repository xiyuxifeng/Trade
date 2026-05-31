import { beforeEach, describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen } from '@testing-library/react';
import { renderWithRouter } from '@/test/test-utils';
import { PersonaPage } from './persona-page';

vi.mock('@/lib/api/persona', () => ({
  buildSampleClusters: vi.fn(),
  listBehaviorRules: vi.fn(),
}));

import { buildSampleClusters, listBehaviorRules } from '@/lib/api/persona';

describe('persona page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows sample clusters and behavior rules in separate tabs', async () => {
    vi.mocked(listBehaviorRules).mockResolvedValueOnce({
      schema_version: 'v1',
      title: '交易行为标签规则',
      description: '用于将单笔交易归类为追涨、抄底、趋势、风控等行为标签的只读规则集。',
      source_path: 'config/rules/behavior_rules.yaml',
      rule_count: 1,
      enabled_rule_count: 1,
      category_count: 1,
      categories: [{ name: '追涨类', rule_count: 1, enabled_rule_count: 1 }],
      rules: [
        {
          id: 'chase_rally',
          label: 'chase_rally',
          category: '追涨类',
          priority: 120,
          enabled: true,
          description: '追涨（突破后追入）',
          signals: ['price_breakout', 'high_volume'],
          condition_summary: 'price_vs_ma > 1.02 且 volume_ratio > 1.5',
          conditions: [
            { field: 'price_vs_ma', op: 'gt', value: 1.02, expression: 'price_vs_ma > 1.02' },
            { field: 'volume_ratio', op: 'gt', value: 1.5, expression: 'volume_ratio > 1.5' },
          ],
        },
      ],
    });

    vi.mocked(buildSampleClusters).mockResolvedValueOnce({
      base_dir: '/tmp/project',
      clusters_path: '/tmp/project/data/processed/persona/clusters.sample.json',
      trader_count: 3,
      clusters_count: 6,
    });

    const user = userEvent.setup();
    renderWithRouter([{ path: '/persona', element: <PersonaPage /> }], ['/persona']);

    expect(await screen.findByRole('heading', { name: '交易风格画像与行为规则' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '样例聚类' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '行为规则（只读）' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '生成样例聚类文件' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '行为规则（只读）' }));

    expect(await screen.findByText('交易行为标签规则')).toBeInTheDocument();
    expect(screen.getByText('追涨类（1 条）')).toBeInTheDocument();
    expect(screen.getByText('chase_rally')).toBeInTheDocument();
    expect(screen.getByText('只读预览')).toBeInTheDocument();
  });
});
