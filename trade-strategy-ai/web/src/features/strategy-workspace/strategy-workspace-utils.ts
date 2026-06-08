import { ApiError } from '@/lib/api/http';
import type { ProfileDetailResponse, ProfileSnapshotRecord } from '@/types/profile';

export const STRATEGY_WORKSPACE_JOB_TYPES = ['snapshot-build', 'strategy-build', 'run-pre-market', 'run-after-close'] as const;
export type StrategyWorkspaceJobType = (typeof STRATEGY_WORKSPACE_JOB_TYPES)[number];

const STRATEGY_WORKSPACE_JOB_LABELS: Record<StrategyWorkspaceJobType, string> = {
  'snapshot-build': '市场上下文准备',
  'strategy-build': '规则版本构建',
  'run-pre-market': '盘前分析',
  'run-after-close': '盘后复盘',
};

export function isStrategyWorkspaceJobType(jobType: string): jobType is StrategyWorkspaceJobType {
  return (STRATEGY_WORKSPACE_JOB_TYPES as readonly string[]).includes(jobType);
}

export function describeStrategyWorkspaceJobType(jobType: string) {
  return isStrategyWorkspaceJobType(jobType) ? STRATEGY_WORKSPACE_JOB_LABELS[jobType] : jobType;
}

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
    if (error.status === 401 || error.status === 403) {
      return '当前账号没有权限执行该操作。';
    }
    if (error.status === 404) {
      return '未找到相关数据，请返回上一页重新选择。';
    }
    if (error.status >= 500) {
      return fallback;
    }
    return fallback;
  }

  if (error instanceof Error) {
    return fallback;
  }

  return fallback;
}

export function isWorkspacePermissionDenied(error: unknown) {
  return error instanceof ApiError && (error.status === 401 || error.status === 403);
}
