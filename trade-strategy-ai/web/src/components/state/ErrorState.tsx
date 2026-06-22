import { type ReactNode, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@/features/auth/auth-context';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { ErrorRecoveryAction, ErrorRecoveryCategory } from '@/lib/error-recovery';

type ErrorStateProps = {
  category: ErrorRecoveryCategory;
  title: string;
  description: string;
  suggestion: string;
  happened?: string;
  affected?: string;
  repairGuidance?: string;
  detail?: string;
  retryLabel?: string;
  onRetry?: () => void;
  actions?: ErrorRecoveryAction[];
  children?: ReactNode;
  className?: string;
};

const CATEGORY_LABELS: Record<ErrorRecoveryCategory, string> = {
  'validation error': '输入不符合要求',
  'permission denied': '权限受限',
  'config missing': '必要配置缺失',
  'provider unavailable': '服务暂不可用',
  'data empty': '暂无可用结果',
  'artifact missing': '结果暂不可用',
  'job failed': '处理未完成',
  'network error': '网络请求失败',
};

const CATEGORY_IMPACTS: Record<ErrorRecoveryCategory, string> = {
  'validation error': '当前提交不会生效，需要先修正输入后再继续。',
  'permission denied': '当前账号无法继续查看或执行相关操作。',
  'config missing': '依赖配置未准备好，当前页面结果不能视为正式可用。',
  'provider unavailable': '本页依赖的服务暂时无法返回完整结果。',
  'data empty': '当前不会显示正式结果，需要等待记录生成或调整筛选条件。',
  'artifact missing': '相关结果材料暂时无法查看，后续判断会受限。',
  'job failed': '本次处理结果可能缺失或不完整，相关业务步骤暂时不能继续。',
  'network error': '当前页面没有拿到完整响应，显示结果不能作为正式依据。',
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
  happened,
  affected,
  repairGuidance,
  detail,
  retryLabel = '重试',
  onRetry,
  actions = [],
  children,
  className,
}: ErrorStateProps) {
  const [showDetail, setShowDetail] = useState(false);
  const { canAccess } = useAuth();
  const canViewDiagnostics = Boolean(detail) && canAccess('operator');
  const happenedText = happened ?? description;
  const affectedText = affected ?? CATEGORY_IMPACTS[category];
  const repairText = repairGuidance ?? suggestion;

  return (
    <section className={cn('rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm', className)}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-3xl">
          <Badge variant="info">错误恢复</Badge>
          <h2 className="mt-3 text-2xl font-semibold tracking-tight text-slate-950">{title}</h2>
        </div>
        <Badge variant="warning" className="shrink-0">
          {CATEGORY_LABELS[category]}
        </Badge>
      </div>

      <div className="mt-6 grid gap-3">
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">发生了什么</p>
          <p className="mt-2 text-sm leading-6 text-slate-700">{happenedText}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">影响什么</p>
          <p className="mt-2 text-sm leading-6 text-slate-700">{affectedText}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">应该怎么处理</p>
          <p className="mt-2 text-sm leading-6 text-slate-700">{repairText}</p>
        </div>
      </div>

      {children ? <div className="mt-6">{children}</div> : null}

      {canViewDiagnostics ? (
        <div className="mt-6">
          <button
            className="text-sm font-medium text-slate-700 hover:text-slate-950"
            onClick={() => setShowDetail((current) => !current)}
            type="button"
          >
            {showDetail ? '收起运维诊断详情' : '查看运维诊断详情'}
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
