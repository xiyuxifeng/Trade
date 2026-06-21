import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';

import { renderWithRouter } from '@/test/test-utils';
import { ApiError } from '@/lib/api/http';
import { getPreMarketReadiness } from '@/lib/api/daily';
import { TodayPreMarketPage } from './index';

vi.mock('@/lib/api/daily', () => ({
  getPreMarketReadiness: vi.fn(),
}));

const mockedGetPreMarketReadiness = vi.mocked(getPreMarketReadiness);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('TodayPreMarketPage', () => {
  it('shows degraded readiness in business Chinese without legacy job language', async () => {
    mockedGetPreMarketReadiness.mockResolvedValue({
      state: 'partial',
      readiness_status: 'degraded',
      trade_date: '2026-06-21',
      slot: '09-25',
      summary_title: '可降级继续',
      happened: '正式规则适用性覆盖不完整。',
      affected: '今日规则选择会缺少一部分正式适用性证据。',
      repair_guidance: '先补齐规则适用性画像，或在降级模式下继续。',
      can_proceed: true,
      can_proceed_in_degraded_mode: true,
      checks: [
        {
          code: 'rule_applicability',
          label: '规则适用性',
          status: 'degraded',
          happened: '正式规则适用性覆盖不完整。',
          affected: '今日规则选择会缺少一部分正式适用性证据。',
          repair_guidance: '先补齐规则适用性画像，或在降级模式下继续。',
          can_proceed_in_degraded_mode: true,
          traceability: {
            applicability_profile_ids: [],
            missing_rule_version_ids: ['rule-version-1'],
          },
        },
      ],
      traceability: {
        trade_date: '2026-06-21',
        strategy_version_id: 'strategy-version-1',
        dataset_snapshot_id: 'dataset-snapshot-1',
        market_snapshot_id: 'market-snapshot-1',
        market_state_id: 'market-state-1',
        rule_applicability_profile_ids: [],
        author_validated_profile_version_id: 'author-validated-1',
        data_quality_state: 'degraded',
      },
      repair_actions: [{ label: '补齐缺失数据', to: '/system/data' }],
      warnings: [],
    } as never);

    renderWithRouter([{ path: '/daily/pre-market', element: <TodayPreMarketPage /> }], ['/daily/pre-market']);

    expect(await screen.findByRole('heading', { name: '今日盘前' })).toBeInTheDocument();
    expect(await screen.findAllByText('可降级继续')).not.toHaveLength(0);
    expect(await screen.findAllByText('正式规则适用性覆盖不完整。')).not.toHaveLength(0);
    expect(await screen.findAllByText('今日规则选择会缺少一部分正式适用性证据。')).not.toHaveLength(0);
    expect(await screen.findByRole('link', { name: '补齐缺失数据' })).toHaveAttribute('href', '/system/data');
    expect(screen.queryByText('run-pre-market')).not.toBeInTheDocument();
    expect(screen.queryByText('snapshot-build')).not.toBeInTheDocument();
    expect(screen.queryByText('config_path')).not.toBeInTheDocument();
    expect(screen.queryByText('Job')).not.toBeInTheDocument();
    expect(screen.queryByText('Workflow')).not.toBeInTheDocument();
    expect(screen.queryByText('Pipeline')).not.toBeInTheDocument();
    expect(screen.queryByText('Artifact')).not.toBeInTheDocument();
  });

  it('shows permission denied truthfully', async () => {
    mockedGetPreMarketReadiness.mockRejectedValue(
      new ApiError(403, 'forbidden'),
    );

    renderWithRouter([{ path: '/daily/pre-market', element: <TodayPreMarketPage /> }], ['/daily/pre-market']);

    expect(await screen.findByRole('heading', { name: '今日盘前' })).toBeInTheDocument();
    expect(await screen.findAllByText('无权限')).not.toHaveLength(0);
  });

  it('shows blocked readiness when canonical market coverage is missing', async () => {
    mockedGetPreMarketReadiness.mockResolvedValue({
      state: 'unavailable',
      readiness_status: 'blocked',
      trade_date: '2026-06-21',
      slot: '09-25',
      summary_title: '已阻塞',
      happened: '今日盘前市场快照缺失。',
      affected: '系统无法确认当前市场状态，也不能继续正式盘前流程。',
      repair_guidance: '先到数据管理补齐今日盘前市场数据。',
      can_proceed: false,
      can_proceed_in_degraded_mode: false,
      checks: [
        {
          code: 'kaipan_pre_market',
          label: 'Kaipan 盘前数据',
          status: 'blocked',
          happened: '今日盘前市场快照缺失。',
          affected: '无法确认当前市场状态。',
          repair_guidance: '先补齐今日盘前市场数据。',
          can_proceed_in_degraded_mode: false,
          traceability: {
            market_snapshot_id: null,
          },
        },
      ],
      traceability: {
        trade_date: '2026-06-21',
        strategy_version_id: 'strategy-version-1',
        dataset_snapshot_id: 'dataset-snapshot-1',
        market_snapshot_id: null,
        market_state_id: null,
        rule_applicability_profile_ids: [],
        author_validated_profile_version_id: 'author-validated-1',
        data_quality_state: 'blocked',
      },
      repair_actions: [{ label: '前往数据管理', to: '/system/data' }],
      warnings: [],
    } as never);

    renderWithRouter([{ path: '/daily/pre-market', element: <TodayPreMarketPage /> }], ['/daily/pre-market']);

    expect(await screen.findAllByText('已阻塞')).not.toHaveLength(0);
    expect(await screen.findAllByText('系统无法确认当前市场状态，也不能继续正式盘前流程。')).not.toHaveLength(0);
    expect(await screen.findByRole('link', { name: '前往数据管理' })).toHaveAttribute('href', '/system/data');
    expect(await screen.findAllByText('当前不能继续后续流程。')).not.toHaveLength(0);
  });
});
