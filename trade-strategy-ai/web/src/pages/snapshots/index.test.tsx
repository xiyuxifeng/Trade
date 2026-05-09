import { describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen, waitFor } from '@testing-library/react';
import { fireEvent } from '@testing-library/react';
import { SnapshotsPage } from './index';
import { renderWithRouter } from '@/test/test-utils';
import { createJob } from '@/lib/api/jobs';
import { getSnapshot, listSnapshots } from '@/lib/api/snapshots';
import type { JobDetailResponse } from '@/types/jobs';

vi.mock('@/lib/api/jobs', () => ({
  createJob: vi.fn(),
}));

vi.mock('@/lib/api/snapshots', () => ({
  getSnapshot: vi.fn(),
  listSnapshots: vi.fn(),
}));

const mockedCreateJob = vi.mocked(createJob);
const mockedGetSnapshot = vi.mocked(getSnapshot);
const mockedListSnapshots = vi.mocked(listSnapshots);

describe('SnapshotsPage', () => {
  it('builds a snapshot job and shows snapshot details', async () => {
    const user = userEvent.setup();

    mockedListSnapshots.mockResolvedValue({
      count: 1,
      total: 1,
      skip: 0,
      limit: 50,
      items: [
        {
          snapshot_id: '2026-05-09_17-30',
          trade_date: '2026-05-09',
          slot: '17-30',
          type: 'hot_topics',
        },
      ],
    });
    mockedGetSnapshot.mockResolvedValue({
      item: {
        trade_date: '2026-05-09',
        slot: '17-30',
        fetched_at: '2026-05-09T09:30:00Z',
        hot_topics: {
          trade_date: '2026-05-09',
          slot: '17-30',
          topics: [
        {
          kind: 'concept',
          topic_id: 't-1',
          topic_name: 'AI',
          score: 98.5,
          increase_pct: 7.2,
          speed_pct: null,
          turnover: null,
          net_inflow: null,
        },
      ],
          sources: ['akshare'],
          fetched_at: '2026-05-09T09:31:00Z',
        },
        topic_constituents: {
          trade_date: '2026-05-09',
          slot: '17-30',
          constituents: [
            {
              kind: 'stock_sector_v2',
              topic_id: 't-1',
              topic_name: 'AI',
              symbol: '000001.SZ',
              name: '平安银行',
              topic_change_pct: null,
              leader_symbol: null,
              leader_name: null,
              leader_change_pct: null,
              board_num: null,
              net_buy: null,
              brief_intro: null,
            },
          ],
          sources: ['akshare'],
          fetched_at: '2026-05-09T09:32:00Z',
        },
        strong_symbols: {
          trade_date: '2026-05-09',
          slot: '17-30',
          symbols: [
            {
              kind: 'strong_fengkou',
              symbol: '000002.SZ',
              name: '万科A',
              strength_score: 87,
              change_pct: null,
              turnover: null,
              turnover_ratio: null,
              return_pct: null,
              net_inflow: null,
              main_force_buy: null,
              main_force_sell: null,
              rt_change_pct: null,
              bid_net: null,
              bid_turnover: null,
              topic_tags: null,
            },
          ],
          sources: ['akshare'],
          fetched_at: '2026-05-09T09:33:00Z',
        },
        metadata: { source: 'snapshot' },
      },
    });
    mockedCreateJob.mockResolvedValue({
      created: true,
      job: { id: 'job-1', job_type: 'snapshot-build' } as JobDetailResponse['job'],
      job_dir: '/tmp/job-1',
      log_path: '/tmp/job-1/job.log',
      params_path: '/tmp/job-1/params.json',
      result_path: '/tmp/job-1/result.json',
      artifacts_path: '/tmp/job-1/artifacts.json',
    });

    renderWithRouter([{ path: '/snapshots', element: <SnapshotsPage /> }], ['/snapshots']);

    await waitFor(() => {
      expect(mockedListSnapshots).toHaveBeenCalled();
    });

    expect(await screen.findByText('快照中心')).toBeInTheDocument();
    expect(await screen.findByText('2026-05-09')).toBeInTheDocument();

    const dateInputs = screen.getAllByLabelText(/date/i);
    fireEvent.change(dateInputs[0], { target: { value: '2026-05-09' } });
    fireEvent.change(dateInputs[1], { target: { value: '2026-05-09' } });

    await user.click(screen.getByRole('button', { name: '构建快照' }));

    expect(mockedCreateJob).toHaveBeenCalledWith({
      job_type: 'snapshot-build',
      params: {
        config_path: 'config/app.yaml',
        date: '2026-05-09',
        start_date: '2026-05-09',
        end_date: '2026-05-09',
        slot: '17-30',
        snapshot_type: 'all',
        force: false,
        offline: false,
      },
      created_by: 'web',
      max_retries: 3,
      retry_backoff_seconds: 0,
      timeout_seconds: null,
    });

    await user.click(screen.getAllByText('2026-05-09 17-30')[0]);
    expect(await screen.findByText('hot_topics')).toBeInTheDocument();
    expect(await screen.findByText('topic_constituents')).toBeInTheDocument();
    expect(await screen.findByText('strong_symbols')).toBeInTheDocument();
  });
});
