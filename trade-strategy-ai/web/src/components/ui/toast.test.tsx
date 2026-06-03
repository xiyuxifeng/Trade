import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, render, screen } from '@testing-library/react';
import { toast, Toaster } from './toast';

describe('Toaster', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('auto dismisses toast after five seconds', async () => {
    vi.useFakeTimers();

    render(<Toaster />);

    act(() => {
      toast({
        title: '文章抓取任务已提交',
        description: 'Job ee37782d-980c-4415-a048-ac4b12a5ae02 已创建，正在打开详情页。',
      });
    });

    expect(screen.getByText('文章抓取任务已提交')).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(screen.queryByText('文章抓取任务已提交')).not.toBeInTheDocument();
  });
});
