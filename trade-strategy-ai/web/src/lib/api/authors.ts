import { fetchJson } from './http';
import type {
  AuthorMethodProfileDraftRequest,
  AuthorProfileListResponse,
  AuthorProfileVersion,
} from '@/types/authors';

export function listAuthorProfiles(profileKind?: 'method' | 'rule' | 'validated') {
  const query = profileKind ? `?profile_kind=${profileKind}` : '';
  return fetchJson<AuthorProfileListResponse>(`/authors/profiles${query}`, {
    method: 'GET',
  });
}

export function getAuthorProfile(versionId: string) {
  return fetchJson<AuthorProfileVersion>(`/authors/profiles/${versionId}`, {
    method: 'GET',
  });
}

export function createAuthorMethodProfileDraft(payload: AuthorMethodProfileDraftRequest) {
  return fetchJson<AuthorProfileVersion>('/authors/method-profiles/drafts', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
