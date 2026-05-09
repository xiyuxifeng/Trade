import { API_KEY_STORAGE_KEY, fetchJson, getApiBaseUrl } from './http';
import type { ImportTradeLogsRequest, ImportTradeLogsResponse, MigrateCrawlStateRequest, MigrateCrawlStateResponse } from '@/types/imports';

export async function importTradeLogs(payload: ImportTradeLogsRequest) {
  const form = new FormData();
  form.append('file', payload.file);
  form.append('dry_run', String(payload.dryRun));
  if (payload.source) {
    form.append('source', payload.source);
  }

  const headers = new Headers();
  headers.set('Accept', 'application/json');
  if (typeof window !== 'undefined') {
    const apiKey = window.localStorage.getItem(API_KEY_STORAGE_KEY);
    if (apiKey) {
      headers.set('X-API-Key', apiKey);
    }
  }

  const response = await fetch(`${getApiBaseUrl()}/imports/trade-logs`, {
    method: 'POST',
    headers,
    body: form,
  });
  if (!response.ok) {
    throw new Error(response.statusText || 'trade log import failed');
  }
  return (await response.json()) as ImportTradeLogsResponse;
}

export function migrateCrawlState(payload: MigrateCrawlStateRequest) {
  return fetchJson<MigrateCrawlStateResponse>('/imports/crawl-state/migrate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
}
