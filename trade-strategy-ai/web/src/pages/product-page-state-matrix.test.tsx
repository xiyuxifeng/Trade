import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import type { PageAvailability } from '@/components/layout/business-page-shell';
import { ProductPageAdapter } from '@/components/layout/product-page-adapter';
import { AuthProvider } from '@/features/auth/auth-context';
import { renderRouteWithAvailability, routeConfig } from '@/app/route-config';

const states: PageAvailability[] = [
  'loading',
  'empty',
  'error',
  'partial',
  'permission_denied',
  'unavailable',
];

afterEach(cleanup);

describe('formal page state matrix', () => {
  it('derives every rendered page category from route config', () => {
    const renderedRoutes = routeConfig.filter((route) => route.renderMode !== 'redirect');

    expect(renderedRoutes.some((route) => route.kind === 'canonical')).toBe(true);
    expect(renderedRoutes.some((route) => route.kind === 'compat')).toBe(true);
    expect(renderedRoutes.some((route) => route.path.includes(':'))).toBe(true);
    expect(renderedRoutes.map((route) => route.path)).toContain('/jobs/:jobId');
    expect(renderedRoutes.map((route) => route.path)).toContain('/system/runs');
    expect(renderedRoutes.map((route) => route.path)).toContain('*');
    expect(routeConfig.filter((route) => route.renderMode === 'redirect').length).toBeGreaterThan(0);
  });

  it('renders every route-derived page across the six non-ready states', () => {
    const renderedRoutes = routeConfig.filter((route) => route.renderMode !== 'redirect');

    for (const route of renderedRoutes) {
      for (const availability of states) {
        const queryClient = new QueryClient({
          defaultOptions: {
            queries: { retry: false },
          },
        });
        render(
          <QueryClientProvider client={queryClient}>
            <AuthProvider
              initialPrincipal={{
                role: 'viewer',
                api_key_label: null,
                authenticated: true,
                source: 'session',
                username: 'viewer',
              }}
            >
              <MemoryRouter>{renderRouteWithAvailability(route, availability)}</MemoryRouter>
            </AuthProvider>
          </QueryClientProvider>,
        );

        for (const heading of ['页面用途', '输入', '处理状态', '输出', '下一步']) {
          expect(screen.getByText(heading), `${route.path} ${availability}`).toBeInTheDocument();
        }
        cleanup();
      }
    }
  });

  it.each(states)('preserves the five-part contract for %s', (availability) => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider
          initialPrincipal={{
            role: 'viewer',
            api_key_label: null,
            authenticated: true,
            source: 'session',
            username: 'viewer',
          }}
        >
          <MemoryRouter>
            <ProductPageAdapter
              title="状态验证页"
              queryState={availability}
              purpose="验证正式页面状态表达。"
              inputDescription="输入来自真实业务数据。"
              processingDescription="系统读取真实状态，不替换缺失值。"
              outputDescription="输出只展示已确认结果。"
              businessAction={{ label: '返回首页', to: '/' }}
              result={<div>当前可用结果</div>}
            />
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>,
    );

    for (const heading of ['页面用途', '输入', '处理状态', '输出', '下一步']) {
      expect(screen.getByText(heading)).toBeInTheDocument();
    }
    expect(screen.getByText('影响：')).toBeInTheDocument();
    expect(screen.getByText('处理方式：')).toBeInTheDocument();
  });
});
