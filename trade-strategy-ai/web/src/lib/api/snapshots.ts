import { fetchJson } from './http';
import type { SnapshotDetailResponse, SnapshotListResponse, SnapshotType } from '@/types/snapshots';

type SnapshotQuery = {
  date_start: string;
  date_end: string;
  type?: SnapshotType | '';
  skip?: number;
  limit?: number;
};

export function listSnapshots(query: SnapshotQuery) {
  const params = new URLSearchParams({
    date_start: query.date_start,
    date_end: query.date_end,
  });
  if (query.type) {
    params.set('type', query.type);
  }
  if (query.skip !== undefined) {
    params.set('skip', String(query.skip));
  }
  if (query.limit !== undefined) {
    params.set('limit', String(query.limit));
  }
  return fetchJson<SnapshotListResponse>(`/snapshots?${params.toString()}`);
}

export function getSnapshot(snapshotId: string) {
  return fetchJson<SnapshotDetailResponse>(`/snapshots/${snapshotId}`);
}
