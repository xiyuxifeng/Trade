import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { JobProgress } from './JobProgress';

describe('JobProgress', () => {
  it('renders structured progress details', () => {
    render(
      <JobProgress
        progress={{
          job_type: 'kaipan-fetch',
          stage: 'normalize',
          current: 2,
          total: 4,
          percent: 50,
          remaining: 2,
          sub_current: 3,
          sub_total: 6,
          sub_percent: 50,
          sub_remaining: 3,
          current_trade_date: '2026-05-25',
          current_slot: '17-30',
          current_fetcher: null,
          current_dataset: 'hot_topics',
          current_step: 'normalize:hot_topics',
          status: 'partial',
          error: null,
          updated_at: '2026-05-25T08:05:00Z',
        }}
      />,
    );

    expect(screen.getByText('normalize:hot_topics')).toBeInTheDocument();
    expect(screen.getByText('2 / 4 · 50%')).toBeInTheDocument();
    expect(screen.getByText(/剩余 2/)).toBeInTheDocument();
    expect(screen.getByText('子进度 3 / 6 · 50%')).toBeInTheDocument();
    expect(screen.getByText('部分完成')).toBeInTheDocument();
  });
});
