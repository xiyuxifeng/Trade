import { fetchJson } from './http';
import type { AuthorProfileListResponse, AuthorProfileVersion } from '@/types/authors';

export function listAuthorProfiles() {
  return fetchJson<AuthorProfileListResponse>('/authors/profiles', {
    method: 'GET',
  });
}

export function getAuthorProfile(versionId: string) {
  return fetchJson<AuthorProfileVersion>(`/authors/profiles/${versionId}`, {
    method: 'GET',
  });
}
