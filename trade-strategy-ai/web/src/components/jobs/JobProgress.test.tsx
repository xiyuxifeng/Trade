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
    expect(screen.getByText('步骤进度 2 / 4 · 50%')).toBeInTheDocument();
    expect(screen.getByText(/剩余 2/)).toBeInTheDocument();
    expect(screen.getByText('子进度 3 / 6 · 50%')).toBeInTheDocument();
    expect(screen.getByText('步骤部分完成')).toBeInTheDocument();
  });

  it('shows step-oriented summary for success progress without implying terminal success', () => {
    render(
      <JobProgress
        progress={{
          job_type: 'crawl',
          stage: 'crawl',
          current: 1,
          total: 5,
          percent: 20,
          remaining: 4,
          current_trade_date: null,
          current_slot: null,
          current_fetcher: 'tgb',
          current_dataset: '10461311',
          current_step: 'save_crawl_state',
          status: 'success',
          error: null,
          updated_at: '2026-06-01T12:00:00Z',
        }}
      />,
    );

    expect(screen.getByText('步骤进度 1 / 5 · 20%')).toBeInTheDocument();
    expect(screen.getByText('当前步骤已完成，任务终态请看上方 Job 状态。')).toBeInTheDocument();
    expect(screen.getByText('步骤完成')).toBeInTheDocument();
    expect(screen.getByText('剩余 4')).toBeInTheDocument();
    expect(screen.queryByText('已完成 · 实际处理 1 条')).not.toBeInTheDocument();
    expect(screen.queryByText('本次上限 5 条，实际完成 1 条')).not.toBeInTheDocument();
  });
});
