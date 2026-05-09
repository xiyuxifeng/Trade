import type { ApiErrorPayload } from '@/types/system';

const DEFAULT_API_BASE_URL = '/api/ui/v1';
const API_KEY_STORAGE_KEY = 'trade-strategy-ai.apiKey';

function getApiBaseUrl() {
  const baseUrl = import.meta.env.VITE_API_BASE_URL as string | undefined;
  return baseUrl?.trim() || DEFAULT_API_BASE_URL;
}

function getStoredApiKey() {
  if (typeof window === 'undefined') {
    return null;
  }

  return window.localStorage.getItem(API_KEY_STORAGE_KEY);
}

function buildHeaders(headers?: HeadersInit) {
  const mergedHeaders = new Headers(headers);
  mergedHeaders.set('Accept', 'application/json');

  const apiKey = getStoredApiKey();
  if (apiKey) {
    mergedHeaders.set('X-API-Key', apiKey);
  }

  return mergedHeaders;
}

export class ApiError extends Error {
  status: number;

  payload?: ApiErrorPayload;

  constructor(status: number, message: string, payload?: ApiErrorPayload) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.payload = payload;
  }
}

async function readErrorPayload(response: Response): Promise<ApiErrorPayload | undefined> {
  const contentType = response.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) {
    return undefined;
  }

  try {
    return (await response.json()) as ApiErrorPayload;
  } catch {
    return undefined;
  }
}

export async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    headers: buildHeaders(init?.headers),
  });

  if (!response.ok) {
    const payload = await readErrorPayload(response);
    throw new ApiError(
      response.status,
      payload?.detail || payload?.message || response.statusText || 'Request failed',
      payload,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export { API_KEY_STORAGE_KEY, getApiBaseUrl };
