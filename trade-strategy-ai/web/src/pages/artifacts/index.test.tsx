import { describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen, waitFor } from '@testing-library/react';
import { ArtifactsPage } from './index';
import { renderWithRouter } from '@/test/test-utils';
import { downloadArtifact, getArtifact, listArtifacts } from '@/lib/api/artifacts';
import { ApiError } from '@/lib/api/http';

vi.mock('@/lib/api/artifacts', () => ({
  downloadArtifact: vi.fn(),
  getArtifact: vi.fn(),
  listArtifacts: vi.fn(),
}));

const mockedDownloadArtifact = vi.mocked(downloadArtifact);
const mockedGetArtifact = vi.mocked(getArtifact);
const mockedListArtifacts = vi.mocked(listArtifacts);

describe('ArtifactsPage', () => {
  it('shows the formal Artifact Center filters and syncs them into the query', async () => {
    const user = userEvent.setup();

    mockedListArtifacts.mockResolvedValue({
      count: 1,
      total: 1,
      skip: 0,
      limit: 50,
      items: [
        {
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
          metadata: {},
        },
      ],
    });

    renderWithRouter([{ path: '/artifacts', element: <ArtifactsPage /> }], ['/artifacts?jobId=job-1']);

    expect(screen.getByText('最近产物')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('搜索文本')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('按 job type 过滤')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('按日期过滤')).toBeInTheDocument();
    expect(screen.getByLabelText('Artifact kind')).toBeInTheDocument();

    await waitFor(() => {
      expect(mockedListArtifacts).toHaveBeenCalledWith(
        expect.objectContaining({
          job_id: 'job-1',
          limit: 50,
        }),
      );
    });

    await user.clear(screen.getByPlaceholderText('按 job type 过滤'));
    await user.type(screen.getByPlaceholderText('按 job type 过滤'), 'strategy-build');

    await waitFor(() => {
      expect(mockedListArtifacts).toHaveBeenLastCalledWith(
        expect.objectContaining({
          job_type: 'strategy-build',
          job_id: 'job-1',
          limit: 50,
        }),
      );
    });
  });

  it('shows artifact detail errors in the drawer', async () => {
    const user = userEvent.setup();

    mockedListArtifacts.mockResolvedValue({
      count: 1,
      total: 1,
      skip: 0,
      limit: 50,
      items: [
        {
          artifact_id: 'artifact-404',
          name: 'missing.json',
          title: 'missing.json',
          path: 'data/jobs/job-404/missing.json',
          kind: 'json',
          source: 'jobs',
          exists: true,
          size_bytes: 128,
          modified_at: '2026-05-09T08:05:00Z',
          previewable: true,
          job_id: 'job-404',
          job_type: 'strategy-build',
          storage_ref: {
            source: 'file',
            logical_id: 'job-404/missing.json',
            relative_path: 'job-404/missing.json',
            uri: null,
            metadata: {},
          },
          metadata: {},
        },
      ],
    });
    mockedGetArtifact.mockRejectedValueOnce(new ApiError(404, 'artifact not found'));

    renderWithRouter([{ path: '/artifacts', element: <ArtifactsPage /> }], ['/artifacts']);

    await user.click(await screen.findByRole('button', { name: '查看详情' }));

    expect(await screen.findByText('artifact not found')).toBeInTheDocument();
    expect(screen.queryByText('预览加载中...')).not.toBeInTheDocument();
  });

  it('shows download errors in the drawer', async () => {
    const user = userEvent.setup();

    mockedListArtifacts.mockResolvedValue({
      count: 1,
      total: 1,
      skip: 0,
      limit: 50,
      items: [
        {
          artifact_id: 'artifact-403',
          name: 'report.json',
          title: 'report.json',
          path: 'data/jobs/job-403/report.json',
          kind: 'json',
          source: 'jobs',
          exists: true,
          size_bytes: 128,
          modified_at: '2026-05-09T08:05:00Z',
          previewable: true,
          job_id: 'job-403',
          job_type: 'strategy-build',
          storage_ref: {
            source: 'file',
            logical_id: 'job-403/report.json',
            relative_path: 'job-403/report.json',
            uri: null,
            metadata: {},
          },
          metadata: {},
        },
      ],
    });
    mockedGetArtifact.mockResolvedValue({
      artifact_id: 'artifact-403',
      name: 'report.json',
      title: 'report.json',
      path: 'data/jobs/job-403/report.json',
      kind: 'json',
      source: 'jobs',
      exists: true,
      size_bytes: 128,
      modified_at: '2026-05-09T08:05:00Z',
      previewable: true,
      job_id: 'job-403',
      job_type: 'strategy-build',
      storage_ref: {
        source: 'file',
        logical_id: 'job-403/report.json',
        relative_path: 'job-403/report.json',
        uri: null,
        metadata: {},
      },
      metadata: {},
      preview: '{"ok":true}',
    });
    mockedDownloadArtifact.mockRejectedValueOnce(new ApiError(403, 'forbidden'));

    renderWithRouter([{ path: '/artifacts', element: <ArtifactsPage /> }], ['/artifacts']);

    await user.click(await screen.findByRole('button', { name: '查看详情' }));
    await user.click(await screen.findByRole('button', { name: '下载' }));

    expect(await screen.findByText('没有权限下载该产物。')).toBeInTheDocument();
  });
});
