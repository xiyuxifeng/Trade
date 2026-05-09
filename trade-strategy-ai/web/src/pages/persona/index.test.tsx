import { describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen, waitFor } from '@testing-library/react';
import { PersonaPage } from './index';
import { renderWithRouter } from '@/test/test-utils';
import { buildSampleClusters } from '@/lib/api/persona';

vi.mock('@/lib/api/persona', () => ({
  buildMarketState: vi.fn(),
  buildSampleClusters: vi.fn(),
}));

const mockedBuildSampleClusters = vi.mocked(buildSampleClusters);

describe('PersonaPage', () => {
  it('generates sample clusters from the workbench', async () => {
    const user = userEvent.setup();
    mockedBuildSampleClusters.mockResolvedValue({
      config_path: 'config/app.yaml',
      base_dir: '/tmp/project',
      clusters_path: '/tmp/project/data/processed/persona/clusters.sample.json',
      trader_count: 3,
      clusters_count: 6,
    });

    renderWithRouter([{ path: '/persona', element: <PersonaPage /> }], ['/persona']);

    expect(await screen.findByText('Persona')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Generate sample clusters' }));

    await waitFor(() => {
      expect(mockedBuildSampleClusters).toHaveBeenCalled();
    });
    expect(
      screen.getByText((_, element) => element?.tagName.toLowerCase() === 'p' && element.textContent?.includes('clusters.sample.json') === true),
    ).toBeInTheDocument();
  });
});
