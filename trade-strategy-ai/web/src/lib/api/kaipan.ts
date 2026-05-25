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

export function kaipanStatus() {
  return fetchJson<KaipanStatusResponse>('/kaipan/status');
}

export function kaipanNormalize(payload: KaipanNormalizeRequest) {
  return fetchJson<KaipanNormalizeResponse>('/kaipan/normalize', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
}

export function kaipanRun(payload: KaipanRunRequest) {
  return fetchJson<KaipanRunResponse>('/kaipan/run', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
}

export function kaipanStop() {
  return fetchJson<KaipanStopResponse>('/kaipan/stop', {
    method: 'POST',
  });
}
