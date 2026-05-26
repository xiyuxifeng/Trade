import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ExternalLink, RefreshCw } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { PageHeader } from '@/components/layout/page-header';
import { Select } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { EmptyState, ErrorState, JsonViewer, LoadingState, SectionCard, StatusBadge } from '@/components/kit';
import { ApiError } from '@/lib/api/http';
import { listArticleFilterOptions, listArticles } from '@/lib/api/articles';
import { listJobs } from '@/lib/api/jobs';
import { listProfiles } from '@/lib/api/profiles';
import {
  getArticlePipeline,
  getArticlePipelineScheduleStatus,
  runArticlePipeline,
  runArticlePipelineStep,
  startArticlePipelineSchedule,
  stopArticlePipelineSchedule,
} from '@/lib/api/pipelines';
import type { ArticleFilterOptionsResponse, ArticleListResponse, ArticleRecord } from '@/types/articles';
import type { JobRecord, JobsListResponse } from '@/types/jobs';
import type { ProfileListResponse, ProfileRecord } from '@/types/profile';
import type { ArticlePipelineRunParams, ArticlePipelineScheduleState, PipelineDetailResponse } from '@/types/pipeline';
import type { WorkflowParamField, WorkflowStep } from '@/types/workflows';

type ArticleJobsResponse = JobsListResponse;
type MaintenanceMode = 'normal' | 'rebuild_pending' | 'retry_failed' | 'cleanup';
type StepParamKey = 'force' | 'skip_crawl' | 'use_db' | 'max_articles' | 'new_version';
type WorkflowRunResult = {
  workflow_id?: unknown;
  workflow_params?: Record<string, unknown> | null;
  run_context?: {
    status?: unknown;
    duration_ms?: unknown;
  } | Record<string, unknown> | null;
  step_results?: unknown[];
};
type JobResultPayload = {
  workflow_run?: WorkflowRunResult | null;
};

const workspaceSections = [
  {
    title: '抓取与处理',
    description: '文章处理全链路。',
    purpose: '从 Profile 触发文章抓取、清洗、校验、入库和结果回看的一条完整流程。',
    path: '/articles/run',
  },
  {
    title: '文章列表',
    description: '文章浏览与筛选。',
    purpose: '按作者、来源、交易者和日期浏览已抓取文章。',
    path: '/articles/list',
  },
  {
    title: '数据质量',
    description: '文章数据质量概览。',
    purpose: '查看摘要、标签、去重和抓取新鲜度等质量信号。',
    path: '/articles/quality',
  },
  {
    title: '最近任务',
    description: '文章任务与进度。',
    purpose: '查看最近 Job 的状态和执行进度，并跳转到 Job Detail。',
    path: '/articles/jobs',
  },
  {
    title: '处理结果',
    description: '文章结构化产物。',
    purpose: '查看最近一次处理的结构化输出和样本结果。',
    path: '/articles/results',
  },
  {
    title: '高级维护',
    description: '文章维护操作。',
    purpose: '执行重跑、失败重试和清理操作。',
    path: '/articles/maintenance',
  },
] as const;

const articlePipelineJobType = 'pipeline-run';

const articleSubpages = {
  '/articles/run': {
    title: '抓取与处理',
    description: '抓取新文章、抓取并处理、处理已有文章的入口。',
    summary: '从 Profile 触发文章处理全链路，完成抓取、清洗、校验、入库和结果回看。',
  },
  '/articles/list': {
    title: '文章列表',
    description: '查看已抓取文章结果和基础筛选条件。',
    summary: '按条件查看已抓取文章结果。',
  },
  '/articles/quality': {
    title: '数据质量',
    description: '查看文章质量信号和结果概览。',
    summary: '结合文章列表和最近 Job 汇总质量信号。',
  },
  '/articles/jobs': {
    title: '最近任务',
    description: '查看文章相关 Job 和执行进度。',
    summary: '聚合最近文章 Job 的状态和执行进度。',
  },
  '/articles/results': {
    title: '处理结果',
    description: '查看文章处理后的结构化结果。',
    summary: '展示最近 Job 的结构化输出与样本文章。',
  },
  '/articles/maintenance': {
    title: '高级维护',
    description: '失败恢复、重跑和清理的维护入口。',
    summary: '提供失败恢复、重跑和清理操作。',
  },
} as const;

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return '请求失败';
}

function createStepDefaults(step: WorkflowStep | null) {
  const defaults: Record<string, string | boolean> = {};
  const fields = step?.param_schema.fields ?? {};

  Object.entries(fields).forEach(([name, field]) => {
    if (name === 'profile_id' || name === 'config_path' || name === 'use_db') {
      return;
    }
    const defaultValue = field.default;
    if (field.type === 'boolean') {
      defaults[name] = typeof defaultValue === 'boolean' ? defaultValue : false;
      return;
    }
    if (field.type === 'number' || field.type === 'integer') {
      defaults[name] = typeof defaultValue === 'number' ? String(defaultValue) : '';
      return;
    }
    if (typeof defaultValue === 'string') {
      defaults[name] = defaultValue;
      return;
    }
    if (defaultValue !== undefined && defaultValue !== null) {
      defaults[name] = String(defaultValue);
      return;
    }
    defaults[name] = '';
  });

  return defaults;
}

function buildStepParams(step: WorkflowStep | null, values: Record<string, string | boolean>, profileId: string) {
  const params: Record<string, unknown> = {};
  const fields = step?.param_schema.fields ?? {};

  Object.entries(fields).forEach(([name, field]) => {
    if (name === 'profile_id' || name === 'config_path' || name === 'use_db') {
      return;
    }
    const rawValue = values[name];

    if (field.type === 'boolean') {
      params[name] = Boolean(rawValue);
      return;
    }

    if (field.type === 'number' || field.type === 'integer') {
      const numericValue = typeof rawValue === 'string' ? Number(rawValue.trim()) : Number(rawValue);
      if (Number.isFinite(numericValue) && String(rawValue).trim() !== '') {
        params[name] = field.type === 'integer' ? Math.trunc(numericValue) : numericValue;
      }
      return;
    }

    if (typeof rawValue === 'string' && rawValue.trim()) {
      params[name] = rawValue.trim();
      return;
    }
  });

  if (profileId.trim()) {
    params.profile_id = profileId.trim();
  }

  if ('use_db' in fields) {
    params.use_db = true;
  }

  return params;
}

