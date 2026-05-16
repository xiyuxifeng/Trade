import { beforeEach, describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen, waitFor } from '@testing-library/react';
import { ApiError } from '@/lib/api/http';
import { MarketPage } from './index';
import { renderWithRouter } from '@/test/test-utils';
import { createJob, listJobs } from '@/lib/api/jobs';
import { listArtifacts } from '@/lib/api/artifacts';

vi.mock('@/lib/api/jobs', () => ({
  createJob: vi.fn(),
  listJobs: vi.fn(),
}));

vi.mock('@/lib/api/artifacts', () => ({
  listArtifacts: vi.fn(),
  getArtifact: vi.fn(),
  downloadArtifact: vi.fn(),
}));

const mockedCreateJob = vi.mocked(createJob);
const mockedListJobs = vi.mocked(listJobs);
const mockedListArtifacts = vi.mocked(listArtifacts);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('MarketPage', () => {
  it('renders the market workspace entry page and submits snapshot-build jobs', async () => {
    const user = userEvent.setup();

    mockedListJobs.mockResolvedValue({
      count: 0,
      total: 0,
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
    mockedCreateJob.mockResolvedValue({
      created: true,
      job: { id: 'job-market-1' },
      job_dir: '/tmp/job-market-1',
      log_path: '/tmp/job-market-1/log.txt',
      params_path: '/tmp/job-market-1/params.json',
      result_path: '/tmp/job-market-1/result.json',
      artifacts_path: '/tmp/job-market-1/artifacts',
    } as never);

    renderWithRouter([{ path: '/market', element: <MarketPage /> }], ['/market']);

    expect(await screen.findByRole('heading', { name: '市场数据工作台' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '运行快照构建' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '运行快照构建' }));

    await waitFor(() => {
      expect(mockedCreateJob).toHaveBeenCalledWith(
        expect.objectContaining({
          job_type: 'snapshot-build',
          params: expect.objectContaining({ config_path: 'config/app.yaml' }),
        }),
      );
    });
  });

  it('shows a shared recovery error when market queries fail', async () => {
    mockedListJobs.mockRejectedValueOnce(new ApiError(503, 'provider unavailable'));
    mockedListArtifacts.mockResolvedValue({
      count: 0,
      total: 0,
      skip: 0,
      limit: 8,
      items: [],
    } as never);

    renderWithRouter([{ path: '/market', element: <MarketPage /> }], ['/market']);

    expect(await screen.findAllByText('上游服务不可用')).toHaveLength(2);
    expect(screen.getAllByText('前往设置').length).toBeGreaterThan(0);
  });
});
