import { Children, type ReactNode } from 'react';
import { Link } from 'react-router-dom';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

export type PageAvailability =
  | 'ready'
  | 'loading'
  | 'empty'
  | 'error'
  | 'partial'
  | 'permission_denied'
  | 'unavailable';

export type PageAction =
  | {
      label: string;
      to: string;
      onClick?: never;
    }
  | {
      label: string;
      onClick: () => void;
      to?: never;
    };

export type PagePrerequisite = {
  label: string;
  status: PageAvailability;
  detail?: string;
};

export type BusinessPageShellProps = {
  title: string;
  purpose: string;
  inputDescription: string;
  processingDescription: string;
  outputDescription: string;
  currentStep?: string;
  prerequisites?: PagePrerequisite[];
  availability?: PageAvailability;
  stateTitle?: string;
  stateDescription?: string;
  impact?: string;
  recoveryAction?: PageAction;
  nextAction?: PageAction;
  input?: ReactNode;
  progress?: ReactNode;
  output?: ReactNode;
  help?: ReactNode;
  children?: ReactNode;
  className?: string;
};

type StateCopy = {
  title: string;
  description: string;
  impact: string;
  recoveryAction: string;
};

const STATE_COPY: Record<Exclude<PageAvailability, 'ready'>, StateCopy> = {
  loading: {
    title: '正在加载',
    description: '页面内容正在获取中，请稍后再看。',
    impact: '你暂时还不能查看完整内容。',
    recoveryAction: '等待加载完成后刷新页面。',
  },
  empty: {
    title: '暂无内容',
    description: '当前没有可展示的业务内容。',
    impact: '这部分页面暂时不会给出结果。',
    recoveryAction: '补齐输入后重新查看。',
  },
  error: {
    title: '出现问题',
    description: '读取页面内容时发生了错误。',
    impact: '当前结果可能不完整或无法展示。',
    recoveryAction: '查看失败原因后重新处理。',
  },
  partial: {
    title: '部分完成',
    description: '已返回一部分内容，仍有项目未处理完。',
    impact: '你看到的是当前可用的部分结果。',
    recoveryAction: '补齐缺失部分后继续处理。',
  },
  permission_denied: {
    title: '无权限',
    description: '当前账号没有查看这部分内容的权限。',
    impact: '高风险操作不会显示。',
    recoveryAction: '切换到有权限的账号，或联系管理员。',
  },
  unavailable: {
    title: '当前不可用',
    description: '相关服务或数据暂时不可用。',
    impact: '暂时无法继续查看完整页面。',
    recoveryAction: '稍后重试，或先补齐缺失数据。',
  },
};

const actionClassName =
  'inline-flex items-center justify-center gap-2 rounded-lg border border-slate-200 bg-slate-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400/50';

function availabilityLabel(availability: PageAvailability) {
  return availability === 'ready' ? '已就绪' : STATE_COPY[availability].title;
}

function hasRenderableContent(children: ReactNode) {
  return Children.toArray(children).some((child) => child !== '');
}

function renderPageAction(action: PageAction) {
  if (action.to !== undefined) {
    return (
      <Link className={actionClassName} to={action.to}>
        {action.label}
      </Link>
    );
  }

  return (
    <Button onClick={action.onClick} variant="default">
      {action.label}
    </Button>
  );
}

function SectionCard({
  title,
  description,
  children,
  className,
}: {
  title: string;
  description: string;
  children?: ReactNode;
  className?: string;
}) {
  const hasContent = hasRenderableContent(children);

  return (
    <Card className={cn('border-slate-200/90 bg-white/95', className)}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      {hasContent ? (
        <CardContent className="grid gap-3" data-testid={`section-content-${title}`}>
          {children}
        </CardContent>
      ) : null}
    </Card>
  );
}

