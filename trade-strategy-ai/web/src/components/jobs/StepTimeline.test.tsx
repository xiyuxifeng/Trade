import { describe, expect, it } from 'vitest';
import userEvent from '@testing-library/user-event';
import { render, screen } from '@testing-library/react';
import { StepTimeline } from './StepTimeline';

describe('StepTimeline', () => {
  it('shows an empty fallback when there are no items', () => {
    render(<StepTimeline items={[]} />);

    expect(screen.getByText('暂无步骤时间线')).toBeInTheDocument();
  });

  it('expands a step to reveal details', async () => {
    const user = userEvent.setup();

    render(
      <StepTimeline
        items={[
          {
            id: 'step-1',
            stepName: 'crawl',
            title: '抓取文章',
            status: 'failed',
            startedAt: '2026-05-15T01:00:00Z',
            finishedAt: '2026-05-15T01:05:00Z',
            durationMs: 300000,
            errorSummary: '抓取超时',
            details: { url: 'https://example.com/articles/1' },
          },
        ]}
      />,
    );

    expect(screen.getByText('抓取文章')).toBeInTheDocument();
    expect(screen.getByText('失败')).toBeInTheDocument();
    expect(screen.getByText(/5 分钟/)).toBeInTheDocument();

    await user.click(screen.getAllByRole('button', { name: '展开步骤详情' })[0]);

    expect(screen.getByText('抓取超时')).toBeInTheDocument();
    expect(screen.getByText(/example.com\/articles\/1/)).toBeInTheDocument();
  });
});
