import type { JobArtifactRef } from '@/types/jobs';

export function formatTimestamp(value: string | null | undefined) {
  if (!value) {
    return '未记录';
  }
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

export function formatBytes(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return '未记录';
  }
  if (!Number.isFinite(value)) {
    return '未记录';
  }
  if (value < 1024) {
    return `${Math.max(0, Math.round(value))} B`;
  }
  const kib = value / 1024;
  if (kib < 1024) {
    return `${kib.toFixed(1)} KiB`;
  }
  return `${(kib / 1024).toFixed(1)} MiB`;
}

export function maskAbsolutePath(value: string | null | undefined) {
  if (!value) {
    return '未记录';
  }
  if (value.startsWith('/') || /^[A-Za-z]:[\\/]/.test(value)) {
    return '[已隐藏路径]';
  }
  return value;
}

export function sanitizeForDisplay(value: unknown): unknown {
  if (typeof value === 'string') {
    return maskAbsolutePath(value);
  }
  if (Array.isArray(value)) {
    return value.map((item) => sanitizeForDisplay(item));
  }
  if (value && typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>);
    return Object.fromEntries(entries.map(([key, item]) => [key, sanitizeForDisplay(item)]));
  }
  return value;
}

export function stringifyJson(value: unknown) {
  if (value === null || value === undefined) {
    return '未记录';
  }
  const sanitized = sanitizeForDisplay(value);
  return JSON.stringify(sanitized, null, 2);
}

export function getVisibilityLabel(visibility: JobArtifactRef['visibility']) {
  if (visibility === 'public') {
    return '公开';
  }
  if (visibility === 'private') {
    return '受限';
  }
  return '内部';
}

export function buildArtifactPreviewPayload(artifact: JobArtifactRef) {
  return {
    artifact_id: artifact.artifact_id,
    job_id: artifact.job_id,
    workflow_id: artifact.workflow_id,
    step_id: artifact.step_id,
    kind: artifact.kind,
    title: artifact.title,
    summary: artifact.summary,
    created_at: artifact.created_at,
    size_bytes: artifact.size_bytes,
    visibility: artifact.visibility,
    metadata: artifact.metadata,
    storage_ref: artifact.storage_ref,
  };
}