function formatTimestamp(value: string | null | undefined) {
  if (!value) return '未记录';
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function formatDuration(durationMs: number | null | undefined) {
  if (durationMs === null || durationMs === undefined || !Number.isFinite(durationMs)) {
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

function toIsoTimestamp(dateInput: string, endOfDay = false) {
  if (!dateInput) return undefined;
  return `${dateInput}T${endOfDay ? '23:59:59' : '00:00:00'}Z`;
}

function mergeFilterOptions(values: string[], selected: string) {
  const merged = new Set(values.map((value) => value.trim()).filter(Boolean));
  const normalizedSelected = selected.trim();
  if (normalizedSelected) {
    merged.add(normalizedSelected);
  }
  return Array.from(merged).sort((left, right) => left.localeCompare(right, 'zh-CN'));
}

function isArticlePipelineJob(job: JobRecord) {
  const params = job.params as Record<string, unknown> | null;
  const result = job.result as JobResultPayload | null;
  const workflowRun = result?.workflow_run ?? undefined;
  const workflowId = workflowRun ? String(workflowRun.workflow_id ?? '') : '';
  return job.job_type === articlePipelineJobType && (Boolean(params?.profile_id) || workflowId === 'article_pipeline');
}

function getWorkflowRun(job: JobRecord) {
  const result = job.result as JobResultPayload | null;
  return result?.workflow_run ?? null;
}

function getWorkflowRunSteps(job: JobRecord) {
  const workflowRun = getWorkflowRun(job);
  const stepResults = workflowRun?.step_results;
  return Array.isArray(stepResults) ? stepResults : [];
}

function getJobProfileId(job: JobRecord) {
  const params = job.params as Record<string, unknown> | null;
  if (params && typeof params.profile_id === 'string') {
    return params.profile_id;
  }
  const workflowRun = getWorkflowRun(job);
  const workflowParams = workflowRun?.workflow_params;
  if (workflowParams && typeof workflowParams === 'object' && typeof (workflowParams as Record<string, unknown>).profile_id === 'string') {
    return String((workflowParams as Record<string, unknown>).profile_id);
  }
  return '未记录';
}

function getJobStage(job: JobRecord) {
  const workflowRun = getWorkflowRun(job);
  if (!workflowRun) return job.job_type;
  const stepResults = getWorkflowRunSteps(job);
  const lastStep = stepResults.length > 0 ? (stepResults[stepResults.length - 1] as Record<string, unknown>) : null;
  if (lastStep && typeof lastStep.step_name === 'string') {
    return lastStep.step_name;
  }
  if (lastStep && typeof lastStep.step_id === 'string') {
    return lastStep.step_id;
  }
  const runContext = workflowRun.run_context as Record<string, unknown> | undefined;
  return typeof runContext?.status === 'string' ? String(runContext.status) : job.job_type;
}

function getJobWorkflowStatus(job: JobRecord) {
  const workflowRun = getWorkflowRun(job);
  const runContext = workflowRun?.run_context as Record<string, unknown> | undefined;
  return typeof runContext?.status === 'string' ? String(runContext.status) : job.status;
}

function getJobDurationMs(job: JobRecord) {
  const workflowRun = getWorkflowRun(job);
  if (!workflowRun) return null;
  const runContext = workflowRun.run_context;
  if (!runContext || typeof runContext !== 'object') return null;
  const durationMs = (runContext as Record<string, unknown>).duration_ms;
  return typeof durationMs === 'number' ? durationMs : null;
}

function getJobResultPayload(job: JobRecord) {
  const workflowRun = getWorkflowRun(job);
  const stepResults = getWorkflowRunSteps(job) as Array<Record<string, unknown>>;
  const processStep = stepResults.find((step) => String(step.step_name ?? step.step_id ?? '') === 'process');
  const validateStep = stepResults.find((step) => String(step.step_name ?? step.step_id ?? '') === 'validate');
  const cleanStep = stepResults.find((step) => String(step.step_name ?? step.step_id ?? '') === 'clean');
  return {
    workflowRun,
    stepResults,
    processStep,
    validateStep,
    cleanStep,
  };
}

function latestArticleJob(jobs: JobRecord[]) {
  return jobs
    .filter(isArticlePipelineJob)
    .slice()
    .sort((left, right) => (right.created_at || '').localeCompare(left.created_at || ''))[0] ?? null;
}

function countBy<T>(items: T[], getter: (item: T) => string | null | undefined) {
  const counts = new Map<string, number>();
  for (const item of items) {
    const key = getter(item) || '';
    if (!key) continue;
    counts.set(key, (counts.get(key) || 0) + 1);
  }
  return counts;
}

function duplicateHashCount(articles: ArticleRecord[]) {
  let duplicates = 0;
  const counts = countBy(articles, (article) => article.content_hash);
  counts.forEach((count) => {
    if (count > 1) {
      duplicates += count - 1;
    }
  });
  return duplicates;
}

function qualityCoverage(articles: ArticleRecord[]) {
  const total = articles.length;
  const withSummary = articles.filter((article) => Boolean(article.summary?.trim())).length;
  const withTags = articles.filter((article) => article.tags.length > 0).length;
  const withHash = articles.filter((article) => Boolean(article.content_hash?.trim())).length;
  const withAuthor = articles.filter((article) => Boolean(article.author_name || article.author_id)).length;
  const duplicateCountValue = duplicateHashCount(articles);
  const latestCrawledAt = articles.reduce<string | null>((latest, article) => {
    if (!article.crawled_at) return latest;
    return !latest || article.crawled_at > latest ? article.crawled_at : latest;
  }, null);

  return {
    total,
    withSummary,
    withTags,
    withHash,
    withAuthor,
    duplicateCount: duplicateCountValue,
    latestCrawledAt,
  };
}

function MetricCard({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">{value}</p>
      {hint ? <p className="mt-2 text-sm leading-6 text-slate-600">{hint}</p> : null}
    </div>
  );
}

function CheckboxField({
  label,
  checked,
  onChange,
  description,
  disabled = false,
}: {
  label: string;
  checked: boolean;
  onChange: (value: boolean) => void;
  description: string;
  disabled?: boolean;
}) {
  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-slate-900">{label}</label>
      <label className={`flex h-10 cursor-pointer items-center gap-3 rounded-xl border px-3 transition-colors ${disabled ? 'border-slate-200 bg-slate-50 opacity-60' : 'border-slate-200 bg-white hover:bg-slate-50'}`}>
        <input
          aria-label={label}
          checked={checked}
          className="h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-400"
          disabled={disabled}
          onChange={(event) => onChange(event.target.checked)}
          type="checkbox"
        />
        <span className="text-sm font-medium text-slate-900">{checked ? '开启' : '关闭'}</span>
      </label>
      <p className="text-xs leading-6 text-slate-500">{description}</p>
    </div>
  );
}

function WorkspaceCard({
  title,
  description,
  purpose,
  path,
}: {
  title: string;
  description: string;
  purpose: string;
  path: string;
}) {
  return (
    <Card className="flex h-full flex-col">
      <CardHeader>
        <div className="min-w-0">
          <CardTitle>{title}</CardTitle>
          <CardDescription className="mt-2">{description}</CardDescription>
        </div>
      </CardHeader>
      <CardContent className="mt-auto space-y-3">
        <p className="text-sm leading-6 text-slate-600">
          <span className="font-medium text-slate-900">用途：</span>
          {purpose}
        </p>
        <Link
          className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-transparent px-4 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400/50"
          to={path}
        >
          进入{title}
        </Link>
      </CardContent>
    </Card>
  );
}

function ArticlePageShell({
  title,
  description,
  summary,
  children,
  actionLabel = '返回文章工作台',
}: {
  title: string;
  description: string;
  summary: string;
  children: ReactNode;
  actionLabel?: string;
}) {
  const navigate = useNavigate();

  return (
    <main className="page-stack">
      <PageHeader kicker="文章" title={title} description={description} actionLabel={actionLabel} onAction={() => navigate('/articles')} />
      <SectionCard title="页面摘要" description={summary}>
        {children}
      </SectionCard>
    </main>
  );
}

function ArticleLoadingState({ label, description }: { label: string; description: string }) {
  return (
    <SectionCard title="加载中" description={description}>
      <LoadingState label={label} description={description} />
      <div className="mt-4 space-y-3">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    </SectionCard>
  );
}

function ArticleErrorState({
  error,
  onRetry,
  retryLabel,
  title,
}: {
  error: unknown;
  onRetry?: () => void;
  retryLabel?: string;
  title: string;
}) {
  return (
    <ErrorState
      category={error instanceof ApiError && error.status === 404 ? 'data empty' : 'network error'}
      title={title}
      description={getErrorMessage(error)}
      suggestion="刷新页面或切换筛选条件后重试。"
      retryLabel={retryLabel ?? '重试'}
      onRetry={onRetry}
    />
  );
}

export function ArticleWorkspacePage() {
  return (
    <main className="page-stack">
      <PageHeader kicker="文章" title="文章工作台" description="请选择一个入口开始处理文章数据。" />

      <section className="grid gap-6">
        <Card className="border-sky-200 bg-sky-50/70">
          <CardHeader>
            <CardTitle>工作台摘要</CardTitle>
            <CardDescription>工作台只保留三项摘要信息，分别对应入口、页面和输入模型。</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-3">
            <MetricCard label="当前入口" value="文章" />
            <MetricCard label="当前页面" value="工作台首页" />
            <MetricCard label="输入模型" value="Profile" />
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {workspaceSections.map((section) => (
          <WorkspaceCard key={section.title} title={section.title} description={section.description} purpose={section.purpose} path={section.path} />
        ))}
      </section>
    </main>
  );
}

export function ArticleRunPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [selectedProfileId, setSelectedProfileId] = useState('');
  const [selectedStepId, setSelectedStepId] = useState('');
  const [stepValues, setStepValues] = useState<Record<string, string | boolean>>({});
  const [scheduleTime, setScheduleTime] = useState('09:00');
  const [scheduleForce, setScheduleForce] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [submittedJobId, setSubmittedJobId] = useState<string | null>(null);

  const profilesQuery = useQuery<ProfileListResponse, ApiError>({
    queryKey: ['profiles', 'article-run'],
    queryFn: () => listProfiles({ skip: 0, limit: 100 }),
    staleTime: 30_000,
  });

  const pipelineQuery = useQuery<PipelineDetailResponse, ApiError>({
    queryKey: ['article-pipeline', 'detail'],
    queryFn: getArticlePipeline,
    staleTime: 30_000,
  });

  const scheduleStatusQuery = useQuery<ArticlePipelineScheduleState, ApiError>({
    queryKey: ['article-pipeline', 'schedule', 'status'],
    queryFn: getArticlePipelineScheduleStatus,
    staleTime: 10_000,
  });

  const profiles = profilesQuery.data?.items ?? [];
  const workflow = pipelineQuery.data?.pipeline.workflow ?? null;
  const steps = workflow?.steps ?? [];

  useEffect(() => {
    if (!selectedProfileId && profiles.length > 0) {
      setSelectedProfileId(profiles[0].profile_id);
    }
  }, [profiles, selectedProfileId]);

  useEffect(() => {
    if (!selectedStepId && steps.length > 0) {
      setSelectedStepId(steps[0].step_id);
    }
  }, [steps, selectedStepId]);

  useEffect(() => {
    if (submittedJobId) {
      navigate(`/jobs/${encodeURIComponent(submittedJobId)}`);
    }
  }, [navigate, submittedJobId]);

  const selectedProfile = useMemo<ProfileRecord | null>(() => {
    return profiles.find((profile) => profile.profile_id === selectedProfileId) ?? null;
  }, [profiles, selectedProfileId]);

  const selectedStep = useMemo<WorkflowStep | null>(() => {
    return steps.find((step) => step.step_id === selectedStepId) ?? steps[0] ?? null;
  }, [selectedStepId, steps]);

  useEffect(() => {
    if (!selectedStep) {
      return;
    }
    setStepValues(createStepDefaults(selectedStep));
  }, [selectedStep]);

  const runMutation = useMutation({
    mutationFn: async () => {
      if (!selectedStep) {
        throw new Error('未选择步骤');
      }

      return runArticlePipelineStep(selectedStep.step_id, {
        params: buildStepParams(selectedStep, stepValues, selectedProfileId),
        created_by: 'web',
        confirmed: false,
      });
    },
    onSuccess: async (data) => {
      setMessage('文章处理已提交，正在跳转到 Job Detail。');
      setSubmittedJobId(data.job.id);
      await queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
    onError: (error: unknown) => {
      setMessage(getErrorMessage(error));
    },
  });

  const startScheduleMutation = useMutation({
    mutationFn: async () => {
      return startArticlePipelineSchedule({
        schedule_time: scheduleTime.trim(),
        profile_id: selectedProfileId,
        force: scheduleForce,
      });
    },
    onSuccess: async () => {
      setMessage('定时任务已启动，后续会按设置时间执行 pipeline-run。');
      await Promise.all([
        scheduleStatusQuery.refetch(),
        queryClient.invalidateQueries({ queryKey: ['jobs'] }),
      ]);
    },
    onError: (error: unknown) => {
      setMessage(getErrorMessage(error));
    },
  });

  const stopScheduleMutation = useMutation({
    mutationFn: async () => {
      return stopArticlePipelineSchedule({
        profile_id: selectedProfileId,
      });
    },
    onSuccess: async () => {
      setMessage('定时任务已停止。');
      await scheduleStatusQuery.refetch();
    },
    onError: (error: unknown) => {
      setMessage(getErrorMessage(error));
    },
  });

  const isLoading = profilesQuery.isLoading || pipelineQuery.isLoading;
  const loadError = profilesQuery.error ?? pipelineQuery.error;
  const canSubmit = Boolean(selectedProfileId) && Boolean(selectedStep) && !isLoading && !loadError;
  const scheduleState = scheduleStatusQuery.data ?? null;
  const scheduleActive = Boolean(scheduleState?.scheduler_started);

  const selectedStepFields = Object.entries(selectedStep?.param_schema.fields ?? {}).filter(
    ([name]) => name !== 'profile_id' && name !== 'config_path' && name !== 'use_db',
  );
  const selectedStepDescription = selectedStep?.description ?? '请选择一个 step。';
  const selectedStepJobType = selectedStep?.required_job_type ?? articlePipelineJobType;
  const scheduleDisabled = !selectedProfileId || !scheduleTime.trim() || isLoading || !!loadError || startScheduleMutation.isPending;
  const scheduleStopDisabled = !scheduleActive || stopScheduleMutation.isPending;

  function renderStepField(name: string, field: WorkflowParamField) {
    const fieldId = `article-run-${selectedStep?.step_id ?? 'step'}-${name}`;
    const value = stepValues[name];

    if (field.enum && field.enum.length > 0) {
      return (
        <div key={name} className="space-y-2">
          <label className="text-sm font-medium text-slate-900" htmlFor={fieldId}>
            {name}
          </label>
          <Select
            id={fieldId}
            value={typeof value === 'string' ? value : ''}
            onChange={(event) =>
              setStepValues((current) => ({
                ...current,
                [name]: event.target.value,
              }))
            }
          >
            <option value="">请选择</option>
            {field.enum.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </Select>
          {field.description ? <p className="text-xs leading-6 text-slate-500">{field.description}</p> : null}
        </div>
      );
    }

    if (field.type === 'boolean') {
      return (
        <CheckboxField
          key={name}
          label={name}
          checked={Boolean(value)}
          onChange={(checked) =>
            setStepValues((current) => ({
              ...current,
              [name]: checked,
            }))
          }
          description={field.description || '布尔参数。'}
        />
      );
    }

    return (
      <div key={name} className="space-y-2">
        <label className="text-sm font-medium text-slate-900" htmlFor={fieldId}>
          {name}
        </label>
        <Input
          id={fieldId}
          type={field.type === 'number' || field.type === 'integer' ? 'number' : 'text'}
          value={typeof value === 'string' ? value : ''}
          onChange={(event) =>
            setStepValues((current) => ({
              ...current,
              [name]: event.target.value,
            }))
          }
          placeholder={field.description || name}
        />
        {field.description ? <p className="text-xs leading-6 text-slate-500">{field.description}</p> : null}
      </div>
    );
  }

  return (
    <main className="page-stack">
      <PageHeader kicker="文章" title="抓取与处理" description="按 step 生成 job，支持 Force、增量处理和每日定时调度。" actionLabel="返回文章工作台" onAction={() => navigate('/articles')} />

      {message ? (
        <div className="rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-800">{message}</div>
      ) : null}

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(0,0.85fr)]">
        <Card>
          <CardHeader>
            <CardTitle>步骤运行</CardTitle>
            <CardDescription>先选 step，再按 schema 填参数。勾选 Force 时会删除旧数据并重新开始。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-5 w-1/3" />
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-24 w-full" />
              </div>
            ) : loadError ? (
              <div className="space-y-3 rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-900">
                <p>{getErrorMessage(loadError)}</p>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => profilesQuery.refetch()}>
                    重试 Profile
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => pipelineQuery.refetch()}>
                    重试 Pipeline
                  </Button>
                </div>
              </div>
            ) : profiles.length === 0 ? (
              <EmptyState
                title="暂无可用 Profile"
                description="请先到配置管理创建 Profile，再回到这里运行文章处理。"
                actionLabel="前往配置管理"
                onAction={() => navigate('/profiles')}
              />
            ) : (
              <>
                <div className="grid gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-slate-900" htmlFor="article-run-profile">
                      Profile
                    </label>
                    <Select id="article-run-profile" value={selectedProfileId} onChange={(event) => setSelectedProfileId(event.target.value)}>
                      {profiles.map((profile) => (
                        <option key={profile.profile_id} value={profile.profile_id}>
                          {profile.profile_id} · {profile.name}
                        </option>
                      ))}
                    </Select>
                    <p className="text-xs text-slate-500">当前选择：{selectedProfile?.environment ?? '未选择'}</p>
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium text-slate-900" htmlFor="article-run-step">
                      Step
                    </label>
                    <Select id="article-run-step" value={selectedStepId} onChange={(event) => setSelectedStepId(event.target.value)}>
                      {steps.map((step) => (
                        <option key={step.step_id} value={step.step_id}>
                          {step.step_id} · {step.title}
                        </option>
                      ))}
                    </Select>
                    {selectedStep ? (
                      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge variant="info">{selectedStepJobType}</Badge>
                          <Badge variant="default">{selectedStep.step_id}</Badge>
                        </div>
                        <p className="mt-3 font-medium text-slate-900">{selectedStep.title}</p>
                        <p className="mt-2 leading-6">{selectedStepDescription}</p>
                      </div>
                    ) : null}
                  </div>
                </div>

                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-medium text-slate-900">步骤参数</p>
                      <p className="mt-1 text-sm text-slate-600">不同 step 会展示不同参数，Force 会在后端重置旧状态。</p>
                    </div>
                    <Badge variant={selectedStep ? 'success' : 'default'}>{selectedStep ? '已选择 step' : '请选择 step'}</Badge>
                  </div>
                  <div className="mt-4 grid gap-4 md:grid-cols-2">
                    {selectedStepFields.map(([name, field]) => renderStepField(name, field))}
                  </div>
                </div>

                <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
                  <p className="font-medium text-slate-900">运行说明</p>
                  <ul className="mt-2 space-y-2 leading-6">
                    <li>Step job 会按照当前选择的参数直接生成对应 Job，不再默认走全量 pipeline-run。</li>
                    <li>Force 勾选后会删除旧数据重新开始；不勾选时只处理上次基础上未完成的数据。</li>
                    <li>运行成功后会跳转到 Job Detail，方便继续查看执行进度和结果。</li>
                  </ul>
                </div>

                <div className="flex flex-wrap items-center gap-3">
                  <Button onClick={() => runMutation.mutate()} disabled={!canSubmit || runMutation.isPending}>
                    {runMutation.isPending ? '提交中' : '运行步骤 Job'}
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => {
                      if (profiles.length > 0) {
                        setSelectedProfileId(profiles[0].profile_id);
                      }
                      if (steps.length > 0) {
                        setSelectedStepId(steps[0].step_id);
                      }
                      setMessage(null);
                    }}
                    disabled={isLoading || loadError != null}
                  >
                    重置
                  </Button>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>定时调度</CardTitle>
            <CardDescription>仅支持 pipeline-run 全量处理，按时间自动抓取当天数据，并支持 start/stop。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {scheduleStatusQuery.isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-5 w-1/2" />
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-20 w-full" />
              </div>
            ) : scheduleStatusQuery.error ? (
              <div className="space-y-3 rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-900">
                <p>{getErrorMessage(scheduleStatusQuery.error)}</p>
                <Button size="sm" variant="outline" onClick={() => scheduleStatusQuery.refetch()}>
                  重试
                </Button>
              </div>
            ) : (
              <>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-slate-900">当前状态</p>
                      <p className="mt-1 text-xs text-slate-500">定时任务只作用于 pipeline-run 全量处理。</p>
                    </div>
                    <Badge variant={scheduleActive ? 'success' : 'default'}>{scheduleActive ? '运行中' : '已停止'}</Badge>
                  </div>
                  <div className="mt-4 space-y-2 text-sm text-slate-700">
                    <p>调度时间：{scheduleState?.schedule_time ?? scheduleTime}</p>
                    <p>Force：{scheduleState?.force ? '开启' : '关闭'}</p>
                    <p>Profile：{scheduleState?.profile_id ?? selectedProfileId ?? '未选择'}</p>
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-900" htmlFor="article-schedule-time">
                    触发时间
                  </label>
                  <Input
                    id="article-schedule-time"
                    type="time"
                    value={scheduleTime}
                    onChange={(event) => setScheduleTime(event.target.value)}
                  />
                  <p className="text-xs text-slate-500">启动后会在每天该时间自动执行当天的 pipeline-run。</p>
                </div>

                <CheckboxField
                  label="Force"
                  checked={scheduleForce}
                  onChange={setScheduleForce}
                  description="勾选后，如果当天已存在成功记录，也会重新执行当天数据。"
                />

                <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
                  <p className="font-medium text-slate-900">启动说明</p>
                  <ul className="mt-2 space-y-2 leading-6">
                    <li>只处理当天数据；如果当天已经完成且未勾选 Force，则会返回已完成。</li>
                    <li>启动和停止都基于当前 Profile，便于单 Profile 场景下切换。</li>
                    <li>当前实现是进程内调度，页面刷新后可以重新查询状态。</li>
                  </ul>
                </div>

                <div className="flex flex-wrap items-center gap-3">
                  <Button onClick={() => startScheduleMutation.mutate()} disabled={scheduleDisabled}>
                    {startScheduleMutation.isPending ? '启动中' : scheduleActive ? '重新启动' : '启动定时任务'}
                  </Button>
                  <Button variant="secondary" onClick={() => stopScheduleMutation.mutate()} disabled={scheduleStopDisabled}>
                    {stopScheduleMutation.isPending ? '停止中' : '停止定时任务'}
                  </Button>
                  <Button variant="outline" onClick={() => scheduleStatusQuery.refetch()}>
                    刷新状态
                  </Button>
                </div>
              </>
            )}
          </CardContent>
        </Card>

      </section>
    </main>
  );
}

