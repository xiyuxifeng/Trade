import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { PageHeader } from '@/components/layout/page-header';
import { ApiError } from '@/lib/api/http';
import { listJobs } from '@/lib/api/jobs';
import { getArticlePipeline, runArticlePipeline } from '@/lib/api/pipelines';
import type { JobRecord, JobsListResponse } from '@/types/jobs';
import type { PipelineDetail, PipelineParamsSchemaField, PipelineDetailResponse } from '@/types/pipeline';

type PipelineInputMode = 'config_path' | 'profile';

const DEFAULT_MODE: PipelineInputMode = 'config_path';

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return 'article_pipeline 数据加载失败';
}

function getStatusLabel(status: string) {
  const mapping: Record<string, string> = {
    pending: '等待中',
    running: '运行中',
    success: '成功',
    failed: '失败',
    cancelled: '已取消',
  };
  return mapping[status] ?? status;
}

function statusVariant(status: string) {
  if (status === 'success') return 'success';
  if (status === 'failed' || status === 'cancelled') return 'destructive';
  if (status === 'running') return 'info';
  return 'warning';
}

function formatTimestamp(value: string | null | undefined) {
  if (!value) return '未记录';
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function getFieldErrors(error: unknown) {
  if (!(error instanceof ApiError)) {
    return {} as Record<PipelineInputMode, string>;
  }
  const detail = error.payload?.detail;
  if (!detail || typeof detail !== 'object') {
    return {} as Record<PipelineInputMode, string>;
  }
  const fields = (detail as { fields?: unknown }).fields;
  if (!fields || typeof fields !== 'object') {
    return {} as Record<PipelineInputMode, string>;
  }

  const nextErrors: Partial<Record<PipelineInputMode, string>> = {};
  const configPathMessage = (fields as Record<string, unknown>).config_path;
  const profileMessage = (fields as Record<string, unknown>).profile;
  if (typeof configPathMessage === 'string' && configPathMessage.trim()) {
    nextErrors.config_path = configPathMessage;
  }
  if (typeof profileMessage === 'string' && profileMessage.trim()) {
    nextErrors.profile = profileMessage;
  }
  return nextErrors as Record<PipelineInputMode, string>;
}

function summarizeParams(job: JobRecord) {
  const params = job.params as Record<string, unknown>;
  if (typeof params.config_path === 'string' && params.config_path.trim()) {
    return params.config_path;
  }
  if (typeof params.profile === 'string' && params.profile.trim()) {
    return params.profile;
  }
  return JSON.stringify(params);
}

function SchemaFieldRow({ fieldName, field }: { fieldName: string; field: PipelineParamsSchemaField }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-medium text-slate-100">{fieldName}</p>
          <p className="mt-1 text-sm text-slate-400">{field.description ?? '未提供说明'}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge variant="info">{field.type}</Badge>
          <Badge variant={field.required ? 'warning' : 'default'}>{field.required ? '必填' : '可选'}</Badge>
        </div>
      </div>
      {field.enum?.length ? <p className="mt-2 text-xs text-slate-500">候选值：{field.enum.join(' / ')}</p> : null}
    </div>
  );
}

function RecentJobRow({ job, onOpen }: { job: JobRecord; onOpen: () => void }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-medium text-slate-100">{job.id}</p>
          <p className="mt-1 text-xs text-slate-500">
            {formatTimestamp(job.created_at)} · {summarizeParams(job)}
          </p>
        </div>
        <Badge variant={statusVariant(job.status)}>{getStatusLabel(job.status)}</Badge>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <Button size="sm" variant="outline" onClick={onOpen}>
          打开 Job Detail
        </Button>
      </div>
    </div>
  );
}

