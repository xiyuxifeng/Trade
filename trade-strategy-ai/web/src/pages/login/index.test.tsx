import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { login } from '@/lib/api/auth';
import { setAuthToken } from '@/lib/api/http';
import { LoginPage } from './index';

vi.mock('@/lib/api/auth', () => ({
  login: vi.fn(),
}));

vi.mock('@/lib/api/http', () => ({
  setAuthToken: vi.fn(),
}));

function DestinationProbe() {
  const location = useLocation();
  return <div>{`${location.pathname}${location.search}${location.hash}`}</div>;
}

function renderLogin(from: unknown) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter
        initialEntries={[{ pathname: '/login', state: { from } }]}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="*" element={<DestinationProbe />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

async function submitLogin() {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText('用户名'), 'alice');
  await user.type(screen.getByLabelText('密码'), 'secret');
  await user.click(screen.getByRole('button', { name: '登 录' }));
}

describe('LoginPage return path', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(login).mockResolvedValue({
      token: 'token',
      expires_at: '2026-06-12T00:00:00Z',
      user: {
        id: 'user-1',
        username: 'alice',
        display_name: 'Alice',
        role: 'viewer',
      },
    });
  });

  it('restores a safe internal pathname with search and hash after login', async () => {
    renderLogin({
      pathname: '/rules/review',
      search: '?source=home',
      hash: '#candidate',
    });

    await submitLogin();

    expect(await screen.findByText('/rules/review?source=home#candidate')).toBeInTheDocument();
    expect(setAuthToken).toHaveBeenCalledWith('token');
  });

  it.each(['https://evil.example/steal', '//evil.example/steal'])(
    'rejects unsafe return path %s',
    async (pathname) => {
    renderLogin({
      pathname,
      search: '',
      hash: '',
    });

    await submitLogin();
    expect(await screen.findByText('/')).toBeInTheDocument();

    await waitFor(() => expect(login).toHaveBeenCalledTimes(1));
    },
  );
});
