import type { ApiErrorPayload } from '@/types/system';

const DEFAULT_API_BASE_URL = '/api/ui/v1';
const API_KEY_STORAGE_KEY = 'trade-strategy-ai.apiKey';
const AUTH_TOKEN_STORAGE_KEY = 'trade-strategy-ai.authToken';

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

/** 获取存储的会话认证令牌（不做客户端过期判断） */
export function getAuthToken(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }
  const token = window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
  return token || null;
}

/** 存储会话认证令牌 */
export function setAuthToken(token: string | null): void {
  if (typeof window === 'undefined') return;
  if (token) {
    window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
  } else {
    window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
  }
}

export function buildApiHeaders(headers?: HeadersInit) {
  const mergedHeaders = new Headers(headers);
  const apiKey = getStoredApiKey();
  if (apiKey) {
    mergedHeaders.set('X-API-Key', apiKey);
  }

  // 添加会话令牌（优先于 API Key）
  const authToken = getAuthToken();
  if (authToken) {
    mergedHeaders.set('X-Auth-Token', authToken);
  }

  return mergedHeaders;
}

type ApiResponseKind = 'json' | 'text' | 'blob';

export class ApiError extends Error {
  status: number;

  payload?: ApiErrorPayload;

  detail?: unknown;

  requestId?: string | null;

  constructor(status: number, message: string, payload?: ApiErrorPayload) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.payload = payload;
    this.detail = payload?.detail;
    this.requestId = typeof payload?.request_id === 'string' ? payload.request_id : null;
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

function resolveUrl(path: string, baseUrl: string) {
  return `${baseUrl}${path}`;
}

async function requestApi<T>(path: string, init: RequestInit | undefined, responseKind: ApiResponseKind, baseUrl: string): Promise<T> {
  const headers = buildApiHeaders(init?.headers);
  const method = init?.method?.toUpperCase() ?? 'GET';

  if (responseKind === 'json') {
    headers.set('Accept', 'application/json');
  } else if (responseKind === 'text') {
    headers.set('Accept', 'text/html, text/plain;q=0.9, */*;q=0.8');
  } else {
    headers.set('Accept', '*/*');
  }

  if (
    !headers.has('Content-Type') &&
    ['POST', 'PUT', 'PATCH'].includes(method) &&
    typeof init?.body === 'string'
  ) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(resolveUrl(path, baseUrl), {
    ...init,
    headers,
  });

  if (!response.ok) {
    const payload = await readErrorPayload(response);
    const detailMessage = typeof payload?.detail === 'string' ? payload.detail : undefined;
    throw new ApiError(response.status, detailMessage || payload?.message || response.statusText || 'Request failed', payload);
  }

  if (responseKind === 'json') {
    if (response.status === 204) {
      return undefined as T;
    }
    return (await response.json()) as T;
  }

  if (responseKind === 'text') {
    return (await response.text()) as T;
  }

  return (await response.blob()) as T;
}

export async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  return requestApi<T>(path, init, 'json', getApiBaseUrl());
}

export async function fetchText(path: string, init?: RequestInit): Promise<string> {
  return requestApi<string>(path, init, 'text', getApiBaseUrl());
}

export async function fetchBlob(path: string, init?: RequestInit): Promise<Blob> {
  return requestApi<Blob>(path, init, 'blob', getApiBaseUrl());
}

export async function fetchRootJson<T>(path: string, init?: RequestInit): Promise<T> {
  return requestApi<T>(path, init, 'json', '');
}

export async function fetchRootText(path: string, init?: RequestInit): Promise<string> {
  return requestApi<string>(path, init, 'text', '');
}

export async function fetchRootBlob(path: string, init?: RequestInit): Promise<Blob> {
  return requestApi<Blob>(path, init, 'blob', '');
}

export { API_KEY_STORAGE_KEY, getApiBaseUrl };
