import { Children, useId, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ChevronDown, ChevronUp } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export type PageAvailability =
  | 'ready'
  | 'loading'
  | 'empty'
  | 'error'
  | 'partial'
  | 'degraded'
  | 'invalid'
  | 'conflict'
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

export type PageLayoutMode = 'workflow' | 'overview' | 'management' | 'detail' | 'library';

export type BusinessPageShellProps = {
  title: string;
  purpose: string;
  inputDescription: string;
  processingDescription: string;
  outputDescription: string;
  layoutMode?: PageLayoutMode;
  showInputSection?: boolean;
  showProcessingSection?: boolean;
  showOutputSection?: boolean;
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
  degraded: {
    title: '已降级',
    description: '系统以受限方式返回结果，部分正式能力暂时不可用。',
    impact: '当前结果只能作为受限参考，不能当成完整正式结果。',
    recoveryAction: '先查看受限原因，再补齐缺失依赖或联系管理员处理。',
  },
  invalid: {
    title: '状态无效',
    description: '当前正式数据或页面状态未通过有效性检查。',
    impact: '继续操作可能导致错误判断，当前流程不能直接继续。',
    recoveryAction: '先修复无效状态，再重新进入当前页面。',
  },
  conflict: {
    title: '数据冲突',
    description: '页面依赖的正式数据之间出现冲突。',
    impact: '当前结果无法作为唯一依据，相关业务步骤需要暂停。',
    recoveryAction: '先确认冲突来源并完成修复，再继续后续操作。',
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
  'inline-flex h-8 whitespace-nowrap items-center justify-center gap-2 rounded-lg border border-slate-200 bg-slate-900 px-3 text-sm font-medium text-white transition-colors hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400/50';

const LAYOUT_SECTION_DEFAULTS: Record<PageLayoutMode, { input: boolean; processing: boolean; output: boolean }> = {
  workflow: { input: true, processing: true, output: true },
  overview: { input: false, processing: false, output: true },
  management: { input: false, processing: false, output: true },
  detail: { input: false, processing: false, output: true },
  library: { input: false, processing: false, output: true },
};

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
    <Button onClick={action.onClick} type="button" variant="default" size="sm">
      {action.label}
    </Button>
  );
}

function resolveSectionVisibility({
  layoutMode = 'workflow',
  showInputSection,
  showProcessingSection,
  showOutputSection,
}: Pick<BusinessPageShellProps, 'layoutMode' | 'showInputSection' | 'showProcessingSection' | 'showOutputSection'>) {
  const defaults = LAYOUT_SECTION_DEFAULTS[layoutMode];

  return {
    showInputSection: showInputSection ?? defaults.input,
    showProcessingSection: showProcessingSection ?? defaults.processing,
    showOutputSection: showOutputSection ?? defaults.output,
  };
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
    <section className={cn('rounded-2xl border border-slate-200/90 bg-white/95 shadow-[0_18px_40px_rgba(15,23,42,0.08)] backdrop-blur', className)}>
      <div className="flex flex-col gap-1.5 p-6">
        <h2 className="text-lg font-semibold leading-none tracking-tight">{title}</h2>
        <p className="text-sm text-slate-600">{description}</p>
      </div>
      {hasContent ? (
        <div className="grid gap-3 px-6 pb-6 pt-0" data-testid={`section-content-${title}`}>
          {children}
        </div>
      ) : null}
    </section>
  );
}

