import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { DataHealthPage } from './index';
import { renderWithRouter } from '@/test/test-utils';
import { buildDashboardReport } from '@/lib/api/dataHealth';

vi.mock('@/lib/api/dataHealth', () => ({
  buildDashboardReport: vi.fn(),
}));

const mockedBuildDashboardReport = vi.mocked(buildDashboardReport);

describe('DataHealthPage', () => {
  it('renders the data health page title', async () => {
    mockedBuildDashboardReport.mockResolvedValue({
      config_path: 'config/app.yaml',
      report: { title: 'Daily Health' },
      html_path: '/tmp/project/data/processed/dashboard/dashboard.html',
      critical_alerts: 0,
      exit_code: 0,
    });

    renderWithRouter([{ path: '/data-health', element: <DataHealthPage /> }], ['/data-health']);

    expect(await screen.findByText('Data Health')).toBeInTheDocument();
    expect(
      await screen.findByText('/tmp/project/data/processed/dashboard/dashboard.html', { selector: 'p' }),
    ).toBeInTheDocument();
    expect(await screen.findByTestId('data-health-json')).toHaveTextContent('dashboard.html');
  });
});
