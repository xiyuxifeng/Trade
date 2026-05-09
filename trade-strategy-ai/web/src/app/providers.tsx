import type { ReactNode } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider, createBrowserRouter } from 'react-router-dom';
import { queryClient } from './query-client';
import { Toaster } from '@/components/ui/toast';

type AppProvidersProps = {
  router: ReturnType<typeof createBrowserRouter>;
  children?: ReactNode;
};

export function AppProviders({ router }: AppProvidersProps) {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      <Toaster />
    </QueryClientProvider>
  );
}
