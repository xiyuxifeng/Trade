import type { ApiErrorPayload } from '@/types/system';

const DEFAULT_API_BASE_URL = '/api/ui/v1';
const API_KEY_STORAGE_KEY = 'trade-strategy-ai.apiKey';
const AUTH_TOKEN_STORAGE_KEY = 'trade-strategy-ai.authToken';
const AUTH_TOKEN_EXPIRY_KEY = 'trade-strategy-ai.authTokenExpiry';

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

/** 获取存储的会话认证令牌（自动检查过期） */
export function getAuthToken(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }
  const token = window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
  if (!token) return null;

  // 检查客户端过期时间
  const expiresAt = window.localStorage.getItem(AUTH_TOKEN_EXPIRY_KEY);
  if (expiresAt) {
    if (Date.now() > new Date(expiresAt).getTime()) {
      // Token 已过期，清理存储
      window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
      window.localStorage.removeItem(AUTH_TOKEN_EXPIRY_KEY);
      return null;
    }
  }
  return token;
}

/** 存储会话认证令牌及过期时间 */
export function setAuthToken(token: string | null, expiresAt?: string): void {
  if (typeof window === 'undefined') return;
  if (token) {
    window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
    if (expiresAt) {
      window.localStorage.setItem(AUTH_TOKEN_EXPIRY_KEY, expiresAt);
    }
  } else {
    window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
    window.localStorage.removeItem(AUTH_TOKEN_EXPIRY_KEY);
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
  const headers = buildApiHeaders(init?.headers);
  headers.set('Accept', 'application/json');
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    headers,
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