export function BusinessPageShell({
  title,
  purpose,
  inputDescription,
  processingDescription,
  outputDescription,
  currentStep,
  prerequisites,
  availability = 'ready',
  stateTitle,
  stateDescription,
  impact,
  recoveryAction,
  nextAction,
  input,
  progress,
  output,
  help,
  children,
  className,
}: BusinessPageShellProps) {
  const stateCopy = availability === 'ready' ? null : STATE_COPY[availability];
  const resolvedStateTitle = stateTitle ?? stateCopy?.title;
  const resolvedStateDescription = stateDescription ?? stateCopy?.description;
  const resolvedImpact = impact ?? stateCopy?.impact;
  const resolvedRecoveryText = stateCopy?.recoveryAction;
  const shouldShowNextAction = nextAction && (availability === 'ready' || availability === 'partial');

  return (
    <main className={cn('page-stack', className)}>
      <section className="page-card">
        <p className="page-kicker">正式业务页面</p>
        <h1>{title}</h1>
        <p className="hero-copy">{purpose}</p>
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <SectionCard title="页面用途" description={purpose} className="lg:col-span-2">
          {currentStep ? (
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
              <p className="m-0 text-sm font-medium text-slate-900">当前步骤</p>
              <p className="mt-1 text-sm text-slate-600">{currentStep}</p>
            </div>
          ) : null}
          {prerequisites ? (
            <div className="grid gap-3">
              {prerequisites.map((item) => (
                <div key={item.label} className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="m-0 text-sm font-medium text-slate-900">{item.label}</p>
                      {item.detail ? <p className="mt-1 text-sm text-slate-600">{item.detail}</p> : null}
                    </div>
                    <Badge variant={item.status === 'ready' ? 'success' : item.status === 'error' ? 'destructive' : item.status === 'partial' ? 'warning' : 'default'}>
                      {availabilityLabel(item.status)}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          ) : null}
        </SectionCard>

        <SectionCard title="输入" description={inputDescription}>
          {input ? <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">{input}</div> : null}
        </SectionCard>

        <SectionCard title="处理状态" description={processingDescription}>
          {availability === 'ready' ? (
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="m-0 text-sm font-medium text-emerald-900">已就绪</p>
                  <p className="mt-1 text-sm text-emerald-800">页面内容可以直接查看。</p>
                </div>
                <Badge variant="success">就绪</Badge>
              </div>
            </div>
          ) : (
            <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  {resolvedStateTitle ? <p className="m-0 text-sm font-medium text-amber-950">{resolvedStateTitle}</p> : null}
                  {resolvedStateDescription ? <p className="mt-1 text-sm text-amber-900">{resolvedStateDescription}</p> : null}
                </div>
                <Badge variant={availability === 'error' ? 'destructive' : availability === 'partial' ? 'warning' : 'default'}>
                  {resolvedStateTitle ?? '处理中'}
                </Badge>
              </div>
              {resolvedImpact ? (
                <div className="mt-3 rounded-xl bg-white/80 px-3 py-2 text-sm text-slate-700">
                  <span className="font-medium text-slate-900">影响：</span>
                  {resolvedImpact}
                </div>
              ) : null}
              {resolvedRecoveryText ? (
                <div className="mt-2 rounded-xl bg-white/80 px-3 py-2 text-sm text-slate-700">
                  <span className="font-medium text-slate-900">处理方式：</span>
                  <span className="ml-1">{resolvedRecoveryText}</span>
                </div>
              ) : null}
              {recoveryAction ? <div className="mt-3">{renderPageAction(recoveryAction)}</div> : null}
            </div>
          )}
          {progress ? <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">{progress}</div> : null}
        </SectionCard>

        <SectionCard title="输出" description={outputDescription}>
          {output ? <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">{output}</div> : null}
        </SectionCard>

        <SectionCard title="下一步" description="请选择下一项业务动作。">
          {shouldShowNextAction ? (
            <div>{renderPageAction(nextAction)}</div>
          ) : null}
          {help ? <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">{help}</div> : null}
          {!shouldShowNextAction && !help ? (
            <p className="m-0 text-sm text-slate-600">当前没有可执行的下一步操作。</p>
          ) : null}
        </SectionCard>

        {children ? <div className="lg:col-span-2">{children}</div> : null}
      </div>
    </main>
  );
}