export function ArticleListPage() {
  const navigate = useNavigate();
  const [authorId, setAuthorId] = useState('');
  const [source, setSource] = useState('');
  const [traderId, setTraderId] = useState('');
  const [publishedAfter, setPublishedAfter] = useState('');
  const [publishedBefore, setPublishedBefore] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 12;

  useEffect(() => {
    setPage(1);
  }, [authorId, source, traderId, publishedAfter, publishedBefore]);

  const articlesQuery = useQuery<ArticleListResponse, ApiError>({
    queryKey: ['articles', 'list', authorId, source, traderId, publishedAfter, publishedBefore, page],
    queryFn: () =>
      listArticles({
        page,
        page_size: pageSize,
        author_id: authorId || undefined,
        source: source || undefined,
        trader_id: traderId || undefined,
        published_after: toIsoTimestamp(publishedAfter),
        published_before: toIsoTimestamp(publishedBefore, true),
      }),
    staleTime: 20_000,
  });

  const filterOptionsQuery = useQuery<ArticleFilterOptionsResponse, ApiError>({
    queryKey: ['articles', 'filter-options', authorId, source, traderId, publishedAfter, publishedBefore],
    queryFn: () =>
      listArticleFilterOptions({
        author_id: authorId || undefined,
        source: source || undefined,
        trader_id: traderId || undefined,
        published_after: toIsoTimestamp(publishedAfter),
        published_before: toIsoTimestamp(publishedBefore, true),
      }),
    staleTime: 20_000,
  });

  const articles = articlesQuery.data?.items ?? [];
  const total = articlesQuery.data?.total ?? 0;
  const pages = articlesQuery.data?.pages ?? 0;

  const authorOptions = useMemo(() => mergeFilterOptions(filterOptionsQuery.data?.author_ids ?? [], authorId), [authorId, filterOptionsQuery.data?.author_ids]);
  const sourceOptions = useMemo(() => mergeFilterOptions(filterOptionsQuery.data?.sources ?? [], source), [source, filterOptionsQuery.data?.sources]);
  const traderOptions = useMemo(() => mergeFilterOptions(filterOptionsQuery.data?.trader_ids ?? [], traderId), [traderId, filterOptionsQuery.data?.trader_ids]);

  const tableRows = useMemo(() => {
    return articles.map((article) => ({
      ...article,
      tagText: article.tags.length ? article.tags.join('、') : '无',
      publishedText: formatTimestamp(article.published_at),
      crawledText: formatTimestamp(article.crawled_at),
    }));
  }, [articles]);

  if (articlesQuery.isLoading) {
    return (
      <ArticlePageShell title={articleSubpages['/articles/list'].title} description={articleSubpages['/articles/list'].description} summary={articleSubpages['/articles/list'].summary}>
        <ArticleLoadingState label="正在加载文章列表" description="正在读取文章数据和筛选条件。" />
      </ArticlePageShell>
    );
  }

  if (articlesQuery.error) {
    return (
      <ArticlePageShell title={articleSubpages['/articles/list'].title} description={articleSubpages['/articles/list'].description} summary={articleSubpages['/articles/list'].summary}>
        <ArticleErrorState
          error={articlesQuery.error}
          title="文章列表加载失败"
          retryLabel="返回文章列表"
          onRetry={() => navigate('/articles/list')}
        />
      </ArticlePageShell>
    );
  }

  return (
    <ArticlePageShell title={articleSubpages['/articles/list'].title} description={articleSubpages['/articles/list'].description} summary={articleSubpages['/articles/list'].summary}>
      <div className="space-y-6">
        <SectionCard title="筛选条件" description="按 author / source / trader / 日期范围过滤文章结果。">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-900" htmlFor="article-author-id">
                Author ID
              </label>
              <Select id="article-author-id" value={authorId} onChange={(event) => setAuthorId(event.target.value)}>
                <option value="">全部作者</option>
                {filterOptionsQuery.isLoading && authorOptions.length === 0 ? <option value="" disabled>正在加载作者选项...</option> : null}
                {authorOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-900" htmlFor="article-source">
                Source
              </label>
              <Select id="article-source" value={source} onChange={(event) => setSource(event.target.value)}>
                <option value="">全部来源</option>
                {filterOptionsQuery.isLoading && sourceOptions.length === 0 ? <option value="" disabled>正在加载来源选项...</option> : null}
                {sourceOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-900" htmlFor="article-trader-id">
                Trader ID
              </label>
              <Select id="article-trader-id" value={traderId} onChange={(event) => setTraderId(event.target.value)}>
                <option value="">全部交易者</option>
                {filterOptionsQuery.isLoading && traderOptions.length === 0 ? <option value="" disabled>正在加载交易者选项...</option> : null}
                {traderOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-900" htmlFor="article-published-after">
                发布时间起
              </label>
              <Input id="article-published-after" type="date" value={publishedAfter} onChange={(event) => setPublishedAfter(event.target.value)} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-900" htmlFor="article-published-before">
                发布时间止
              </label>
              <Input id="article-published-before" type="date" value={publishedBefore} onChange={(event) => setPublishedBefore(event.target.value)} />
            </div>
            <div className="flex items-end gap-3">
              <Button
                variant="secondary"
                onClick={() => {
                  setAuthorId('');
                  setSource('');
                  setTraderId('');
                  setPublishedAfter('');
                  setPublishedBefore('');
                }}
              >
                重置筛选
              </Button>
            </div>
          </div>
        </SectionCard>

        <SectionCard
          title="文章结果"
          description={`共 ${total} 条，当前第 ${page} / ${Math.max(pages, 1)} 页。`}
          action={
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={() => void articlesQuery.refetch()}>
                <RefreshCw className="mr-2 h-4 w-4" />
                刷新
              </Button>
            </div>
          }
        >
          {tableRows.length === 0 ? (
            <EmptyState
              title="暂无文章结果"
              description="当前筛选条件下没有文章数据。"
              actionLabel="返回工作台"
              onAction={() => navigate('/articles')}
            />
          ) : (
            <div className="overflow-hidden rounded-2xl border border-slate-200">
              <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase tracking-[0.16em] text-slate-500">
                  <tr>
                    <th className="px-4 py-3">标题</th>
                    <th className="px-4 py-3">作者 / Source</th>
                    <th className="px-4 py-3">时间</th>
                    <th className="px-4 py-3">标签 / 互动</th>
                    <th className="px-4 py-3">操作</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 bg-white">
                  {tableRows.map((article) => (
                    <tr key={article.id} className="align-top">
                      <td className="px-4 py-4">
                        <p className="font-medium text-slate-950">{article.title}</p>
                        <p className="mt-1 break-all text-xs text-slate-500">{article.source_url}</p>
                      </td>
                      <td className="px-4 py-4 text-slate-700">
                        <p>{article.author_name ?? article.author_id ?? '未记录'}</p>
                        <p className="mt-1 text-xs text-slate-500">{article.source}</p>
                      </td>
                      <td className="px-4 py-4 text-slate-700">
                        <p>发布时间：{article.publishedText}</p>
                        <p className="mt-1 text-xs text-slate-500">抓取：{article.crawledText}</p>
                      </td>
                      <td className="px-4 py-4 text-slate-700">
                        <p>标签：{article.tagText}</p>
                        <p className="mt-1 text-xs text-slate-500">
                          评论 {article.comment_count} · 点赞 {article.like_count} · 收藏 {article.bookmark_count}
                        </p>
                      </td>
                      <td className="px-4 py-4">
                        <a
                          className="inline-flex h-9 min-w-24 shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-lg border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
                          href={article.source_url}
                          rel="noreferrer"
                          target="_blank"
                        >
                          <ExternalLink className="h-4 w-4" />
                          查看
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="mt-4 flex items-center justify-between gap-3 text-sm text-slate-600">
            <span>
              第 {page} / {Math.max(pages, 1)} 页
            </span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>
                上一页
              </Button>
              <Button variant="outline" size="sm" disabled={page >= pages} onClick={() => setPage((current) => current + 1)}>
                下一页
              </Button>
            </div>
          </div>
        </SectionCard>
      </div>
    </ArticlePageShell>
  );
}

export function ArticleJobsPage() {
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState<'all' | 'pending' | 'running' | 'success' | 'failed' | 'cancelled'>('all');

  const jobsQuery = useQuery<ArticleJobsResponse, ApiError>({
    queryKey: ['articles', 'jobs', statusFilter],
    queryFn: () =>
      listJobs({
        job_type: articlePipelineJobType,
        status: statusFilter === 'all' ? undefined : statusFilter,
        limit: 25,
      }),
    staleTime: 20_000,
  });

  const jobs = useMemo(() => {
    const items = jobsQuery.data?.items ?? [];
    return items.filter(isArticlePipelineJob);
  }, [jobsQuery.data?.items]);

  if (jobsQuery.isLoading) {
    return (
      <ArticlePageShell title={articleSubpages['/articles/jobs'].title} description={articleSubpages['/articles/jobs'].description} summary={articleSubpages['/articles/jobs'].summary}>
        <ArticleLoadingState label="正在加载最近任务" description="正在读取文章相关 Job 列表。" />
      </ArticlePageShell>
    );
  }

  if (jobsQuery.error) {
    return (
      <ArticlePageShell title={articleSubpages['/articles/jobs'].title} description={articleSubpages['/articles/jobs'].description} summary={articleSubpages['/articles/jobs'].summary}>
        <ArticleErrorState error={jobsQuery.error} title="最近任务加载失败" onRetry={() => void jobsQuery.refetch()} />
      </ArticlePageShell>
    );
  }

  return (
    <ArticlePageShell title={articleSubpages['/articles/jobs'].title} description={articleSubpages['/articles/jobs'].description} summary={articleSubpages['/articles/jobs'].summary}>
      <div className="space-y-6">
        <SectionCard title="任务筛选" description="仅查看文章工作台相关的 Job。">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-900" htmlFor="article-job-status">
                状态
              </label>
              <Select id="article-job-status" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as typeof statusFilter)}>
                <option value="all">全部</option>
                <option value="pending">pending</option>
                <option value="running">running</option>
                <option value="success">success</option>
                <option value="failed">failed</option>
                <option value="cancelled">cancelled</option>
              </Select>
            </div>
            <div className="flex items-end gap-3">
              <Button variant="outline" onClick={() => void jobsQuery.refetch()}>
                <RefreshCw className="mr-2 h-4 w-4" />
                刷新
              </Button>
            </div>
          </div>
        </SectionCard>

        <SectionCard title="最近任务" description={`共 ${jobs.length} 条文章相关 Job。`}>
          {jobs.length === 0 ? (
            <EmptyState
              title="暂无文章任务"
              description="当前没有匹配到 article_pipeline 的最近任务。"
              actionLabel="返回工作台"
              onAction={() => navigate('/articles')}
            />
          ) : (
            <div className="grid gap-4">
              {jobs.map((job) => (
                <div key={job.id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="font-medium text-slate-950">{job.id}</p>
                      <p className="mt-1 text-sm text-slate-600">操作类型：{job.job_type}</p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="info">Profile: {getJobProfileId(job)}</Badge>
                      <StatusBadge value={job.status} />
                    </div>
                  </div>

                  <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                    <MetricCard label="当前阶段" value={getJobStage(job)} />
                    <MetricCard label="创建时间" value={formatTimestamp(job.created_at)} />
                    <MetricCard label="耗时" value={formatDuration(getJobDurationMs(job))} />
                    <MetricCard label="工作流状态" value={getJobWorkflowStatus(job)} />
                  </div>

                  <div className="mt-4 flex flex-wrap gap-3">
                    <Button variant="outline" size="sm" onClick={() => navigate(`/jobs/${encodeURIComponent(job.id)}`)}>
                      打开 Job Detail
                    </Button>
                    <a
                      className="inline-flex h-9 items-center rounded-lg border border-transparent px-3 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-50 hover:text-slate-900"
                      href={`/jobs/${encodeURIComponent(job.id)}`}
                    >
                      直接跳转
                    </a>
                  </div>
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      </div>
    </ArticlePageShell>
  );
}

export function ArticleQualityPage() {
  const navigate = useNavigate();
  const articlesQuery = useQuery<ArticleListResponse, ApiError>({
    queryKey: ['articles', 'quality'],
    queryFn: () => listArticles({ page: 1, page_size: 50 }),
    staleTime: 20_000,
  });

  const jobsQuery = useQuery<ArticleJobsResponse, ApiError>({
    queryKey: ['articles', 'quality-jobs'],
    queryFn: () => listJobs({ job_type: articlePipelineJobType, limit: 10 }),
    staleTime: 20_000,
  });

  const articles = articlesQuery.data?.items ?? [];
  const latestJob = latestArticleJob(jobsQuery.data?.items ?? []);
  const coverage = useMemo(() => qualityCoverage(articles), [articles]);
  const latestJobPayload = latestJob ? getJobResultPayload(latestJob) : null;

  if (articlesQuery.isLoading || jobsQuery.isLoading) {
    return (
      <ArticlePageShell title={articleSubpages['/articles/quality'].title} description={articleSubpages['/articles/quality'].description} summary={articleSubpages['/articles/quality'].summary}>
        <ArticleLoadingState label="正在加载数据质量" description="正在读取文章列表和最近文章 Job。" />
      </ArticlePageShell>
    );
  }

  if (articlesQuery.error) {
    return (
      <ArticlePageShell title={articleSubpages['/articles/quality'].title} description={articleSubpages['/articles/quality'].description} summary={articleSubpages['/articles/quality'].summary}>
        <ArticleErrorState error={articlesQuery.error} title="文章质量加载失败" onRetry={() => void articlesQuery.refetch()} />
      </ArticlePageShell>
    );
  }

  if (jobsQuery.error) {
    return (
      <ArticlePageShell title={articleSubpages['/articles/quality'].title} description={articleSubpages['/articles/quality'].description} summary={articleSubpages['/articles/quality'].summary}>
        <ArticleErrorState error={jobsQuery.error} title="文章质量加载失败" onRetry={() => void jobsQuery.refetch()} />
      </ArticlePageShell>
    );
  }

  return (
    <ArticlePageShell title={articleSubpages['/articles/quality'].title} description={articleSubpages['/articles/quality'].description} summary={articleSubpages['/articles/quality'].summary}>
      <div className="space-y-6">
        <SectionCard title="质量概览" description="结合文章列表和最近一次文章 Job 计算当前质量信号。">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <MetricCard label="文章总数" value={coverage.total} hint="直接读取文章列表接口。"/>
            <MetricCard label="有摘要" value={coverage.withSummary} hint="可快速判断文章是否完成整理。"/>
            <MetricCard label="有标签" value={coverage.withTags} hint="用于观察结构化分类覆盖。"/>
            <MetricCard label="有内容 Hash" value={coverage.withHash} hint="用于检查去重和重复抓取。"/>
            <MetricCard label="重复文章数" value={coverage.duplicateCount} hint="按 content_hash 粗略统计重复记录。"/>
            <MetricCard label="最近抓取时间" value={formatTimestamp(coverage.latestCrawledAt)} hint="帮助判断数据是否新鲜。" />
          </div>
        </SectionCard>

        <SectionCard title="最近一次文章 Job" description="展示最近一次 article_pipeline 的执行状态和流程输出。">
          {latestJob ? (
            <div className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <MetricCard label="Job ID" value={latestJob.id} />
                <MetricCard label="Profile" value={getJobProfileId(latestJob)} />
                <MetricCard label="状态" value={latestJob.status} />
                <MetricCard label="阶段" value={getJobStage(latestJob)} />
              </div>

              <div className="grid gap-4 xl:grid-cols-2">
                <JsonViewer value={latestJobPayload?.stepResults ?? []} title="Step Results" />
                <JsonViewer value={latestJob.artifacts ?? []} title="Job Artifacts" />
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <MetricCard label="clean step" value={latestJobPayload?.cleanStep ? String(latestJobPayload.cleanStep.step_name ?? latestJobPayload.cleanStep.step_id ?? '已记录') : '未记录'} />
                <MetricCard label="validate step" value={latestJobPayload?.validateStep ? String(latestJobPayload.validateStep.step_name ?? latestJobPayload.validateStep.step_id ?? '已记录') : '未记录'} />
              </div>
            </div>
          ) : (
            <EmptyState
              title="暂无文章 Job"
              description="还没有找到 article_pipeline 的执行记录。"
              actionLabel="返回工作台"
              onAction={() => navigate('/articles')}
            />
          )}
        </SectionCard>
      </div>
    </ArticlePageShell>
  );
}

export function ArticleResultsPage() {
  const navigate = useNavigate();
  const articlesQuery = useQuery<ArticleListResponse, ApiError>({
    queryKey: ['articles', 'results'],
    queryFn: () => listArticles({ page: 1, page_size: 10 }),
    staleTime: 20_000,
  });

  const jobsQuery = useQuery<ArticleJobsResponse, ApiError>({
    queryKey: ['articles', 'results-jobs'],
    queryFn: () => listJobs({ job_type: articlePipelineJobType, limit: 10 }),
    staleTime: 20_000,
  });

  const articles = articlesQuery.data?.items ?? [];
  const latestJob = latestArticleJob(jobsQuery.data?.items ?? []);
  const latestJobPayload = latestJob ? getJobResultPayload(latestJob) : null;
  const resultHighlights = useMemo(() => {
    const payload = latestJobPayload?.processStep?.output_json;
    if (!payload || typeof payload !== 'object') {
      return [];
    }
    const record = payload as Record<string, unknown>;
    return [
      { label: 'extracted_concepts', value: Array.isArray(record.extracted_concepts) ? record.extracted_concepts.length : 0 },
      { label: 'trading_symbols', value: Array.isArray(record.trading_symbols) ? record.trading_symbols.length : 0 },
      { label: 'strategy_rules', value: Array.isArray(record.strategy_rules) ? record.strategy_rules.length : 0 },
      { label: 'preconditions', value: Array.isArray(record.preconditions) ? record.preconditions.length : 0 },
      { label: 'comment_insights', value: Array.isArray(record.comment_insights) ? record.comment_insights.length : 0 },
      { label: 'sentiment_score', value: record.sentiment_score ?? '未记录' },
      { label: 'confidence_score', value: record.confidence_score ?? '未记录' },
    ];
  }, [latestJobPayload?.processStep?.output_json]);

  if (articlesQuery.isLoading || jobsQuery.isLoading) {
    return (
      <ArticlePageShell title={articleSubpages['/articles/results'].title} description={articleSubpages['/articles/results'].description} summary={articleSubpages['/articles/results'].summary}>
        <ArticleLoadingState label="正在加载处理结果" description="正在读取文章结果和最近一次文章 Job。" />
      </ArticlePageShell>
    );
  }

  if (articlesQuery.error) {
    return (
      <ArticlePageShell title={articleSubpages['/articles/results'].title} description={articleSubpages['/articles/results'].description} summary={articleSubpages['/articles/results'].summary}>
        <ArticleErrorState error={articlesQuery.error} title="处理结果加载失败" onRetry={() => void articlesQuery.refetch()} />
      </ArticlePageShell>
    );
  }

  if (jobsQuery.error) {
    return (
      <ArticlePageShell title={articleSubpages['/articles/results'].title} description={articleSubpages['/articles/results'].description} summary={articleSubpages['/articles/results'].summary}>
        <ArticleErrorState error={jobsQuery.error} title="处理结果加载失败" onRetry={() => void jobsQuery.refetch()} />
      </ArticlePageShell>
    );
  }

  return (
    <ArticlePageShell title={articleSubpages['/articles/results'].title} description={articleSubpages['/articles/results'].description} summary={articleSubpages['/articles/results'].summary}>
      <div className="space-y-6">
        <SectionCard title="结构化结果摘要" description="展示最近一次文章 Job 中可消费的结构化输出。">
          {latestJob ? (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              {resultHighlights.map((item) => (
                <MetricCard key={item.label} label={item.label} value={String(item.value)} />
              ))}
            </div>
          ) : (
            <EmptyState title="暂无结构化结果" description="还没有找到 article_pipeline 的执行记录。" />
          )}
        </SectionCard>

        <div className="grid gap-6">
          <SectionCard title="最新 process 输出" description="这里直接展示最近一次 process step 的输出结果。">
            {latestJobPayload?.processStep ? <JsonViewer value={latestJobPayload.processStep.output_json ?? {}} title="Process Output" /> : <EmptyState title="暂无 process 输出" description="最近一次文章 Job 未暴露 process step 输出。" />}
          </SectionCard>

          <SectionCard title="结果样本" description="文章列表中的内容可与结构化输出一起用于验收。">
            {articles.length === 0 ? (
              <EmptyState title="暂无文章样本" description="当前没有可展示的文章结果。" actionLabel="返回工作台" onAction={() => navigate('/articles')} />
            ) : (
              <div className="space-y-3">
                {articles.slice(0, 5).map((article) => (
                  <div key={article.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <p className="font-medium text-slate-950">{article.title}</p>
                    <p className="mt-1 text-sm text-slate-600">{article.author_name ?? article.author_id ?? '未记录'} · {article.source}</p>
                    <p className="mt-2 text-sm leading-6 text-slate-700">{article.summary ?? '暂无摘要'}</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {article.tags.map((tag) => (
                        <Badge key={tag} variant="info">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </SectionCard>
        </div>
      </div>
    </ArticlePageShell>
  );
}

export function ArticleMaintenancePage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [selectedProfileId, setSelectedProfileId] = useState('');
  const [fromStep, setFromStep] = useState<'crawl' | 'clean' | 'validate' | 'store' | 'process' | ''>('');
  const [maxArticles, setMaxArticles] = useState('');
  const [newVersion, setNewVersion] = useState('');
  const [force, setForce] = useState(false);
  const [skipCrawl, setSkipCrawl] = useState(false);
  const [useDb, setUseDb] = useState(false);
  const [rebuildPending, setRebuildPending] = useState(false);
  const [retryFailed, setRetryFailed] = useState(false);
  const [cleanup, setCleanup] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [submittedJobId, setSubmittedJobId] = useState<string | null>(null);

  const profilesQuery = useQuery<ProfileListResponse, ApiError>({
    queryKey: ['profiles', 'article-maintenance'],
    queryFn: () => listProfiles({ skip: 0, limit: 100 }),
    staleTime: 30_000,
  });

  const profiles = profilesQuery.data?.items ?? [];

  useEffect(() => {
    if (!selectedProfileId && profiles.length > 0) {
      setSelectedProfileId(profiles[0].profile_id);
    }
  }, [profiles, selectedProfileId]);

  useEffect(() => {
    if (submittedJobId) {
      navigate(`/jobs/${encodeURIComponent(submittedJobId)}`);
    }
  }, [navigate, submittedJobId]);

  const selectedProfile = useMemo<ProfileRecord | null>(() => {
    return profiles.find((profile) => profile.profile_id === selectedProfileId) ?? null;
  }, [profiles, selectedProfileId]);

  const visibleStepParams = useMemo<StepParamKey[]>(() => {
    const supportMap: Record<'crawl' | 'clean' | 'validate' | 'store' | 'process' | '', StepParamKey[]> = {
      '': ['force', 'skip_crawl', 'use_db', 'max_articles'],
      crawl: ['force', 'skip_crawl', 'use_db', 'max_articles'],
      clean: ['force', 'max_articles'],
      validate: ['force', 'max_articles'],
      store: ['force', 'skip_crawl', 'use_db'],
      process: ['force', 'skip_crawl', 'use_db', 'new_version'],
    } as const;
    return supportMap[fromStep];
  }, [fromStep]);

  const normalizedMaintenanceMode: MaintenanceMode = cleanup
    ? 'cleanup'
    : rebuildPending
      ? 'rebuild_pending'
      : retryFailed
        ? 'retry_failed'
        : 'normal';

  const runMutation = useMutation({
    mutationFn: async () => {
      const params: ArticlePipelineRunParams = {
        profile_id: selectedProfileId,
      };

      if (normalizedMaintenanceMode === 'cleanup') {
        params.from_step = 'cleanup';
        params.cleanup = true;
      } else if (normalizedMaintenanceMode === 'rebuild_pending') {
        params.from_step = 'process';
        params.force = true;
        params.skip_crawl = true;
        params.use_db = true;
        params.rebuild_pending = true;
      } else if (normalizedMaintenanceMode === 'retry_failed') {
        params.from_step = fromStep || 'process';
        params.force = true;
        params.skip_crawl = true;
        params.use_db = true;
        params.retry_failed = true;
      } else if (fromStep) {
        params.from_step = fromStep;
      }

      if (force && normalizedMaintenanceMode === 'normal') {
        params.force = true;
      }
      if (skipCrawl && normalizedMaintenanceMode === 'normal') {
        params.skip_crawl = true;
      }
      if (useDb && normalizedMaintenanceMode === 'normal') {
        params.use_db = true;
      }
      if (normalizedMaintenanceMode === 'normal' && visibleStepParams.includes('max_articles') && maxArticles.trim()) {
        const parsedMaxArticles = Number(maxArticles);
        if (Number.isFinite(parsedMaxArticles) && parsedMaxArticles > 0) {
          params.max_articles = Math.floor(parsedMaxArticles);
        }
      }
      if (normalizedMaintenanceMode === 'normal' && visibleStepParams.includes('new_version') && newVersion.trim()) {
        params.new_version = newVersion.trim();
      }

      return runArticlePipeline({
        params,
        created_by: 'web',
        confirmed: false,
      });
    },
    onSuccess: async (data) => {
      setMessage('文章维护任务已提交，正在跳转到 Job Detail。');
      setSubmittedJobId(data.job.id);
      await queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
    onError: (error: unknown) => {
      setMessage(getErrorMessage(error));
    },
  });

  const isLoading = profilesQuery.isLoading;
  const loadError = profilesQuery.error;
  const canSubmit = Boolean(selectedProfileId) && !isLoading && !loadError;

  const modeSummary =
    normalizedMaintenanceMode === 'cleanup'
      ? '清理中间文件'
      : normalizedMaintenanceMode === 'rebuild_pending'
        ? '重建 pending tasks'
        : normalizedMaintenanceMode === 'retry_failed'
          ? '重试 failed tasks'
          : '普通重跑';

  return (
    <main className="page-stack">
      <PageHeader kicker="文章" title="高级维护" description="仅用于失败恢复、重跑、任务修复和数据修复。" actionLabel="返回文章工作台" onAction={() => navigate('/articles')} />

      {message ? (
        <div className="rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-800">{message}</div>
      ) : null}

      <section className="grid gap-6">
        <Card>
          <CardHeader>
            <CardTitle>维护入口</CardTitle>
            <CardDescription>重跑选项使用 Checkbox，并根据所选步骤显示对应参数。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            {isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-5 w-1/3" />
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-24 w-full" />
              </div>
            ) : loadError ? (
              <div className="space-y-3 rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-900">
                <p>{getErrorMessage(loadError)}</p>
                <Button size="sm" variant="outline" onClick={() => profilesQuery.refetch()}>
                  重试
                </Button>
              </div>
            ) : profiles.length === 0 ? (
              <EmptyState
                title="暂无可用 Profile"
                description="请先到配置管理创建 Profile，再回到这里执行维护操作。"
                actionLabel="前往配置管理"
                onAction={() => navigate('/profiles')}
              />
            ) : (
              <>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-900" htmlFor="article-maintenance-profile">
                    Profile
                  </label>
                  <Select
                    id="article-maintenance-profile"
                    value={selectedProfileId}
                    onChange={(event) => setSelectedProfileId(event.target.value)}
                  >
                    {profiles.map((profile) => (
                      <option key={profile.profile_id} value={profile.profile_id}>
                        {profile.profile_id} · {profile.name}
                      </option>
                    ))}
                  </Select>
                  <p className="text-xs text-slate-500">当前选择：{selectedProfile?.environment ?? '未选择'}</p>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-900" htmlFor="article-maintenance-from-step">
                    从指定步骤开始
                  </label>
                  <Select
                    id="article-maintenance-from-step"
                    value={fromStep}
                    onChange={(event) => setFromStep(event.target.value as typeof fromStep)}
                    disabled={cleanup || rebuildPending || retryFailed}
                  >
                    <option value="">不指定，完整执行</option>
                    <option value="crawl">crawl</option>
                    <option value="clean">clean</option>
                    <option value="validate">validate</option>
                    <option value="store">store</option>
                    <option value="process">process</option>
                  </Select>
                </div>

                <div className="space-y-3">
                  <p className="text-sm font-medium text-slate-900">维护模式</p>
                  <div className="grid gap-3 md:grid-cols-2">
                    <CheckboxField
                      label="重建 pending tasks"
                      checked={rebuildPending}
                      onChange={(value) => {
                        setRebuildPending(value);
                        if (value) {
                          setRetryFailed(false);
                          setCleanup(false);
                        }
                      }}
                      description="收口为 process 阶段的重建运行。"
                      disabled={cleanup}
                    />
                    <CheckboxField
                      label="重试 failed tasks"
                      checked={retryFailed}
                      onChange={(value) => {
                        setRetryFailed(value);
                        if (value) {
                          setRebuildPending(false);
                          setCleanup(false);
                        }
                      }}
                      description="收口为 process 阶段的失败重试运行。"
                      disabled={cleanup}
                    />
                    <CheckboxField
                      label="cleanup"
                      checked={cleanup}
                      onChange={(value) => {
                        setCleanup(value);
                        if (value) {
                          setRebuildPending(false);
                          setRetryFailed(false);
                        }
                      }}
                      description="清理中间文件。"
                    />
                  </div>
                </div>

                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
                  <p className="font-medium text-slate-900">步骤参数</p>
                  {fromStep ? (
                    <p className="mt-2 leading-6">当前只显示 {fromStep} 支持的参数。</p>
                  ) : (
                    <p className="mt-2 leading-6">未选择步骤时，显示通用参数。</p>
                  )}
                  <div className="mt-4 grid gap-3 md:grid-cols-2">
                    {visibleStepParams.includes('force') ? (
                      <CheckboxField
                        label="force"
                        checked={force}
                        onChange={setForce}
                        description="忽略已有中间结果，重新执行相关步骤。"
                        disabled={cleanup || rebuildPending || retryFailed}
                      />
                    ) : null}
                    {visibleStepParams.includes('skip_crawl') ? (
                      <CheckboxField
                        label="skip_crawl"
                        checked={skipCrawl}
                        onChange={setSkipCrawl}
                        description="跳过抓取，只处理已有文章。"
                        disabled={cleanup || rebuildPending || retryFailed}
                      />
                    ) : null}
                    {visibleStepParams.includes('use_db') ? (
                      <CheckboxField
                        label="use_db"
                        checked={useDb}
                        onChange={setUseDb}
                        description="从 raw_articles / DB 模式读取原始文章。"
                        disabled={cleanup}
                      />
                    ) : null}
                    {visibleStepParams.includes('max_articles') ? (
                      <div className="space-y-2 rounded-2xl border border-slate-200 bg-white p-4">
                        <label className="text-sm font-medium text-slate-900" htmlFor="article-maintenance-max-articles">
                          max_articles
                        </label>
                        <Input
                          id="article-maintenance-max-articles"
                          type="number"
                          min="1"
                          value={maxArticles}
                          onChange={(event) => setMaxArticles(event.target.value)}
                          placeholder="例如 100"
                          disabled={cleanup || rebuildPending || retryFailed}
                        />
                        <p className="text-xs leading-5 text-slate-500">仅在当前步骤支持时显示。</p>
                      </div>
                    ) : null}
                    {visibleStepParams.includes('new_version') ? (
                      <div className="space-y-2 rounded-2xl border border-slate-200 bg-white p-4">
                        <label className="text-sm font-medium text-slate-900" htmlFor="article-maintenance-new-version">
                          new_version
                        </label>
                        <Input
                          id="article-maintenance-new-version"
                          value={newVersion}
                          onChange={(event) => setNewVersion(event.target.value)}
                          placeholder="例如 v2"
                          disabled={cleanup || rebuildPending || retryFailed}
                        />
                        <p className="text-xs leading-5 text-slate-500">仅在 process 步骤显示。</p>
                      </div>
                    ) : null}
                  </div>
                </div>

                <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                  <p className="font-medium text-amber-950">当前维护模式：{modeSummary}</p>
                  <p className="mt-2 leading-6">选择不同步骤后，下面只保留该步骤支持的参数。</p>
                </div>

                <div className="flex flex-wrap items-center gap-3">
                  <Button
                    variant={cleanup ? 'destructive' : 'default'}
                    onClick={() => runMutation.mutate()}
                    disabled={!canSubmit || runMutation.isPending}
                  >
                    {runMutation.isPending ? '提交中' : '运行维护'}
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setFromStep('');
                      setMaxArticles('');
                      setNewVersion('');
                      setForce(false);
                      setSkipCrawl(false);
                      setUseDb(false);
                      setRebuildPending(false);
                      setRetryFailed(false);
                      setCleanup(false);
                      setMessage(null);
                    }}
                    disabled={isLoading || loadError != null}
                  >
                    恢复默认
                  </Button>
                </div>
              </>
            )}
          </CardContent>
        </Card>

      </section>
    </main>
  );
}
