import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { LegacyRouteMetadata } from '@/app/route-config';
import { CompatibilityNotice } from './compatibility-notice';

describe('CompatibilityNotice', () => {
  it('explains the formal target and keeps the legacy link clear', () => {
    const legacy: LegacyRouteMetadata = {
      targetPath: '/system/status',
      mode: 'redirect',
      retireStage: '长期保留',
      retireCondition: '系统状态正式入口已稳定，可直接进入。',
      retirementRequired: false,
    };

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <CompatibilityNotice
            legacy={legacy}
            legacyLabel="系统管理旧入口"
            continueAction={{ label: '继续查看当前入口', onClick: vi.fn() }}
          />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByText('正式入口')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '前往正式入口' })).toHaveAttribute('href', '/system/status');
    expect(screen.getByText('退役条件')).toBeInTheDocument();
    expect(screen.getByText('系统状态正式入口已稳定，可直接进入。')).toBeInTheDocument();
    expect(screen.getAllByText('当前入口继续保留，方便已有链接继续可用。').length).toBeGreaterThan(0);
    expect(screen.getByRole('button', { name: '继续查看当前入口' })).toBeInTheDocument();
    expect(screen.queryByText('redirect')).not.toBeInTheDocument();
    expect(screen.queryByText('notice')).not.toBeInTheDocument();
  });
});
