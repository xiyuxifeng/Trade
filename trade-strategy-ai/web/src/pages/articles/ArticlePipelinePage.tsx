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
import { listArticles } from '@/lib/api/articles';
import { listJobs } from '@/lib/api/jobs';
import { listProfiles } from '@/lib/api/profiles';
import { runArticlePipeline } from '@/lib/api/pipelines';
import type { ArticleListResponse, ArticleRecord } from '@/types/articles';
import type { JobRecord, JobsListResponse } from '@/types/jobs';
import type { ProfileListResponse, ProfileRecord } from '@/types/profile';

type ArticleJobsResponse = JobsListResponse;
type MaintenanceMode = 'normal' | 'rebuild_pending' | 'retry_failed' | 'cleanup';

const workspaceSections = [
  {
    title: '抓取与处理',
    description: '抓取新文章、抓取并处理、处理已有文章。',
    path: '/articles/run',
  },
  {
    title: '文章列表',
    description: '查看文章结果、处理状态和基础筛选入口。',
    path: '/articles/list',
  },
  {
    title: '数据质量',
    description: '查看清洗、校验与抽取质量的总体入口。',
    path: '/articles/quality',
  },
  {
    title: '最近任务',
    description: '查看最近的文章相关 Job 与执行状态。',
    path: '/articles/jobs',
  },
  {
    title: '处理结果',
    description: '查看结构化抽取结果与可消费的文章信息。',
    path: '/articles/results',
  },
  {
    title: '高级维护',
    description: '失败恢复、重跑和维护操作入口，支持危险操作收口。',
    path: '/articles/maintenance',
  },
] as const;

const articlePipelineJobType = 'pipeline-run';

const articleSubpages = {
  '/articles/run': {
    title: '抓取与处理',
    description: '抓取新文章、抓取并处理、处理已有文章的入口。',
    summary: '从 Profile 开始运行文章处理主链路，并跳转到 Job Detail 查看结果。',
  },
  '/articles/list': {
    title: '文章列表',
    description: '查看已抓取文章、状态和基础筛选条件。',
    summary: '直接读取文章数据接口，展示可浏览、可筛选的文章结果。',
  },
  '/articles/quality': {
    title: '数据质量',
    description: '查看清洗、校验和抽取质量的结果概览。',
    summary: '基于文章列表和最近一次文章 Job 汇总质量信号和验证结果。',
  },
  '/articles/jobs': {
    title: '最近任务',
    description: '查看最近的文章相关 Job 和执行状态。',
    summary: '仅显示文章工作台相关的 Job，并保留跳转到 Job Detail 的入口。',
  },
  '/articles/results': {
    title: '处理结果',
    description: '查看文章处理后的结构化结果。',
    summary: '以最近一次文章 Job 的 workflow run 和产物作为结果入口。',
  },
  '/articles/maintenance': {
    title: '高级维护',
    description: '失败恢复、重跑和数据修复的维护入口。',
    summary: '支持普通重跑、process 阶段重建、失败重试和危险清理操作。',
  },
} as const;

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return '请求失败';
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

function isArticlePipelineJob(job: JobRecord) {
  const params = job.params as Record<string, unknown> | null;
  const result = job.result as Record<string, unknown> | null;
  const workflowRun = result && typeof result === 'object' ? (result.workflow_run as Record<string, unknown> | undefined) : undefined;
  const workflowId = workflowRun && typeof workflowRun === 'object' ? String(workflowRun.workflow_id ?? '') : '';
  return job.job_type === articlePipelineJobType && (Boolean(params?.profile_id) || workflowId === 'article_pipeline');
}

function getWorkflowRun(job: JobRecord) {
  const result = job.result as Record<string, unknown> | null;
  if (!result || typeof result !== 'object') return null;
  const workflowRun = result.workflow_run;
  return workflowRun && typeof workflowRun === 'object' ? (workflowRun as Record<string, unknown>) : null;
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
    <label className={`flex cursor-pointer items-start gap-3 rounded-2xl border p-4 transition-colors ${disabled ? 'border-slate-200 bg-slate-50 opacity-60' : 'border-slate-200 bg-white hover:bg-slate-50'}`}>
      <input
        aria-label={label}
        checked={checked}
        className="mt-1 h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-400"
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
        type="checkbox"
      />
      <div className="min-w-0">
        <p className="text-sm font-medium text-slate-900">{label}</p>
        <p className="mt-1 text-sm leading-6 text-slate-600">{description}</p>
      </div>
    </label>
  );
}