export function ArticlePipelinePage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [mode, setMode] = useState<PipelineInputMode>(DEFAULT_MODE);
  const [value, setValue] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<PipelineInputMode, string>>>({});
  const [submitMessage, setSubmitMessage] = useState<string | null>(null);
  const [submittedJobId, setSubmittedJobId] = useState<string | null>(null);

  const pipelineQuery = useQuery<PipelineDetailResponse, ApiError>({
    queryKey: ['article-pipeline'],
    queryFn: getArticlePipeline,
    staleTime: 30_000,
  });

  const recentJobsQuery = useQuery<JobsListResponse, ApiError>({
    queryKey: ['jobs', { jobType: 'pipeline-run', limit: 5 }],
    queryFn: () => listJobs({ job_type: 'pipeline-run', limit: 5 }),
    staleTime: 15_000,
  });

  const pipeline: PipelineDetail | null = pipelineQuery.data?.pipeline ?? null;
  const schemaFields = useMemo(
    () => Object.entries(pipeline?.workflow?.job_definition?.params_schema?.fields ?? {}),
    [pipeline],
  );
  const recentJobs = recentJobsQuery.data?.items ?? [];

  useEffect(() => {
    if (submittedJobId) {
      navigate(`/jobs/${encodeURIComponent(submittedJobId)}`);
    }
  }, [navigate, submittedJobId]);

  useEffect(() => {
    setFieldErrors({});
    setSubmitMessage(null);
  }, [mode]);

  const runMutation = useMutation({
    mutationFn: async (request: { params: Record<string, unknown> }) => {
      return runArticlePipeline({
        params: request.params,
        created_by: 'web',
        confirmed: false,
      });
    },
    onSuccess: async (data) => {
      setFieldErrors({});
      setSubmitMessage('article_pipeline 已提交，正在跳转到 Job Detail。');
      setSubmittedJobId(data.job.id);
      await queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
    onError: (error: unknown) => {
      setFieldErrors(getFieldErrors(error));
      setSubmitMessage(getErrorMessage(error));
    },
  });

  function submitForm() {
    const trimmedValue = value.trim();
    if (!trimmedValue) {
      setFieldErrors({
        [mode]: '请输入 config_path 或 Profile 值。',
      });
      setSubmitMessage(null);
      return;
    }

    setFieldErrors({});
    setSubmitMessage(null);
    runMutation.mutate({
      params: {
        [mode]: trimmedValue,
      },
    });
  }

  const isLoading = pipelineQuery.isLoading;
  const pipelineError = pipelineQuery.error;
  const recentJobsError = recentJobsQuery.error;

  return (
    <main className="page-stack">
      {/* <PageHeader
        kicker="文章"
        title="Article Pipeline"
        description="通过 Web 触发 article_pipeline，检查参数约束，查看最近运行记录，并直接跳到 Job Detail。"
      /> */}

      {submitMessage ? (
        <div className="rounded-2xl border border-sky-500/30 bg-sky-500/10 px-4 py-3 text-sm text-sky-100">{submitMessage}</div>
      ) : null}

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(340px,0.85fr)]">
        <Card>
          <CardHeader>
            <CardTitle>Pipeline 概览</CardTitle>
            <CardDescription>只展示 article_pipeline 的正式入口和 schema 摘要，不在页面内编排执行逻辑。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-5 w-1/2" />
                <Skeleton className="h-4 w-5/6" />
                <Skeleton className="h-20 w-full" />
              </div>
            ) : pipelineError ? (
              <div className="space-y-3 rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-100">
                <p>{getErrorMessage(pipelineError)}</p>
                <Button size="sm" variant="outline" onClick={() => pipelineQuery.refetch()}>
                  重试
                </Button>
              </div>
            ) : pipeline ? (
              <>
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                    <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Pipeline ID</p>
                    <p className="mt-1 break-all text-sm text-slate-100">{pipeline.pipeline_id}</p>
                  </div>
                  <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                    <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Workflow</p>
                    <p className="mt-1 break-all text-sm text-slate-100">{pipeline.workflow.workflow_id}</p>
                  </div>
                  <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                    <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Job Type</p>
                    <p className="mt-1 break-all text-sm text-slate-100">{pipeline.workflow.job_type}</p>
                  </div>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Pipeline 说明</p>
                  <p className="mt-2 text-sm leading-6 text-slate-300">{pipeline.description}</p>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                  <p className="text-sm font-medium text-slate-100">{pipeline.workflow.title}</p>
                  <p className="mt-2 text-sm leading-6 text-slate-300">{pipeline.workflow.description}</p>
                </div>
                <div>
                  <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                    <h3 className="text-sm font-semibold text-slate-100">输入参数</h3>
                    <Badge variant="info">
                      {pipeline.workflow.job_definition?.params_schema?.allow_additional_fields ? '允许额外字段' : '仅 schema 字段'}
                    </Badge>
                  </div>
                  {schemaFields.length ? (
                    <div className="space-y-3">
                      {schemaFields.map(([fieldName, field]) => (
                        <SchemaFieldRow key={fieldName} fieldName={fieldName} field={field} />
                      ))}
                    </div>
                  ) : (
                    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">
                      当前 pipeline 没有可编辑的参数定义。
                    </div>
                  )}
                </div>
              </>
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>运行表单</CardTitle>
            <CardDescription>在 config_path 和 Profile 之间切换，提交后进入 Job Detail。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3">
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-200" htmlFor="article-pipeline-mode">
                  参数类型
                </label>
                <Select
                  id="article-pipeline-mode"
                  value={mode}
                  onChange={(event) => setMode(event.target.value as PipelineInputMode)}
                  disabled={isLoading || Boolean(pipelineError)}
                >
                  <option value="config_path">config_path</option>
                  <option value="profile">Profile</option>
                </Select>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-200" htmlFor="article-pipeline-value">
                  {mode}
                </label>
                <Input
                  id="article-pipeline-value"
                  aria-invalid={Boolean(fieldErrors[mode])}
                  aria-describedby={fieldErrors[mode] ? 'article-pipeline-value-error' : undefined}
                  placeholder={mode === 'config_path' ? 'config/articles.yaml' : 'default-profile'}
                  value={value}
                  onChange={(event) => {
                    setValue(event.target.value);
                    setFieldErrors((current) => ({ ...current, [mode]: undefined }));
                  }}
                  disabled={isLoading || Boolean(pipelineError)}
                />
                {fieldErrors[mode] ? (
                  <p id="article-pipeline-value-error" className="text-sm text-rose-300">
                    {fieldErrors[mode]}
                  </p>
                ) : null}
              </div>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-300">
              <p className="font-medium text-slate-100">常见失败原因</p>
              <ul className="mt-2 space-y-2">
                <li>config_path 不存在、写错，或者运行账号没有读取权限。</li>
                <li>Profile 与当前环境不匹配，导致配置加载失败。</li>
                <li>上游抓取、清洗或抽取步骤失败，Job 会在 Job Detail 的日志里保留现场。</li>
                <li>任务被取消、worker 中断，或者队列出现短暂拥塞。</li>
              </ul>
            </div>

            <div className="flex items-center gap-3">
              <Button onClick={submitForm} disabled={isLoading || Boolean(pipelineError) || runMutation.isPending}>
                {runMutation.isPending ? '提交中' : '运行 article_pipeline'}
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setMode(DEFAULT_MODE);
                  setValue('');
                  setFieldErrors({});
                  setSubmitMessage(null);
                }}
              >
                重置
              </Button>
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle>最近 article_pipeline jobs</CardTitle>
                <CardDescription>这里只列出 article_pipeline 触发的最近记录，方便直接打开详情和日志。</CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={() => recentJobsQuery.refetch()} disabled={recentJobsQuery.isFetching}>
                {recentJobsQuery.isFetching ? '刷新中' : '刷新'}
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {recentJobsQuery.isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-20 w-full" />
              </div>
            ) : recentJobsError ? (
              <div className="space-y-3 rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-100">
                <p>{getErrorMessage(recentJobsError)}</p>
                <Button size="sm" variant="outline" onClick={() => recentJobsQuery.refetch()}>
                  重试
                </Button>
              </div>
            ) : recentJobs.length ? (
              <div className="space-y-3">
                {recentJobs.map((job) => (
                  <RecentJobRow key={job.id} job={job} onOpen={() => navigate(`/jobs/${encodeURIComponent(job.id)}`)} />
                ))}
              </div>
            ) : (
              <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">
                暂无 article_pipeline 运行记录。
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>失败定位</CardTitle>
            <CardDescription>如果运行失败，先去 Job Detail 看 logs、artifacts 和 audit trail。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-slate-300">
            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
              <p className="font-medium text-slate-100">定位顺序</p>
              <ol className="mt-2 space-y-2 pl-4">
                <li>打开对应 Job Detail。</li>
                <li>检查错误 message 和 log 文件。</li>
                <li>如果产生产物，查看 artifacts 和 result。</li>
                <li>再回到这里补 config_path 或 Profile。</li>
              </ol>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
              <p className="font-medium text-slate-100">页面状态覆盖</p>
              <ul className="mt-2 space-y-2">
                <li>API unavailable: 概览或最近任务加载失败时显示重试。</li>
                <li>validation error: 本地空值校验和后端字段错误都会落到表单下方。</li>
                <li>running / success / failed: 最近 jobs 里直接用状态徽标展示。</li>
                <li>empty history: 最近任务为空时显示空态提示。</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
