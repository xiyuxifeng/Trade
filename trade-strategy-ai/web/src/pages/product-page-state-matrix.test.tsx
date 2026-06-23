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
const actionableStates: PageAvailability[] = ['ready', 'partial', 'degraded'];

afterEach(cleanup);

describe('formal page state matrix', () => {
  it('derives every rendered page category from route config', () => {
    const renderedRoutes = routeConfig.filter((route) => route.renderMode !== 'redirect');

    expect(renderedRoutes.some((route) => route.kind === 'canonical')).toBe(true);
    expect(routeConfig.filter((route) => route.kind === 'compat').length).toBeGreaterThan(0);
    expect(renderedRoutes.every((route) => route.kind === 'canonical')).toBe(true);
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
          if (heading === '下一步' && availability !== 'partial') {
            expect(screen.queryByText(heading), `${route.path} ${availability}`).not.toBeInTheDocument();
            continue;
          }
          expect(screen.getByText(heading), `${route.path} ${availability}`).toBeInTheDocument();
        }
        expect(screen.queryByText('正式业务页面'), `${route.path} ${availability}`).not.toBeInTheDocument();
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
      if (heading === '下一步' && availability !== 'partial') {
        expect(screen.queryByText(heading)).not.toBeInTheDocument();
        continue;
      }
      expect(screen.getByText(heading)).toBeInTheDocument();
    }
    expect(screen.queryByText('正式业务页面')).not.toBeInTheDocument();
    expect(screen.getByText('影响什么：')).toBeInTheDocument();
    expect(screen.getByText('应该怎么处理：')).toBeInTheDocument();
  });

  it.each(actionableStates)('renders a compact next-action bar for actionable state %s', (availability) => {
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
              help="下一步说明只显示在可操作状态。"
            />
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>,
    );

    expect(screen.getByText('下一步')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '返回首页' })).toHaveAttribute('href', '/');
    expect(screen.getByRole('button', { name: '展开更多信息' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '状态验证页' })).toBeInTheDocument();
    expect(screen.queryByText('正式业务页面')).not.toBeInTheDocument();
  });
});
