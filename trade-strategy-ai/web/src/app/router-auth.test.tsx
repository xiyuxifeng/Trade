import type { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, render, waitFor } from '@testing-library/react';
import { Outlet, RouterProvider, createMemoryRouter, useLocation } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { AuthProvider } from '@/features/auth/auth-context';
import type { CurrentPrincipal } from '@/types/auth';
import { compatibilityRoutes } from './route-config';
import { RequireAuth, authenticatedRoutes } from './router';

const authenticatedPrincipal = (role: CurrentPrincipal['role']): CurrentPrincipal => ({
  role,
  api_key_label: role,
  authenticated: true,
  source: 'session',
});

function renderRouter(children: ReactNode, principal: CurrentPrincipal) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider initialPrincipal={principal}>{children}</AuthProvider>
    </QueryClientProvider>,
  );
}

function LocationStateProbe() {
  const location = useLocation();
  return <pre>{JSON.stringify({ pathname: location.pathname, state: location.state })}</pre>;
}

function createAuthenticatedRouter(initialEntry: string) {
  return createMemoryRouter(
    [
      {
        element: (
          <RequireAuth>
            <Outlet />
          </RequireAuth>
        ),
        children: authenticatedRoutes,
      },
    ],
    {
      initialEntries: [initialEntry],
      future: { v7_relativeSplatPath: true },
    },
  );
}

describe('router authentication and authorization', () => {
  it('preserves pathname, search, and hash when redirecting to login', async () => {
    const router = createMemoryRouter(
      [
        { path: '/login', element: <LocationStateProbe /> },
        {
          element: (
            <RequireAuth>
              <Outlet />
            </RequireAuth>
          ),
          children: [{ path: '/rules/review', element: <div>规则审核</div> }],
        },
      ],
      { initialEntries: ['/rules/review?source=home#candidate'] },
    );

    renderRouter(
      <RouterProvider router={router} future={{ v7_startTransition: true }} />,
      {
        role: 'anonymous',
        api_key_label: null,
        authenticated: false,
        source: 'anonymous',
      },
    );

    await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
    expect(router.state.location.state).toEqual({
      from: {
        pathname: '/rules/review',
        search: '?source=home',
        hash: '#candidate',
      },
    });
  });

  it('redirects viewer system entry to status and blocks admin subroutes', async () => {
    const testRoutes = authenticatedRoutes.map((route) => {
      if (route.path === '/system/status') {
        return { ...route, element: <div>系统状态</div> };
      }
      return route;
    });
    const router = createMemoryRouter(
      [
        {
          element: (
            <RequireAuth>
              <Outlet />
            </RequireAuth>
          ),
          children: testRoutes,
        },
      ],
      {
        initialEntries: ['/system/audit'],
        future: { v7_relativeSplatPath: true },
      },
    );

    renderRouter(
      <RouterProvider router={router} future={{ v7_startTransition: true }} />,
      {
        role: 'viewer',
        api_key_label: 'Viewer',
        authenticated: true,
        source: 'session',
      },
    );

    await waitFor(() => expect(router.state.location.pathname).toBe('/system/status'));

    await act(async () => {
      await router.navigate('/system');
    });
    await waitFor(() => expect(router.state.location.pathname).toBe('/system/status'));

    await act(async () => {
      await router.navigate('/system/status');
    });
    expect(router.state.location.pathname).toBe('/system/status');
  });

  for (const role of ['viewer', 'operator'] as const) {
    it.each([
      ['/system/configuration', '/system/configuration'],
      ['/system/data', '/system/data'],
      ['/system/runs', '/system/runs'],
      ['/settings', '/system/configuration'],
    ])(`allows ${role} to access %s without an admin route guard`, async (entry, expectedPath) => {
      const router = createAuthenticatedRouter(entry);

      renderRouter(
        <RouterProvider router={router} future={{ v7_startTransition: true }} />,
        authenticatedPrincipal(role),
      );

      await waitFor(() => expect(router.state.location.pathname).toBe(expectedPath));
    });
  }

  const redirectRoutes = compatibilityRoutes.filter((route) => route.legacy?.mode === 'redirect');

  it.each(redirectRoutes)(
    'navigates compat redirect $path to its declared target',
    async ({ path, legacy }) => {
      const router = createAuthenticatedRouter(path);

      renderRouter(
        <RouterProvider router={router} future={{ v7_startTransition: true }} />,
        authenticatedPrincipal('admin'),
      );

      await waitFor(() => expect(router.state.location.pathname).toBe(legacy?.targetPath));
    },
  );

  it('keeps a dynamic notice deep link on its original pathname', async () => {
    const router = createAuthenticatedRouter('/jobs/job-123');

    renderRouter(
      <RouterProvider router={router} future={{ v7_startTransition: true }} />,
      authenticatedPrincipal('admin'),
    );

    await waitFor(() => expect(router.state.location.pathname).toBe('/jobs/job-123'));
  });

  it('matches unknown paths with the Chinese 404 route', async () => {
    const router = createAuthenticatedRouter('/route-that-does-not-exist');

    const view = renderRouter(
      <RouterProvider router={router} future={{ v7_startTransition: true }} />,
      authenticatedPrincipal('admin'),
    );

    await waitFor(() => expect(view.getByRole('heading', { name: '页面未找到' })).toBeInTheDocument());
  });

  it('matches a static route before the wildcard route', async () => {
    const router = createAuthenticatedRouter('/system/status');

    const view = renderRouter(
      <RouterProvider router={router} future={{ v7_startTransition: true }} />,
      authenticatedPrincipal('viewer'),
    );

    await waitFor(() => expect(view.getByRole('heading', { name: '系统状态入口迁移中' })).toBeInTheDocument());
    expect(view.queryByRole('heading', { name: '页面未找到' })).not.toBeInTheDocument();
  });
});
