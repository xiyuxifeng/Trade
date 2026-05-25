import type { HTMLAttributes } from 'react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { JobProgress as JobProgressRecord } from '@/types/jobs';

function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '0%';
  }
  return `${Math.max(0, Math.min(100, value)).toFixed(value % 1 === 0 ? 0 : 2)}%`;
}

function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return '未记录';
  }
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function stepLabel(progress: JobProgressRecord) {
  if (progress.current_step) {
    return progress.current_step;
  }
  if (progress.current_dataset) {
    return `${progress.stage}:${progress.current_dataset}`;
  }
  if (progress.current_fetcher) {
    return `${progress.stage}:${progress.current_fetcher}`;
  }
  return progress.stage || '未知进度';
}

function statusLabel(status: string | null | undefined) {
  if (!status) {
    return '进行中';
  }
  const mapping: Record<string, string> = {
    success: '正常',
    partial: '部分完成',
    error: '异常',
    missing: '缺失',
    running: '运行中',
  };
  return mapping[status] ?? status;
}

export function JobProgress({
  progress,
  compact = false,
  className,
}: {
  progress: JobProgressRecord;
  compact?: boolean;
  className?: HTMLAttributes<HTMLDivElement>['className'];
}) {
  const percent = Math.max(0, Math.min(100, Number(progress.percent) || 0));
  const mainLine = `${progress.current} / ${progress.total} · ${formatPercent(percent)}`;
  const subLine =
    progress.sub_total !== undefined && progress.sub_total !== null
      ? `子进度 ${progress.sub_current ?? 0} / ${progress.sub_total} · ${formatPercent(progress.sub_percent)}`
      : null;
  const metaLine = [progress.current_trade_date, progress.current_slot, progress.current_fetcher, progress.current_dataset]
    .filter(Boolean)
    .join(' · ');
  const badgeVariant: 'default' | 'success' | 'warning' | 'destructive' | 'info' =
    progress.status === 'error'
      ? 'destructive'
      : progress.status === 'missing'
        ? 'warning'
        : progress.status === 'partial'
          ? 'warning'
        : progress.status === 'success'
          ? 'success'
          : 'info';

  return (
    <div className={cn('space-y-2', className)}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className={cn('font-medium text-slate-900', compact ? 'text-sm' : 'text-base')}>{stepLabel(progress)}</p>
          <p className={cn('mt-1 text-slate-500', compact ? 'text-xs' : 'text-sm')}>{metaLine || '未记录日期 / slot'}</p>
        </div>
        <Badge variant={badgeVariant}>{statusLabel(progress.status)}</Badge>
      </div>

      <div className="h-2 overflow-hidden rounded-full bg-slate-200">
        <div className="h-full rounded-full bg-sky-500 transition-[width] duration-300 ease-out" style={{ width: `${percent}%` }} />
      </div>

      <div className={cn('flex flex-wrap items-center gap-x-3 gap-y-1 text-slate-600', compact ? 'text-xs' : 'text-sm')}>
        <span>{mainLine}</span>
        <span>剩余 {progress.remaining}</span>
        <span>更新时间 {formatDateTime(progress.updated_at)}</span>
      </div>
      {subLine ? <p className={cn('text-slate-500', compact ? 'text-xs' : 'text-sm')}>{subLine}</p> : null}

      {progress.error ? (
        <p className={cn('text-rose-600', compact ? 'text-xs' : 'text-sm')}>
          {progress.error}
        </p>
      ) : null}
    </div>
  );
}
