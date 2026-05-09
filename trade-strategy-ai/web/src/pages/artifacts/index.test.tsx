import { describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen, waitFor } from '@testing-library/react';
import { ArtifactsPage } from './index';
import { renderWithRouter } from '@/test/test-utils';
import { listArtifacts } from '@/lib/api/artifacts';

vi.mock('@/lib/api/artifacts', () => ({
  downloadArtifact: vi.fn(),
  getArtifact: vi.fn(),
  listArtifacts: vi.fn(),
}));

const mockedListArtifacts = vi.mocked(listArtifacts);

describe('ArtifactsPage', () => {
  it('filters artifacts by job id from the URL and updates the query when edited', async () => {
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
          path: 'data/jobs/job-1/result.json',
          kind: 'json',
          source: 'jobs',
          exists: true,
          size_bytes: 128,
          modified_at: '2026-05-09T08:05:00Z',
          previewable: true,
          job_id: 'job-1',
          metadata: {},
        },
      ],
    });

    renderWithRouter([{ path: '/artifacts', element: <ArtifactsPage /> }], ['/artifacts?jobId=job-1']);

    await waitFor(() => {
      expect(mockedListArtifacts).toHaveBeenCalledWith(
        expect.objectContaining({
          job_id: 'job-1',
          limit: 50,
        }),
      );
    });

    expect(screen.getByDisplayValue('job-1')).toBeInTheDocument();

    await user.clear(screen.getByPlaceholderText('Filter by job id'));
    await user.type(screen.getByPlaceholderText('Filter by job id'), 'job-2');

    await waitFor(() => {
      expect(mockedListArtifacts).toHaveBeenLastCalledWith(
        expect.objectContaining({
          job_id: 'job-2',
          limit: 50,
        }),
      );
    });
  });
});
