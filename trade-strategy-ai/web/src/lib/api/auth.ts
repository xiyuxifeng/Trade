import type { CurrentPrincipal } from '@/types/auth';
import { fetchJson } from './http';

export function getCurrentPrincipal() {
  return fetchJson<CurrentPrincipal>('/auth/me');
}
