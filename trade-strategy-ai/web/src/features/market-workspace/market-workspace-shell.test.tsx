import { beforeEach, describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen, waitFor } from '@testing-library/react';
import { MarketWorkspaceShell } from './market-workspace-shell';
import { renderWithRouter } from '@/test/test-utils';
import { createJob, listJobs } from '@/lib/api/jobs';
import { listArtifacts } from '@/lib/api/artifacts';
import { listBenchmarkOptions } from '@/lib/api/market';

vi.mock('@/lib/api/jobs', () => ({
  createJob: vi.fn(),
  listJobs: vi.fn(),
}));

vi.mock('@/lib/api/artifacts', () => ({
  listArtifacts: vi.fn(),
  getArtifact: vi.fn(),
  downloadArtifact: vi.fn(),
}));

vi.mock('@/lib/api/market', () => ({
  listBenchmarkOptions: vi.fn(),
}));

const mockedCreateJob = vi.mocked(createJob);
const mockedListJobs = vi.mocked(listJobs);
const mockedListArtifacts = vi.mocked(listArtifacts);
const mockedListBenchmarkOptions = vi.mocked(listBenchmarkOptions);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('MarketWorkspaceShell', () => {
  it('renders the market workspace and can submit a market job', async () => {
    const user = userEvent.setup();

    mockedListJobs.mockResolvedValue({
      count: 1,
      total: 1,
      skip: 0,
      limit: 12,
      items: [],
    } as never);
    mockedListArtifacts.mockResolvedValue({
      count: 0,
      total: 0,
      skip: 0,
      limit: 8,
      items: [],
    } as never);
    mockedListBenchmarkOptions.mockResolvedValue({
      count: 2,
      items: [
        { symbol: '000300.SH', code: '000300', market: 'CN', name: '沪深300', security_type: 'index' },
        { symbol: '510300.SH', code: '510300', market: 'CN', name: '沪深300ETF', security_type: 'etf' },
      ],
    } as never);
    mockedCreateJob.mockResolvedValue({
      created: true,
      job: { id: 'job-market-1' },
      job_dir: '/tmp/job-market-1',
      log_path: '/tmp/job-market-1/log.txt',
      params_path: '/tmp/job-market-1/params.json',
      result_path: '/tmp/job-market-1/result.json',
      artifacts_path: '/tmp/job-market-1/artifacts',
    } as never);

    renderWithRouter([{ path: '/market', element: <MarketWorkspaceShell /> }], ['/market']);

    expect(await screen.findByRole('heading', { name: '市场数据工作台' })).toBeInTheDocument();
    expect(screen.getByText('运行指定任务')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '运行快照构建' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '运行快照构建' }));

    await waitFor(() => {
      expect(mockedCreateJob).toHaveBeenCalledWith(
        expect.objectContaining({
          job_type: 'snapshot-build',
          params: expect.objectContaining({
            config_path: 'config/app.yaml',
            benchmark_symbol: '000300.SH',
          }),
        }),
      );
    });
  });
});
