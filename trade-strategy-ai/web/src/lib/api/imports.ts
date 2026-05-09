import { fetchJson } from './http';
import type { ImportTradeLogsRequest, ImportTradeLogsResponse, MigrateCrawlStateRequest, MigrateCrawlStateResponse } from '@/types/imports';

export async function importTradeLogs(payload: ImportTradeLogsRequest) {
  const form = new FormData();
  form.append('file', payload.file);
  form.append('dry_run', String(payload.dryRun));
  if (payload.source) {
    form.append('source', payload.source);
  }

  return fetchJson<ImportTradeLogsResponse>('/imports/trade-logs', {
    method: 'POST',
    body: form,
  });
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
