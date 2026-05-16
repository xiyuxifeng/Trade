import { fetchJson } from './http';
import type {
  ProfileArchiveRequest,
  ProfileArchiveResponse,
  ProfileDetailResponse,
  ProfileEditDraft,
  ProfileEditResponse,
  ProfileImportRequest,
  ProfileImportResponse,
  ProfileListResponse,
  ProfileSnapshotResponse,
  ProfileUpdateRequest,
  ProfileUpdateResponse,
  ProfileValidationResponse,
} from '@/types/profile';

type ProfilesQuery = {
  environment?: string;
  validation_status?: string;
  skip?: number;
  limit?: number;
};

export function listProfiles(query: ProfilesQuery = {}) {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      return;
    }
    params.set(key, String(value));
  });
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return fetchJson<ProfileListResponse>(`/profiles${suffix}`);
}

export function getProfile(profileId: string) {
  return fetchJson<ProfileDetailResponse>(`/profiles/${profileId}`);
}

export function getProfileEdit(profileId: string) {
  return fetchJson<ProfileEditResponse>(`/profiles/${profileId}/edit`);
}

export function validateProfileUpdate(profileId: string, draft: ProfileEditDraft) {
  return fetchJson<ProfileValidationResponse>(`/profiles/${profileId}/validate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(draft),
  });
}

export function updateProfile(profileId: string, request: ProfileUpdateRequest) {
  return fetchJson<ProfileUpdateResponse>(`/profiles/${profileId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}

export function archiveProfile(profileId: string, request: ProfileArchiveRequest) {
  return fetchJson<ProfileArchiveResponse>(`/profiles/${profileId}/archive`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}

export function importProfile(request: ProfileImportRequest) {
  return fetchJson<ProfileImportResponse>('/profiles/import', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}

export function getProfileSnapshot(profileId: string, snapshotId: string) {
  return fetchJson<ProfileSnapshotResponse>(`/profiles/${profileId}/snapshots/${snapshotId}`);
}
