import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { SystemPage } from './index';
import { renderWithRouter } from '@/test/test-utils';

vi.mock('@/features/system-management/system-management-workspace', () => ({
  SystemManagementWorkspace: () => <div>system-workspace</div>,
}));

describe('SystemPage', () => {
  it('renders the system management page shell', async () => {
    renderWithRouter([{ path: '/system', element: <SystemPage /> }], ['/system']);

    expect(await screen.findByRole('heading', { name: '系统管理' })).toBeInTheDocument();
    expect(screen.getByText('system-workspace')).toBeInTheDocument();
  });
});
