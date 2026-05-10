import type { ReactElement } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { render } from '@testing-library/react';
import { AuthProvider } from '@/features/auth/auth-context';
import type { CurrentPrincipal } from '@/types/auth';

type RouteDefinition = {
  path: string;
  element: ReactElement;
};

const defaultTestPrincipal: CurrentPrincipal = {
  role: 'operator',
  api_key_label: 'Local Operator',
  authenticated: true,
  source: 'api_key',
};

export function renderWithRouter(
  routes: RouteDefinition[],
  initialEntries: string[],
  options?: { initialPrincipal?: CurrentPrincipal | null },
) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  const router = createMemoryRouter(routes, {
    initialEntries,
  });
  const initialPrincipal = options?.initialPrincipal ?? defaultTestPrincipal;

  return {
    ...render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider initialPrincipal={initialPrincipal}>
          <RouterProvider router={router} future={{ v7_startTransition: true }} />
        </AuthProvider>
      </QueryClientProvider>,
    ),
    router,
    queryClient,
  };
}