function AvailabilityPanel({
  availability,
  resolvedStateTitle,
  resolvedStateDescription,
  resolvedImpact,
  resolvedRecoveryText,
  recoveryAction,
}: {
  availability: PageAvailability;
  resolvedStateTitle?: string;
  resolvedStateDescription?: string;
  resolvedImpact?: string;
  resolvedRecoveryText?: string;
  recoveryAction?: PageAction;
}) {
  if (availability === 'ready') {
    return (
      <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="m-0 text-sm font-medium text-emerald-900">已就绪</p>
            <p className="mt-1 text-sm text-emerald-800">页面内容可以直接查看。</p>
          </div>
          <Badge variant="success">就绪</Badge>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 space-y-2">
          <div>
            <p className="m-0 text-xs font-medium uppercase tracking-[0.16em] text-amber-900">发生了什么</p>
            {resolvedStateTitle ? <p className="mt-1 text-sm font-medium text-amber-950">{resolvedStateTitle}</p> : null}
            {resolvedStateDescription ? <p className="mt-1 text-sm text-amber-900">{resolvedStateDescription}</p> : null}
          </div>
        </div>
        <Badge
          variant={
            availability === 'error' || availability === 'invalid' || availability === 'conflict'
              ? 'destructive'
              : availability === 'partial' || availability === 'degraded'
                ? 'warning'
                : 'default'
          }
        >
          {resolvedStateTitle ?? '处理中'}
        </Badge>
      </div>
      {resolvedImpact ? (
        <div className="mt-3 rounded-xl bg-white/80 px-3 py-2 text-sm text-slate-700">
          <span className="font-medium text-slate-900">影响什么：</span>
          {resolvedImpact}
        </div>
      ) : null}
      {resolvedRecoveryText ? (
        <div className="mt-2 rounded-xl bg-white/80 px-3 py-2 text-sm text-slate-700">
          <span className="font-medium text-slate-900">应该怎么处理：</span>
          <span className="ml-1">{resolvedRecoveryText}</span>
        </div>
      ) : null}
      {recoveryAction ? <div className="mt-3">{renderPageAction(recoveryAction)}</div> : null}
    </div>
  );
}

export function BusinessPageShell({
  title,
  purpose,
  inputDescription,
  processingDescription,
  outputDescription,
  layoutMode = 'workflow',
  showInputSection,
  showProcessingSection,
  showOutputSection,
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
  const nextActionPanelId = useId();
  const [isNextActionExpanded, setIsNextActionExpanded] = useState(false);
  const stateCopy = availability === 'ready' ? null : STATE_COPY[availability];
  const resolvedStateTitle = stateTitle ?? stateCopy?.title;
  const resolvedStateDescription = stateDescription ?? stateCopy?.description;
  const resolvedImpact = impact ?? stateCopy?.impact;
  const resolvedRecoveryText = stateCopy?.recoveryAction;
  const shouldShowNextAction = nextAction && (availability === 'ready' || availability === 'partial' || availability === 'degraded');
  const hasNextActionDetails = hasRenderableContent(help);
  const sectionVisibility = resolveSectionVisibility({
    layoutMode,
    showInputSection,
    showProcessingSection,
    showOutputSection,
  });
  const inlineAvailabilityInPurpose = !sectionVisibility.showProcessingSection && (availability !== 'ready' || progress);
  const progressPanel = progress ? <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">{progress}</div> : null;

  return (
    <main className={cn('page-stack', shouldShowNextAction && 'pb-36 md:pb-32', className)}>
      <h1 className="sr-only">{title}</h1>

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
                    <Badge
                      variant={
                        item.status === 'ready'
                          ? 'success'
                          : item.status === 'error' || item.status === 'invalid' || item.status === 'conflict'
                            ? 'destructive'
                            : item.status === 'partial' || item.status === 'degraded'
                              ? 'warning'
                              : 'default'
                      }
                    >
                      {availabilityLabel(item.status)}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          ) : null}
          {inlineAvailabilityInPurpose ? (
            <AvailabilityPanel
              availability={availability}
              resolvedStateTitle={resolvedStateTitle}
              resolvedStateDescription={resolvedStateDescription}
              resolvedImpact={resolvedImpact}
              resolvedRecoveryText={resolvedRecoveryText}
              recoveryAction={recoveryAction}
            />
          ) : null}
          {inlineAvailabilityInPurpose ? progressPanel : null}
        </SectionCard>

        {sectionVisibility.showInputSection ? (
          <SectionCard title="输入" description={inputDescription}>
            {input ? <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">{input}</div> : null}
          </SectionCard>
        ) : null}

        {sectionVisibility.showProcessingSection ? (
          <SectionCard title="处理状态" description={processingDescription}>
            <AvailabilityPanel
              availability={availability}
              resolvedStateTitle={resolvedStateTitle}
              resolvedStateDescription={resolvedStateDescription}
              resolvedImpact={resolvedImpact}
              resolvedRecoveryText={resolvedRecoveryText}
              recoveryAction={recoveryAction}
            />
            {progressPanel}
          </SectionCard>
        ) : null}

        {sectionVisibility.showOutputSection ? (
          <SectionCard title="输出" description={outputDescription} className="lg:col-span-2">
            {output ? <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">{output}</div> : null}
          </SectionCard>
        ) : null}

        {children ? <div className="lg:col-span-2">{children}</div> : null}
      </div>

      {shouldShowNextAction ? (
        <div className="pointer-events-none fixed bottom-[calc(0.75rem+env(safe-area-inset-bottom))] left-4 right-4 z-30 md:bottom-[calc(1rem+env(safe-area-inset-bottom))] md:left-[calc(var(--dashboard-sidebar-width,0px)+24px)] md:right-6">
          <div className="pointer-events-auto overflow-hidden rounded-2xl border border-slate-200/90 bg-white/95 shadow-[0_18px_40px_rgba(15,23,42,0.12)] backdrop-blur">
            <div className="flex min-h-[64px] items-center gap-3 px-4 py-3 md:min-h-[56px]">
              <div className="min-w-0 flex-1">
                <p className="m-0 text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">下一步</p>
                {hasNextActionDetails ? (
                  <div className="mt-1 hidden max-w-full overflow-hidden text-ellipsis whitespace-nowrap text-sm text-slate-600 md:block">
                    {help}
                  </div>
                ) : null}
              </div>
              <div className="flex shrink-0 items-center gap-2">
                {renderPageAction(nextAction)}
                {hasNextActionDetails ? (
                  <Button
                    aria-controls={nextActionPanelId}
                    aria-expanded={isNextActionExpanded}
                    aria-label={isNextActionExpanded ? '收起更多信息' : '展开更多信息'}
                    onClick={() => setIsNextActionExpanded((current) => !current)}
                    type="button"
                    variant="outline"
                    size="sm"
                  >
                    {isNextActionExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    <span>{isNextActionExpanded ? '收起' : '更多信息'}</span>
                  </Button>
                ) : null}
              </div>
            </div>
            {isNextActionExpanded && hasNextActionDetails ? (
              <div
                aria-label="下一步详情"
                className="max-h-[50vh] overflow-y-auto border-t border-slate-200/80 px-4 py-3 text-sm text-slate-700 md:max-h-[40vh]"
                id={nextActionPanelId}
              >
                {help}
              </div>
            ) : null}
          </div>
        </div>
      ) : null}
    </main>
  );
}
