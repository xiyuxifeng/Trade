import { beforeEach, describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen, waitFor } from '@testing-library/react';
import { ArtifactDetailPage, ArtifactsPage } from './index';
import { renderWithRouter } from '@/test/test-utils';
import {
  downloadArtifact,
  getArtifact,
  listArtifactFilterOptions,
  listArtifacts,
} from '@/lib/api/artifacts';
import { ApiError } from '@/lib/api/http';
import type { ArtifactRecord } from '@/types/artifacts';

vi.mock('@/lib/api/artifacts', () => ({
  downloadArtifact: vi.fn(),
  getArtifact: vi.fn(),
  listArtifactFilterOptions: vi.fn(),
  listArtifacts: vi.fn(),
}));

const mockedDownloadArtifact = vi.mocked(downloadArtifact);
const mockedGetArtifact = vi.mocked(getArtifact);
const mockedListArtifactFilterOptions = vi.mocked(listArtifactFilterOptions);
const mockedListArtifacts = vi.mocked(listArtifacts);

const filterOptions = {
  status: 'success',
  kinds: ['html', 'json'],
  sources: ['jobs', 'processed'],
  job_types: ['strategy-build', 'run-pre-market'],
  job_ids: ['job-2', 'job-1'],
};

const artifactItem: ArtifactRecord = {
  artifact_id: 'artifact-1',
  name: 'job result',
  title: 'job result',
  path: 'data/jobs/job-1/result.json',
  kind: 'json',
  source: 'jobs',
  exists: true,
  size_bytes: 128,
  modified_at: '2026-05-09T08:05:00Z',
  previewable: true,
  job_id: 'job-1',
  job_type: 'strategy-build',
  storage_ref: {
    source: 'file',
    logical_id: 'job-1/result.json',
    relative_path: 'job-1/result.json',
    uri: null,
    metadata: {},
  },
  metadata: { summary: 'demo' },
  preview: '{"ok":true}',
  download_name: 'result.json',
};

describe('ArtifactsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders dropdown filters and only submits after search', async () => {
    const user = userEvent.setup();

    mockedListArtifactFilterOptions.mockResolvedValue(filterOptions);
    mockedListArtifacts.mockResolvedValue({
      count: 1,
      total: 1,
      skip: 0,
      limit: 50,
      items: [artifactItem],
    });

    renderWithRouter([{ path: '/artifacts', element: <ArtifactsPage /> }], ['/artifacts?jobId=job-1']);

    expect(screen.getByText('筛选条件')).toBeInTheDocument();
    expect(screen.getByText('最近产物')).toBeInTheDocument();
    expect(await screen.findByRole('combobox', { name: '产物类型' })).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: '来源' })).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: 'Job Type' })).toBeInTheDocument();
    expect(screen.getByLabelText('任务 ID')).toBeInTheDocument();
    expect(screen.getByLabelText('日期')).toBeInTheDocument();

    await waitFor(() => {
      expect(mockedListArtifacts).toHaveBeenCalledWith(
        expect.objectContaining({
          job_id: 'job-1',
          limit: 50,
        }),
      );
    });

    await user.selectOptions(screen.getByLabelText('产物类型'), 'html');
    await user.selectOptions(screen.getByLabelText('来源'), 'processed');
    await user.selectOptions(screen.getByLabelText('Job Type'), 'run-pre-market');
    await user.clear(screen.getByLabelText('任务 ID'));
    await user.type(screen.getByLabelText('任务 ID'), 'job-2');
    await user.type(screen.getByLabelText('日期'), '2026-05-09');

    await user.click(screen.getByRole('button', { name: '搜索' }));

    await waitFor(() => {
      expect(mockedListArtifacts).toHaveBeenLastCalledWith(
        expect.objectContaining({
          kind: 'html',
          source: 'processed',
          job_type: 'run-pre-market',
          job_id: 'job-2',
          date: '2026-05-09',
          limit: 50,
        }),
      );
    });

    expect(screen.getByText('总计 1')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'job result' })).toBeInTheDocument();
  });

  it('navigates to detail page and back', async () => {
    const user = userEvent.setup();

    mockedListArtifactFilterOptions.mockResolvedValue(filterOptions);
    mockedListArtifacts.mockResolvedValue({
      count: 1,
      total: 1,
      skip: 0,
      limit: 50,
      items: [artifactItem],
    });
    mockedGetArtifact.mockResolvedValue({
      ...artifactItem,
      preview: '{"ok":true}',
    });

    const { router } = renderWithRouter(
      [
        { path: '/artifacts', element: <ArtifactsPage /> },
        { path: '/artifacts/:artifactId', element: <ArtifactDetailPage /> },
      ],
      ['/artifacts'],
    );

    await user.click(await screen.findByRole('button', { name: '查看详情' }));

    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/artifacts/artifact-1');
    });
    expect(screen.getByRole('heading', { name: 'job result' })).toBeInTheDocument();
    expect(screen.getByText('总览信息')).toBeInTheDocument();

    await user.click(screen.getByRole('link', { name: '返回列表' }));

    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/artifacts');
    });
  });

  it('shows detail load errors on the standalone detail page', async () => {
    mockedGetArtifact.mockRejectedValueOnce(new ApiError(404, 'artifact not found'));

    renderWithRouter([{ path: '/artifacts/:artifactId', element: <ArtifactDetailPage /> }], ['/artifacts/artifact-404']);

    expect(await screen.findByText('产物不可用')).toBeInTheDocument();
    expect(screen.getByText('先查看来源 Job，再判断是否需要重新运行。')).toBeInTheDocument();
    expect(screen.queryByText('预览')).not.toBeInTheDocument();
  });

  it('shows download errors on the standalone detail page', async () => {
    const user = userEvent.setup();

    mockedGetArtifact.mockResolvedValue({
      ...artifactItem,
      preview: '{"ok":true}',
    });
    mockedDownloadArtifact.mockRejectedValueOnce(new ApiError(403, 'forbidden'));

    renderWithRouter([{ path: '/artifacts/:artifactId', element: <ArtifactDetailPage /> }], ['/artifacts/artifact-1']);

    await user.click(await screen.findByRole('button', { name: '下载产物' }));

    expect(await screen.findByText('forbidden')).toBeInTheDocument();
  });
});
