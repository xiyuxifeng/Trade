import { fetchJson } from './http';
import type { OhlcvResponse, SymbolListResponse } from '@/types/market';

export function listSymbols(q?: string, limit = 200) {
  const params = new URLSearchParams();
  if (q) {
    params.set('q', q);
  }
  params.set('limit', String(limit));
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return fetchJson<SymbolListResponse>(`/market/symbols${suffix}`);
}

export function getOhlcv(symbol: string, startDate: string, endDate: string) {
  const params = new URLSearchParams({
    symbol,
    start_date: startDate,
    end_date: endDate,
  });
  return fetchJson<OhlcvResponse>(`/market/ohlcv?${params.toString()}`);
}
