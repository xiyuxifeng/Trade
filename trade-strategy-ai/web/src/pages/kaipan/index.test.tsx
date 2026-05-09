import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { KaipanPage } from './index';
import { renderWithRouter } from '@/test/test-utils';
import { kaipanStatus } from '@/lib/api/kaipan';

vi.mock('@/lib/api/kaipan', () => ({
  kaipanFetch: vi.fn(),
  kaipanNormalize: vi.fn(),
  kaipanRun: vi.fn(),
  kaipanStatus: vi.fn(),
}));

const mockedKaipanStatus = vi.mocked(kaipanStatus);

describe('KaipanPage', () => {
  it('renders the kaipan page title', async () => {
    mockedKaipanStatus.mockResolvedValue({
      config_path: 'config/app.yaml',
      base_dir: '/tmp/project',
      raw_base: '/tmp/project/data/processed/kaipan/raw',
      latest_slot: '2026-05-09_17-30',
    });

    renderWithRouter([{ path: '/kaipan', element: <KaipanPage /> }], ['/kaipan']);

    expect(await screen.findByText('Kaipan')).toBeInTheDocument();
    expect(await screen.findByText('2026-05-09_17-30')).toBeInTheDocument();
  });
});