function WorkspaceCard({
  title,
  description,
  path,
  badgeLabel = '可用',
}: {
  title: string;
  description: string;
  path: string;
  badgeLabel?: string;
}) {
  return (
    <Card className="flex h-full flex-col">
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <CardTitle>{title}</CardTitle>
            <CardDescription className="mt-2">{description}</CardDescription>
          </div>
          <Badge variant="info">{badgeLabel}</Badge>
        </div>
      </CardHeader>
      <CardContent className="mt-auto">
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
  title,
}: {
  error: unknown;
  onRetry?: () => void;
  title: string;
}) {
  return (
    <ErrorState
      category={error instanceof ApiError && error.status === 404 ? 'data empty' : 'network error'}
      title={title}
      description={getErrorMessage(error)}
      suggestion="刷新页面或切换筛选条件后重试。"
      retryLabel="重试"
      onRetry={onRetry}
    />
  );
}

export function ArticleWorkspacePage() {
  return (
    <main className="page-stack">
      <PageHeader kicker="文章" title="文章工作台" description="请选择一个入口开始处理文章数据。" />

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
        <Card className="border-sky-200 bg-sky-50/70">
          <CardHeader>
            <CardTitle>工作台摘要</CardTitle>
            <CardDescription>入口迁移已完成，下面的子页面会继续接入真实数据和维护动作。</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2">
            <MetricCard label="当前入口" value="文章" />
            <MetricCard label="当前页面" value="工作台首页" />
            <MetricCard label="输入模型" value="Profile" />
            <MetricCard label="导出入口" value="已隐藏" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>迁移说明</CardTitle>
            <CardDescription>这里不再直接暴露单一 Pipeline 表单，而是作为文章工作台入口。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm leading-6 text-slate-700">
            <p>1. sidebar 保留“文章”，但工作台内承接抓取、列表、质量、任务、结果和维护。</p>
            <p>2. 运行入口只保留 Profile，维护入口继续收口到文章模块内。</p>
            <p>3. DuckDB 导出代码保留，但页面不暴露入口。</p>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {workspaceSections.map((section) => (
          <WorkspaceCard key={section.title} title={section.title} description={section.description} path={section.path} />
        ))}
      </section>
    </main>
  );
}

