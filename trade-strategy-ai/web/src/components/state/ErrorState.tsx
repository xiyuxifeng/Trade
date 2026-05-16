import { type ReactNode, useState } from 'react';
import { Link } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { ErrorRecoveryAction, ErrorRecoveryCategory } from '@/lib/error-recovery';

type ErrorStateProps = {
  category: ErrorRecoveryCategory;
  title: string;
  description: string;
  suggestion: string;
  detail?: string;
  retryLabel?: string;
  onRetry?: () => void;
  actions?: ErrorRecoveryAction[];
  children?: ReactNode;
  className?: string;
};

function actionBaseClass(variant: 'primary' | 'secondary') {
  return cn(
    'inline-flex h-10 items-center justify-center rounded-lg border px-4 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400/30',
    variant === 'primary'
      ? 'border-sky-200 bg-sky-500 text-slate-950 hover:bg-sky-400'
      : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50',
  );
}

export function ErrorState({
  category,
  title,
  description,
  suggestion,
  detail,
  retryLabel = '重试',
  onRetry,
  actions = [],
  children,
  className,
}: ErrorStateProps) {
  const [showDetail, setShowDetail] = useState(false);

  return (
    <section className={cn('rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm', className)}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-3xl">
          <Badge variant="info">错误恢复</Badge>
          <h2 className="mt-3 text-2xl font-semibold tracking-tight text-slate-950">{title}</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">{description}</p>
        </div>
        <Badge variant="warning" className="shrink-0">
          {category}
        </Badge>
      </div>

      <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-4">
        <p className="text-xs uppercase tracking-[0.16em] text-slate-500">下一步建议</p>
        <p className="mt-2 text-sm leading-6 text-slate-700">{suggestion}</p>
      </div>

      {children ? <div className="mt-6">{children}</div> : null}

      {detail ? (
        <div className="mt-6">
          <button
            className="text-sm font-medium text-slate-700 hover:text-slate-950"
            onClick={() => setShowDetail((current) => !current)}
            type="button"
          >
            {showDetail ? '收起技术详情' : '查看技术详情'}
          </button>
          {showDetail ? (
            <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap break-words rounded-2xl border border-slate-200 bg-slate-50 p-4 text-xs leading-6 text-slate-700">
              {detail}
            </pre>
          ) : null}
        </div>
      ) : null}

      <div className="mt-6 flex flex-wrap gap-3">
        {onRetry ? (
          <button
            className={actionBaseClass('primary')}
            onClick={onRetry}
            type="button"
          >
            {retryLabel}
          </button>
        ) : null}
        {actions.map((action, index) => (
          <Link
            key={`${action.to}-${index}`}
            className={actionBaseClass(index === 0 && !onRetry ? 'primary' : 'secondary')}
            to={action.to}
          >
            {action.label}
          </Link>
        ))}
      </div>
    </section>
  );
}
