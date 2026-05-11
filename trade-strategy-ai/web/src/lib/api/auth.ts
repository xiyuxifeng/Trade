import type { CurrentPrincipal } from '@/types/auth';
import { fetchJson } from './http';

export type LoginRequest = {
  username: string;
  password: string;
};

export type LoginResponse = {
  token: string;
  expires_at: string;
  user: {
    id: string;
    username: string;
    role: string;
    display_name: string | null;
  };
};

export type UserRecord = {
  id: string;
  username: string;
  role: string;
  is_active: boolean;
  display_name: string | null;
  last_login_at: string | null;
  created_at: string | null;
};

export function getCurrentPrincipal() {
  return fetchJson<CurrentPrincipal>('/auth/me');
}

export function login(data: LoginRequest) {
  return fetchJson<LoginResponse>('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export function logout() {
  return fetchJson<{ message: string }>('/auth/logout', { method: 'POST' });
}

export function listUsers() {
  return fetchJson<UserRecord[]>('/auth/users');
}

export function createUser(data: {
  username: string;
  password: string;
  role: string;
  display_name?: string;
}) {
  return fetchJson<UserRecord>('/auth/users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export function updateUser(
  userId: string,
  data: {
    role?: string;
    is_active?: boolean;
    display_name?: string;
    password?: string;
  },
) {
  return fetchJson<UserRecord>(`/auth/users/${userId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export function deleteUser(userId: string) {
  return fetchJson<{ message: string }>(`/auth/users/${userId}`, {
    method: 'DELETE',
  });
}