export function ArticleRunPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [selectedProfileId, setSelectedProfileId] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const [submittedJobId, setSubmittedJobId] = useState<string | null>(null);

  const profilesQuery = useQuery<ProfileListResponse, ApiError>({
    queryKey: ['profiles', 'article-run'],
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

  const runMutation = useMutation({
    mutationFn: async () => {
      return runArticlePipeline({
        params: {
          profile_id: selectedProfileId,
        },
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

  const isLoading = profilesQuery.isLoading;
  const loadError = profilesQuery.error;
  const canSubmit = Boolean(selectedProfileId) && !isLoading && !loadError;

  return (
    <main className="page-stack">
      <PageHeader kicker="文章" title="抓取与处理" description="只保留 Profile 选择，不再要求填写 config_path。" actionLabel="返回文章工作台" onAction={() => navigate('/articles')} />

      {message ? (
        <div className="rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-800">{message}</div>
      ) : null}

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
        <Card>
          <CardHeader>
            <CardTitle>Profile-only 运行入口</CardTitle>
            <CardDescription>运行入口只暴露 Profile 选择，并沿用现有 article_pipeline 路径。</CardDescription>
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
                <Button size="sm" variant="outline" onClick={() => profilesQuery.refetch()}>
                  重试
                </Button>
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
                <div className="grid gap-3">
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-slate-900" htmlFor="article-run-profile">
                      Profile
                    </label>
                    <Select
                      id="article-run-profile"
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
                </div>

                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
                  <p className="font-medium text-slate-900">运行说明</p>
                  <ul className="mt-2 space-y-2">
                    <li>提交后会把 `profile_id` 传给后端，由后端统一解析运行上下文。</li>
                    <li>页面不再显示 `config_path` 输入框或参数类型切换。</li>
                    <li>运行完成后会跳转到 Job Detail 查看进度与日志。</li>
                  </ul>
                </div>

                <div className="flex items-center gap-3">
                  <Button onClick={() => runMutation.mutate()} disabled={!canSubmit || runMutation.isPending}>
                    {runMutation.isPending ? '提交中' : '运行抓取与处理'}
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => {
                      if (profiles.length > 0) {
                        setSelectedProfileId(profiles[0].profile_id);
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

        <Card className="border-sky-200 bg-sky-50/70">
          <CardHeader>
            <CardTitle>当前状态</CardTitle>
            <CardDescription>这一步只负责把文章运行入口迁移到 Profile-only，不改变任务链路结构。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <MetricCard label="输入模型" value="Profile" />
            <MetricCard label="旧参数" value="config_path 已移除" />
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

  const articles = articlesQuery.data?.items ?? [];
  const total = articlesQuery.data?.total ?? 0;
  const pages = articlesQuery.data?.pages ?? 0;

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
        <ArticleErrorState error={articlesQuery.error} title="文章列表加载失败" onRetry={() => void articlesQuery.refetch()} />
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
              <Input id="article-author-id" value={authorId} onChange={(event) => setAuthorId(event.target.value)} placeholder="例如 10461311" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-900" htmlFor="article-source">
                Source
              </label>
              <Input id="article-source" value={source} onChange={(event) => setSource(event.target.value)} placeholder="例如 tgb" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-900" htmlFor="article-trader-id">
                Trader ID
              </label>
              <Input id="article-trader-id" value={traderId} onChange={(event) => setTraderId(event.target.value)} placeholder="例如 trader_a" />
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
                    <th className="px-4 py-3">结果</th>
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
                      <td className="px-4 py-4 text-slate-700">
                        <p>Hash：{article.content_hash ?? '未记录'}</p>
                        <p className="mt-1 text-xs text-slate-500">字数：{article.content_text.length}</p>
                      </td>
                      <td className="px-4 py-4">
                        <a
                          className="inline-flex h-9 items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
                          href={article.source_url}
                          rel="noreferrer"
                          target="_blank"
                        >
                          <ExternalLink className="h-4 w-4" />
                          打开原文
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
                    <MetricCard label="耗时" value={formatDuration(job.result ? (job.result as any)?.workflow_run?.run_context?.duration_ms : null)} />
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

        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)]">
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

  const normalizedMaintenanceMode: MaintenanceMode = cleanup
    ? 'cleanup'
    : rebuildPending
      ? 'rebuild_pending'
      : retryFailed
        ? 'retry_failed'
        : 'normal';

  const runMutation = useMutation({
    mutationFn: async () => {
      const params: Record<string, unknown> = {
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

      return runArticlePipeline({
        params: params as any,
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

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
        <Card>
          <CardHeader>
            <CardTitle>维护入口</CardTitle>
            <CardDescription>重跑选项使用 Checkbox，从指定步骤开始使用下拉选择，DuckDB export 不在页面中出现。</CardDescription>
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

                <div className="grid gap-3 md:grid-cols-2">
                  <CheckboxField
                    label="force"
                    checked={force}
                    onChange={setForce}
                    description="忽略已有中间结果，重新执行相关步骤。"
                    disabled={cleanup || rebuildPending || retryFailed}
                  />
                  <CheckboxField
                    label="skip_crawl"
                    checked={skipCrawl}
                    onChange={setSkipCrawl}
                    description="跳过抓取，只处理已有文章。"
                    disabled={cleanup || rebuildPending || retryFailed}
                  />
                  <CheckboxField
                    label="use_db"
                    checked={useDb}
                    onChange={setUseDb}
                    description="从 raw_articles / DB 模式读取原始文章。"
                    disabled={cleanup}
                  />
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
                    description="清理 articles.jsonl、cleaned、validated、pending、failed 和 checkpoint 文件。"
                  />
                </div>

                <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                  <p className="font-medium text-amber-950">当前维护模式：{modeSummary}</p>
                  <p className="mt-2 leading-6">
                    cleanup 会直接收口到危险清理；rebuild pending / retry failed 会在 process 阶段执行，并在后端按现有语义重建或重试。
                  </p>
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

        <Card className="border-sky-200 bg-sky-50/70">
          <CardHeader>
            <CardTitle>维护边界</CardTitle>
            <CardDescription>维护动作仅在文章模块内收口，不暴露 DuckDB export 入口。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <MetricCard label="可执行身份" value="operator / admin" />
            <MetricCard label="重跑选项" value="Checkbox" />
            <MetricCard label="from_step" value="下拉选择" />
            <MetricCard label="导出入口" value="不展示" />
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
