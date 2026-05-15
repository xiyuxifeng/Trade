import { beforeEach, describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { cleanup, render, screen } from '@testing-library/react';
import { ApiError } from '@/lib/api/http';
import { downloadArtifact } from '@/lib/api/artifacts';
import { ArtifactPanel } from './artifact-panel';
import type { JobArtifactRef } from '@/types/jobs';

vi.mock('@/lib/api/artifacts', () => ({
  downloadArtifact: vi.fn(),
}));

const mockedDownloadArtifact = vi.mocked(downloadArtifact);

beforeEach(() => {
  vi.clearAllMocks();
  cleanup();
});

function makeArtifact(overrides: Partial<JobArtifactRef> = {}): JobArtifactRef {
  return {
    artifact_id: 'artifact-1',
    job_id: 'job-1',
    workflow_id: 'workflow-1',
    step_id: 'crawl',
    kind: 'json',
    title: '抓取结果',
    summary: '抓取后的结构化数据',
    safe_download_url: '/api/ui/v1/artifacts/artifact-1/download',
    download_token: null,
    size_bytes: 2048,
    created_at: '2026-05-09T08:05:00Z',
    visibility: 'internal',
    metadata: { output_path: '/tmp/job-1/result.json', records: 3 },
    storage_ref: {
      source: 'file',
      logical_id: 'artifact-1',
      relative_path: 'jobs/job-1/result.json',
      uri: null,
      metadata: { format: 'json' },
    },
    ...overrides,
  };
}

describe('ArtifactPanel', () => {
  it('groups artifacts by step and renders a sanitized JSON preview', async () => {
    const user = userEvent.setup();
    mockedDownloadArtifact.mockResolvedValueOnce(new Blob(['artifact']));

    render(
      <ArtifactPanel
        artifacts={[
          makeArtifact({
            artifact_id: 'artifact-1',
            title: '抓取结果',
            step_id: 'crawl',
            metadata: { output_path: '/tmp/job-1/result.json', records: 3 },
          }),
          makeArtifact({
            artifact_id: 'artifact-2',
            title: '清洗结果',
            step_id: 'transform',
            kind: 'csv',
            summary: '清洗后的明细表',
            safe_download_url: null,
            metadata: { source: '/Users/wanghui/project/data.csv', rows: 12 },
          }),
          makeArtifact({
            artifact_id: 'artifact-3',
            title: '运行日志',
            step_id: null,
            kind: 'log',
            summary: null,
            metadata: { lines: 120 },
          }),
        ]}
      />,
    );

    expect(screen.getByText('步骤 crawl')).toBeInTheDocument();
    expect(screen.getByText('步骤 transform')).toBeInTheDocument();
    expect(screen.getByText('未关联步骤')).toBeInTheDocument();
    expect(screen.getByText('抓取结果')).toBeInTheDocument();
    expect(screen.getByText('清洗结果')).toBeInTheDocument();
    expect(screen.getByText('运行日志')).toBeInTheDocument();

    await user.click(screen.getAllByRole('button', { name: '预览' })[0]);
    await user.click(screen.getAllByRole('button', { name: '下载' })[0]);

    const previewLabel = await screen.findByText('JSON 预览');
    expect(previewLabel.closest('div')?.textContent).toContain('[已隐藏路径]');
    expect(screen.getByRole('button', { name: '下载不可用' })).toBeDisabled();
    expect(mockedDownloadArtifact).toHaveBeenCalledWith('artifact-1');
    expect(screen.getByText('该产物缺少安全下载入口，可能已丢失或尚未生成。')).toBeInTheDocument();
  });

  it('shows an empty fallback when no artifacts exist', () => {
    render(<ArtifactPanel artifacts={[]} />);

    expect(screen.getByText('该任务未产生任何产物。')).toBeInTheDocument();
  });

  it('shows a permission denied message when download fails with 403', async () => {
    const user = userEvent.setup();
    mockedDownloadArtifact.mockRejectedValueOnce(new ApiError(403, 'forbidden'));

    render(<ArtifactPanel artifacts={[makeArtifact({ artifact_id: 'artifact-403' })]} />);

    await user.click(screen.getByRole('button', { name: '下载' }));

    expect(await screen.findByText('没有权限下载该产物。')).toBeInTheDocument();
  });
});
