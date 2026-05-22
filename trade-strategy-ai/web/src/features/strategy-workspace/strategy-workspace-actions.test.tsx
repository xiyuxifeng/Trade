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
  it('opens confirmation and submits strategy-build with the selected profile_id', async () => {
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
              disabled={false}
              onSubmitted={() => undefined}
              profileId="default"
              snapshotId="snap-1"
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
            profile_id: 'default',
            trader_id: 'trader_a',
            strategy_date: '2026-05-16',
            force: false,
            snapshot_id: 'snap-1',
            market_regime_version: 'market-regime-v3',
            selected_by: 'web',
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
              disabled={false}
              onSubmitted={() => undefined}
              profileId="default"
              snapshotId="snap-1"
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
              disabled={false}
              onSubmitted={() => undefined}
              profileId="default"
              snapshotId="snap-1"
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
            profile_id: 'default',
            as_of_date: '2026-05-16',
            force: false,
          }),
        }),
      );
    });
  });
});
