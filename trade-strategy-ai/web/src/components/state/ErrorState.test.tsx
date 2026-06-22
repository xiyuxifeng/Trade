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
      {
        initialPrincipal: {
          role: 'viewer',
          api_key_label: 'Local Viewer',
          authenticated: true,
          source: 'api_key',
        },
      },
    );

    expect(await screen.findByText('没有权限访问任务列表')).toBeInTheDocument();
    expect(screen.getByText('当前身份无法查看该页面。')).toBeInTheDocument();
    expect(screen.getByText('当前账号无法继续查看或执行相关操作。')).toBeInTheDocument();
    expect(screen.getByText('请切换到有权限的账号，或联系管理员。')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '查看运维诊断详情' })).not.toBeInTheDocument();
    expect(screen.queryByText('request_id=abc-123')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '重试' }));
    expect(onRetry).toHaveBeenCalledTimes(1);

    expect(screen.getByRole('link', { name: '返回任务列表' })).toBeInTheDocument();
  });

  it('shows diagnostic detail only to operator/admin viewers', async () => {
    const user = userEvent.setup();

    renderWithRouter(
      [
        {
          path: '/system',
          element: (
            <ErrorState
              category="provider unavailable"
              title="系统状态暂不可用"
              description="状态接口请求失败。"
              affected="当前无法确认系统是否支持后续业务操作。"
              suggestion="请先刷新状态；如果持续失败，请联系管理员。"
              detail="trace_id=trace-001"
            />
          ),
        },
      ],
      ['/system'],
      {
        initialPrincipal: {
          role: 'operator',
          api_key_label: 'Local Operator',
          authenticated: true,
          source: 'api_key',
        },
      },
    );

    await user.click(screen.getByRole('button', { name: '查看运维诊断详情' }));
    expect(screen.getByText('trace_id=trace-001')).toBeInTheDocument();
  });
});
