import { beforeEach, describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen, waitFor } from '@testing-library/react';
import { StrategyWorkspaceActions } from './strategy-workspace-actions';
import { renderWithRouter } from '@/test/test-utils';
import { createJob } from '@/lib/api/jobs';

vi.mock('@/lib/api/jobs', () => ({
  createJob: vi.fn(),
}));

const mockedCreateJob = vi.mocked(createJob);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('StrategyWorkspaceActions', () => {
  it('opens confirmation and submits strategy-build with the selected config_path', async () => {
    const user = userEvent.setup();

    mockedCreateJob.mockResolvedValue({
      created: true,
      job: { id: 'job-strategy-1' },
      job_dir: '/tmp/job-strategy-1',
      log_path: '/tmp/job-strategy-1/log.txt',
      params_path: '/tmp/job-strategy-1/params.json',
      result_path: '/tmp/job-strategy-1/result.json',
      artifacts_path: '/tmp/job-strategy-1/artifacts',
    } as never);

    renderWithRouter(
      [
        {
          path: '/',
          element: (
            <StrategyWorkspaceActions
              configPath="config/strategy-v3.yaml"
              disabled={false}
              onSubmitted={() => undefined}
              profileId="default"
              profileName="默认配置"
              snapshotCapturedAt="2026-05-16T08:00:00Z"
              strategyDate="2026-05-16"
              traderId="trader_a"
            />
          ),
        },
      ],
      ['/'],
    );

    await user.click(screen.getByRole('button', { name: /构建策略版本/ }));
    expect(screen.getByRole('dialog', { name: '确认构建策略版本' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '确认提交' }));

    await waitFor(() => {
      expect(mockedCreateJob).toHaveBeenCalledWith(
        expect.objectContaining({
          job_type: 'strategy-build',
          created_by: 'web',
          params: expect.objectContaining({
            config_path: 'config/strategy-v3.yaml',
            trader_id: 'trader_a',
            strategy_date: '2026-05-16',
            force: false,
          }),
        }),
      );
    });
  });

  it('keeps the confirm action disabled while a strategy submission is pending', async () => {
    const user = userEvent.setup();
    let resolveJob!: (value: unknown) => void;

    mockedCreateJob.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveJob = resolve;
        }) as never,
    );

    renderWithRouter(
      [
        {
          path: '/',
          element: (
            <StrategyWorkspaceActions
              configPath="config/strategy-v3.yaml"
              disabled={false}
              onSubmitted={() => undefined}
              profileId="default"
              profileName="默认配置"
              snapshotCapturedAt="2026-05-16T08:00:00Z"
              strategyDate="2026-05-16"
              traderId="trader_a"
            />
          ),
        },
      ],
      ['/'],
    );

    await user.click(screen.getByRole('button', { name: /构建策略版本/ }));
    await user.click(screen.getByRole('button', { name: '确认提交' }));

    const pendingButton = await screen.findByRole('button', { name: '提交中' });
    expect(pendingButton).toBeDisabled();

    await user.click(pendingButton);
    expect(mockedCreateJob).toHaveBeenCalledTimes(1);

    resolveJob({ created: true, job: { id: 'job-strategy-2' } });

    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: '确认构建策略版本' })).not.toBeInTheDocument();
    });
  });

  it('submits pre-market jobs with as_of_date derived from the selected strategy date', async () => {
    const user = userEvent.setup();

    mockedCreateJob.mockResolvedValue({
      created: true,
      job: { id: 'job-pre-market-1' },
      job_dir: '/tmp/job-pre-market-1',
      log_path: '/tmp/job-pre-market-1/log.txt',
      params_path: '/tmp/job-pre-market-1/params.json',
      result_path: '/tmp/job-pre-market-1/result.json',
      artifacts_path: '/tmp/job-pre-market-1/artifacts',
    } as never);

    renderWithRouter(
      [
        {
          path: '/',
          element: (
            <StrategyWorkspaceActions
              configPath="config/strategy-v3.yaml"
              disabled={false}
              onSubmitted={() => undefined}
              profileId="default"
              profileName="默认配置"
              snapshotCapturedAt="2026-05-16T08:00:00Z"
              strategyDate="2026-05-16"
              traderId="trader_a"
            />
          ),
        },
      ],
      ['/'],
    );

    await user.click(screen.getByRole('button', { name: /盘前运行/ }));
    expect(screen.getByRole('dialog', { name: '确认盘前运行' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '确认提交' }));

    await waitFor(() => {
      expect(mockedCreateJob).toHaveBeenCalledWith(
        expect.objectContaining({
          job_type: 'run-pre-market',
          params: expect.objectContaining({
            config_path: 'config/strategy-v3.yaml',
            as_of_date: '2026-05-16',
            force: false,
          }),
        }),
      );
    });
  });
});
