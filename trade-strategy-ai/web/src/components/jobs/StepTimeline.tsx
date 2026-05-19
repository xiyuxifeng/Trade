import { useMemo, useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { StepTimelineItem, StepTimelineStatus } from '@/types/job';

type StepTimelineProps = {
  items: StepTimelineItem[];
  emptyLabel?: string;
};

function getStatusLabel(status: StepTimelineStatus) {
  const mapping: Record<StepTimelineStatus, string> = {
    pending: '等待中',
    running: '运行中',
    success: '成功',
    failed: '失败',
    cancelled: '已取消',
    skipped: '已跳过',
  };
  return mapping[status];
}

function statusVariant(status: StepTimelineStatus) {
  if (status === 'success') return 'success';
  if (status === 'failed' || status === 'cancelled') return 'destructive';
  if (status === 'running') return 'info';
  return 'warning';
}

function formatTimestamp(value: string | null | undefined) {
  if (!value) {
    return '未记录';
  }
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function formatDuration(durationMs: number | null | undefined) {
  if (durationMs === null || durationMs === undefined) {
    return '未记录';
  }
  if (!Number.isFinite(durationMs)) {
    return '未记录';
  }

  if (durationMs < 1000) {
    return `${Math.max(0, Math.round(durationMs))} ms`;
  }

  const totalSeconds = Math.max(0, Math.round(durationMs / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes === 0) {
    return `${seconds} 秒`;
  }
  if (seconds === 0) {
    return `${minutes} 分钟`;
  }
  return `${minutes} 分钟 ${seconds} 秒`;
}

function stringifyDetails(details: StepTimelineItem['details']) {
  if (details === null || details === undefined) {
    return '未提供详情';
  }
  if (typeof details === 'string') {
    return details.trim() || '未提供详情';
  }
  return JSON.stringify(details, null, 2);
}

function timelineSummary(item: StepTimelineItem) {
  const startedAt = formatTimestamp(item.startedAt);
  const finishedAt = formatTimestamp(item.finishedAt);
  const duration = item.durationMs !== null && item.durationMs !== undefined
    ? formatDuration(item.durationMs)
    : item.startedAt && item.finishedAt
      ? formatDuration(new Date(item.finishedAt).getTime() - new Date(item.startedAt).getTime())
      : '未记录';

  return `${startedAt} · ${finishedAt} · ${duration}`;
}

export function StepTimeline({ items, emptyLabel = '暂无步骤时间线' }: StepTimelineProps) {
  const [expandedIds, setExpandedIds] = useState<string[]>([]);

  const orderedItems = useMemo(() => {
    return items
      .map((item, index) => ({
        item,
        sortKey: item.order ?? index,
      }))
      .sort((left, right) => left.sortKey - right.sortKey)
      .map(({ item }) => item);
  }, [items]);

  if (!orderedItems.length) {
    return <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">{emptyLabel}</div>;
  }

  function toggleExpanded(itemId: string) {
    setExpandedIds((current) =>
      current.includes(itemId)
        ? current.filter((id) => id !== itemId)
        : [...current, itemId],
    );
  }

  return (
    <div className="space-y-3">
      {orderedItems.map((item) => {
        const isExpanded = expandedIds.includes(item.id);
        const summary = timelineSummary(item);

        return (
          <div key={item.id} className="rounded-2xl border border-slate-200 bg-white p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <button
                type="button"
                className="flex min-w-0 flex-1 items-start gap-3 text-left"
                aria-expanded={isExpanded}
                aria-label={isExpanded ? '收起步骤详情' : '展开步骤详情'}
                onClick={() => toggleExpanded(item.id)}
              >
                <span
                  className={cn(
                    'mt-1 size-2.5 shrink-0 rounded-full',
                    item.status === 'success' && 'bg-emerald-400',
                    item.status === 'running' && 'bg-sky-400',
                    item.status === 'failed' && 'bg-rose-400',
                    item.status === 'cancelled' && 'bg-slate-400',
                    item.status === 'pending' && 'bg-amber-400',
                    item.status === 'skipped' && 'bg-violet-400',
                  )}
                />
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="truncate font-medium text-slate-900">{item.title ?? item.stepName}</p>
                    <Badge variant={statusVariant(item.status)}>{getStatusLabel(item.status)}</Badge>
                  </div>
                  <p className="mt-1 break-all text-xs text-slate-500">
                    {item.stepName}
                    {item.metadata?.['source'] ? ` · ${String(item.metadata['source'])}` : ''}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">{summary}</p>
                </div>
              </button>

              <button
                type="button"
                className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-transparent text-slate-700 transition-colors hover:bg-slate-100"
                aria-label={isExpanded ? '收起步骤详情' : '展开步骤详情'}
                onClick={() => toggleExpanded(item.id)}
              >
                {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </button>
            </div>

            {isExpanded ? (
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">开始时间</p>
                  <p className="mt-1 text-sm text-slate-900">{formatTimestamp(item.startedAt)}</p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">完成时间</p>
                  <p className="mt-1 text-sm text-slate-900">{formatTimestamp(item.finishedAt)}</p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">耗时</p>
                  <p className="mt-1 text-sm text-slate-900">{formatDuration(item.durationMs)}</p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">错误摘要</p>
                  <p className={cn('mt-1 text-sm', item.errorSummary ? 'text-rose-600' : 'text-slate-900')}>
                    {item.errorSummary ?? '未提供'}
                  </p>
                </div>
                <div className="md:col-span-2">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">详情</p>
                  <pre className="mt-2 max-h-60 overflow-auto rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-800">
                    {stringifyDetails(item.details)}
                  </pre>
                </div>
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
