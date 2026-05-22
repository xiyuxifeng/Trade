import { ApiError } from '@/lib/api/http';
import type { ProfileDetailResponse, ProfileSnapshotRecord } from '@/types/profile';

export function sortSnapshotsByCapturedAt(snapshots: ProfileSnapshotRecord[]) {
  return [...snapshots].sort((left, right) => right.captured_at.localeCompare(left.captured_at));
}

export function selectLatestProfileSnapshot(detail: ProfileDetailResponse | null) {
  return sortSnapshotsByCapturedAt(detail?.snapshots ?? [])[0] ?? null;
}

export function formatWorkspaceTimestamp(value: string | null | undefined) {
  if (!value) {
    return '未记录';
  }

  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

export function getWorkspaceErrorMessage(error: unknown, fallback: string) {
  if (error instanceof ApiError) {
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return fallback;
}

export function isWorkspacePermissionDenied(error: unknown) {
  return error instanceof ApiError && (error.status === 401 || error.status === 403);
}
