import { fetchJson } from './http';
import type {
  KaipanFetchRequest,
  KaipanFetchResponse,
  KaipanNormalizeRequest,
  KaipanNormalizeResponse,
  KaipanRunRequest,
  KaipanRunResponse,
  KaipanStopResponse,
  KaipanStatusResponse,
} from '@/types/kaipan';

function buildQueryString(params: KaipanFetchRequest) {
  const query = new URLSearchParams();
  if (params.profile_id) query.set('profile_id', params.profile_id);
  if (params.trade_date) query.set('trade_date', params.trade_date);
  if (params.start_date) query.set('start_date', params.start_date);
  if (params.end_date) query.set('end_date', params.end_date);
  if (params.slot) query.set('slot', params.slot);
  return query.toString();
}

export function kaipanFetch(params: KaipanFetchRequest) {
  const suffix = buildQueryString(params);
  return fetchJson<KaipanFetchResponse>(`/kaipan/fetch${suffix ? `?${suffix}` : ''}`, {
    method: 'POST',
  });
}

export function kaipanStatus(profileId?: string | null) {
  const query = profileId ? `?profile_id=${encodeURIComponent(profileId)}` : '';
  return fetchJson<KaipanStatusResponse>(`/kaipan/status${query}`);
}

export function kaipanNormalize(payload: KaipanNormalizeRequest) {
  const { profile_id: profileId, ...body } = payload;
  const query = profileId ? `?profile_id=${encodeURIComponent(profileId)}` : '';
  return fetchJson<KaipanNormalizeResponse>(`/kaipan/normalize${query}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });
}

export function kaipanRun(payload: KaipanRunRequest, profileId?: string | null) {
  const query = profileId ? `?profile_id=${encodeURIComponent(profileId)}` : payload.profile_id ? `?profile_id=${encodeURIComponent(payload.profile_id)}` : '';
  const { profile_id: _profileId, ...body } = payload;
  return fetchJson<KaipanRunResponse>(`/kaipan/run${query}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });
}

export function kaipanStop(profileId?: string | null) {
  const query = profileId ? `?profile_id=${encodeURIComponent(profileId)}` : '';
  return fetchJson<KaipanStopResponse>(`/kaipan/stop${query}`, {
    method: 'POST',
  });
}
