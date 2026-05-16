import { describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen } from '@testing-library/react';
import { renderWithRouter } from '@/test/test-utils';
import { ErrorState } from './ErrorState';

describe('ErrorState', () => {
  it('shows recovery details, retry and navigation actions', async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();

    renderWithRouter(
      [
        {
          path: '/jobs',
          element: (
            <ErrorState
              category="permission denied"
              title="没有权限访问任务列表"
              description="当前身份无法查看该页面。"
              suggestion="请切换到有权限的账号，或联系管理员。"
              detail="request_id=abc-123"
              actions={[{ label: '返回任务列表', to: '/jobs' }]}
              onRetry={onRetry}
            />
          ),
        },
      ],
      ['/jobs'],
    );

    expect(await screen.findByText('没有权限访问任务列表')).toBeInTheDocument();
    expect(screen.getByText('请切换到有权限的账号，或联系管理员。')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '查看技术详情' }));
    expect(screen.getByText('request_id=abc-123')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '重试' }));
    expect(onRetry).toHaveBeenCalledTimes(1);

    expect(screen.getByRole('link', { name: '返回任务列表' })).toBeInTheDocument();
  });
});
