import { type ReactNode, useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { PageHeader } from '@/components/layout/page-header';
import { ProductPageAdapter } from '@/components/layout/product-page-adapter';
import { ArtifactPanel } from '@/components/artifacts/artifact-panel';
import { EmptyState, JsonViewer, LoadingState, SectionCard, StatusBadge } from '@/components/kit';
import { ErrorState } from '@/components/state/ErrorState';
import { createJob, listJobs } from '@/lib/api/jobs';
import { buildErrorRecoveryState } from '@/lib/error-recovery';
import { formatLocalDateInputOffset } from '@/lib/date';
import { listProfiles } from '@/lib/api/profiles';
import type { JobArtifactRef, JobRecord } from '@/types/jobs';
import { describeStrategyWorkspaceJobType, formatWorkspaceTimestamp, isWorkspacePermissionDenied } from './strategy-workspace-utils';
import { StrategyWorkspaceHistory } from './strategy-workspace-history';

type SubmissionState = {
  jobId: string;
  submittedAt: string;
};

type StrategyAfterClosePageProps = {
  productMode?: boolean;
  navigationTarget?: string;
};

type AfterCloseEvaluation = {
  idea_id?: string;
  symbol?: string;
  entry_price?: number | null;
  current_price?: number | null;
  return_pct?: number | null;
  status?: string;
  partial_data?: boolean;
  fallback_reason?: string | null;
  notes?: string[];
};

type AfterCloseResultDetail = {
  result_id?: string;
  as_of_date?: string;
  generated_at?: string;
  evaluations?: AfterCloseEvaluation[];
  evidence_pack_refs?: string[];
  failure_categories?: string[];
  ranking_features?: Record<string, unknown>;
  postmortem_notes?: string[];
  summary?: string[];
};

type AfterCloseJobResultPayload = {
  as_of_date?: string;
  evaluations_count?: number;
  result?: AfterCloseResultDetail;
  html_path?: string | null;
};

type SubmissionFormState = {
  profileId: string;
  asOfDate: string;
  force: boolean;
  exportHtml: boolean;
};

function sortJobsByCreatedAtDesc(jobs: JobRecord[]) {
  return [...jobs].sort((left, right) => right.created_at.localeCompare(left.created_at));
}

function jobProfileId(job: JobRecord) {
  const params = job.params ?? {};
  if (typeof params.profile_id === 'string' && params.profile_id.trim()) {
    return params.profile_id;
  }
  const profileSnapshotId = job.profile_snapshot?.profile_id;
  return typeof profileSnapshotId === 'string' && profileSnapshotId.trim() ? profileSnapshotId : null;
}

function jobAsOfDate(job: JobRecord) {
  const params = job.params ?? {};
  if (typeof params.as_of_date === 'string' && params.as_of_date.trim()) {
    return params.as_of_date;
  }
  const resultPayload = getAfterCloseJobResult(job);
  if (typeof resultPayload?.as_of_date === 'string' && resultPayload.as_of_date.trim()) {
    return resultPayload.as_of_date;
  }
  return null;
}

function getAfterCloseJobResult(job: JobRecord | null | undefined) {
  const result = job?.result;
  if (!result || typeof result !== 'object') {
    return null;
  }
  return result as AfterCloseJobResultPayload;
}

function getAfterCloseResultDetail(job: JobRecord | null | undefined) {
  const payload = getAfterCloseJobResult(job);
  const result = payload?.result;
  if (!result || typeof result !== 'object') {
    return null;
  }
  return result as AfterCloseResultDetail;
}

function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '未记录';
  }
  const sign = value > 0 ? '+' : '';
  return `${sign}${(value * 100).toFixed(2)}%`;
}

function describeEvaluationStatus(status: string | undefined) {
  const labels: Record<string, string> = {
    ok: '已完成',
    success: '已完成',
    insufficient_sample: '样本不足',
    failed: '处理失败',
    unavailable: '当前不可用',
    pending: '等待处理',
    running: '处理中',
  };
  return status ? labels[status] ?? '状态待确认' : '状态未记录';
}

function describeFallbackReason(reason: string | null | undefined) {
  const labels: Record<string, string> = {
    provider_unavailable: '数据来源暂不可用',
    missing_data: '数据不完整',
    insufficient_sample: '样本不足',
  };
  return reason ? labels[reason] ?? '存在未说明的数据降级' : null;
}

function describeJobError(error: JobRecord['error']) {
  if (!error) {
    return '任务失败，请稍后重试。';
  }
  return '任务失败，请稍后重试。';
}

function summarizeJob(job: JobRecord, productMode = false) {
  const profileId = jobProfileId(job);
  const asOfDate = jobAsOfDate(job);
  const params = job.params ?? {};
  const force = typeof params.force === 'boolean' ? params.force : null;
  const exportHtml = typeof params.export_html === 'boolean' ? params.export_html : null;

  return [
    !productMode && profileId ? `画像 ${profileId}` : null,
    asOfDate ? `分析日期 ${asOfDate}` : null,
    !productMode && force !== null ? `强制 ${force ? '是' : '否'}` : null,
    !productMode && exportHtml !== null ? `导出网页 ${exportHtml ? '是' : '否'}` : null,
  ]
    .filter(Boolean)
    .join(' · ');
}

function jobMatchesProfile(job: JobRecord, profileId: string) {
  if (!profileId) {
    return true;
  }
  return jobProfileId(job) === profileId;
}

function buildAfterCloseRequest({
  profileId,
  asOfDate,
  force,
  exportHtml,
}: SubmissionFormState) {
  return {
    job_type: 'run-after-close',
    created_by: 'web',
    params: {
      profile_id: profileId,
      as_of_date: asOfDate,
      force,
      export_html: exportHtml,
    },
  };
}

function buildPerformanceStats(evaluations: AfterCloseEvaluation[] | null) {
  if (!evaluations) {
    return {
      total: null,
      wins: null,
      losses: null,
      average: null,
      best: null,
      worst: null,
    };
  }

  const validReturns = evaluations
    .map((item) => item.return_pct)
    .filter((value): value is number => typeof value === 'number' && Number.isFinite(value));

  const wins = validReturns.filter((value) => value >= 0).length;
  const losses = validReturns.filter((value) => value < 0).length;
  const total = validReturns.length;
  const average = total ? validReturns.reduce((sum, value) => sum + value, 0) / total : null;
  const best = total ? Math.max(...validReturns) : null;
  const worst = total ? Math.min(...validReturns) : null;

  return {
    total,
    wins,
    losses,
    average,
    best,
    worst,
  };
}

function SummaryTile({ label, value, detail }: { label: string; value: ReactNode; detail?: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <div className="mt-2 break-all text-sm font-medium text-slate-950">{value}</div>
      {detail ? <p className="mt-2 text-sm leading-6 text-slate-600">{detail}</p> : null}
    </div>
  );
}

function ResultRow({ evaluation }: { evaluation: AfterCloseEvaluation }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-base font-medium text-slate-950">{evaluation.symbol ?? '未知标的'}</p>
          <p className="mt-1 text-sm text-slate-600">
            {describeEvaluationStatus(evaluation.status)}
            {evaluation.partial_data ? ' · 部分数据' : ''}
            {evaluation.fallback_reason ? ` · ${describeFallbackReason(evaluation.fallback_reason)}` : ''}
          </p>
        </div>
        <Badge variant="info">{formatPercent(evaluation.return_pct)}</Badge>
      </div>
      {evaluation.notes?.length ? (
        <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-600">
          {evaluation.notes.slice(0, 3).map((note) => (
            <li key={note} className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
              {note}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function ResultSummaryCard({ latestJob, productMode = false }: { latestJob: JobRecord | null; productMode?: boolean }) {
  const resultPayload = getAfterCloseJobResult(latestJob);
  const resultDetail = getAfterCloseResultDetail(latestJob);
  const evaluations = Array.isArray(resultDetail?.evaluations) ? resultDetail.evaluations : null;
  const stats = buildPerformanceStats(evaluations);
  const evaluationsCount =
    typeof resultPayload?.evaluations_count === 'number'
      ? resultPayload.evaluations_count
      : evaluations
        ? evaluations.length
        : null;
  const failed = latestJob?.status === 'failed';

  if (!latestJob) {
    return (
      <div className="space-y-4">
        <EmptyState
          title="暂无盘后结果。"
          description="提交盘后复盘后，这里会展示最近结果、归因、表现和产物。"
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {failed ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm leading-6 text-rose-900">
          <p className="font-medium">盘后任务失败</p>
          <p className="mt-1 break-words text-rose-800">原因：{describeJobError(latestJob.error)}</p>
          {!productMode ? (
            <div className="mt-3 flex flex-wrap gap-2">
              <Link className="text-sm font-medium text-rose-700 hover:underline" to={`/system/jobs/${encodeURIComponent(latestJob.id)}`}>
                打开任务详情
              </Link>
              <Link className="text-sm font-medium text-rose-700 hover:underline" to={`/system/jobs?job_type=run-after-close`}>
                查看任务列表
              </Link>
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <SummaryTile
          label={productMode ? '最近结果' : 'Job ID'}
          value={productMode ? describeStrategyWorkspaceJobType(latestJob.job_type) : latestJob.id}
          detail={productMode ? summarizeJob(latestJob, true) : summarizeJob(latestJob)}
        />
        <SummaryTile label="状态" value={<StatusBadge value={latestJob.status} />} detail={formatWorkspaceTimestamp(latestJob.created_at)} />
        <SummaryTile
          label={productMode ? '复盘日期' : '执行日期'}
          value={resultPayload?.as_of_date ?? jobAsOfDate(latestJob) ?? '未记录'}
          detail={resultPayload?.html_path && !productMode ? `HTML ${resultPayload.html_path}` : '当前结果已生成'}
        />
        <SummaryTile
          label={productMode ? '复盘数' : '评估数'}
          value={evaluationsCount === null ? '未记录' : String(evaluationsCount)}
          detail={productMode ? '展示当前可用的最近复盘结果。' : resultDetail?.result_id ? `Result ${resultDetail.result_id}` : '暂无结果 ID'}
        />
      </div>

      {resultDetail ? (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
          <div className="space-y-4">
            <Card className="border-slate-200 bg-white shadow-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg text-slate-950">盘后结果</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-3 md:grid-cols-2">
                  <SummaryTile label="总评估数" value={stats.total ?? '未记录'} />
                  <SummaryTile label="正收益" value={stats.wins ?? '未记录'} detail={stats.losses === null ? '负收益未记录' : `负收益 ${stats.losses}`} />
                  <SummaryTile label="平均收益" value={formatPercent(stats.average)} />
                  <SummaryTile label="最佳 / 最差" value={`${formatPercent(stats.best)} / ${formatPercent(stats.worst)}`} />
                </div>

                {resultDetail.summary?.length ? (
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-slate-500">后端摘要</p>
                    <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-700">
                      {resultDetail.summary.map((item) => (
                        <li key={item} className="rounded-xl border border-slate-200 bg-white px-3 py-2">
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                {evaluations?.length ? (
                  <div className="space-y-3">
                    <p className="text-sm font-medium text-slate-950">最近评估明细</p>
                    <div className="space-y-3">
                      {evaluations.slice(0, 5).map((evaluation) => (
                        <ResultRow key={`${evaluation.symbol ?? 'unknown'}-${evaluation.idea_id ?? evaluation.status ?? 'item'}`} evaluation={evaluation} />
                      ))}
                    </div>
                  </div>
                ) : (
                  <EmptyState title="暂无评估明细。" description="后端 evaluation 列表为空时，这里会保留结果摘要与产物入口。" />
                )}
              </CardContent>
            </Card>

            <Card className="border-slate-200 bg-white shadow-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg text-slate-950">今日策略表现</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                  <SummaryTile label="有效评估" value={stats.total ?? '未记录'} />
                  <SummaryTile label="胜率" value={stats.total && stats.wins !== null ? `${Math.round((stats.wins / stats.total) * 100)}%` : '未记录'} />
                  <SummaryTile label="平均收益" value={formatPercent(stats.average)} />
                  <SummaryTile label="收益区间" value={`${formatPercent(stats.best)} / ${formatPercent(stats.worst)}`} />
                </div>

                {!productMode ? (
                  <JsonViewer
                    title="ranking_features"
                    value={resultDetail.ranking_features ?? {}}
                  />
                ) : null}
              </CardContent>
            </Card>
          </div>

          <div className="space-y-4">
            <Card className="border-slate-200 bg-white shadow-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg text-slate-950">信号归因</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">失败归因</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {resultDetail.failure_categories?.length ? (
                      resultDetail.failure_categories.map((item) => (
                        <Badge key={item} variant="warning">
                          {item}
                        </Badge>
                      ))
                    ) : (
                      <span className="text-sm text-slate-600">暂无失败归因。</span>
                    )}
                  </div>
                </div>

                <div>
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">复盘说明</p>
                  {resultDetail.postmortem_notes?.length ? (
                    <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-700">
                      {resultDetail.postmortem_notes.map((item) => (
                        <li key={item} className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
                          {item}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-3 text-sm text-slate-600">暂无复盘说明。</p>
                  )}
                </div>

                {!productMode ? <div>
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Evidence pack refs</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {resultDetail.evidence_pack_refs?.length ? (
                      resultDetail.evidence_pack_refs.map((item) => (
                        <Badge key={item} variant="info">
                          {item}
                        </Badge>
                      ))
                    ) : (
                      <span className="text-sm text-slate-600">暂无证据包引用。</span>
                    )}
                  </div>
                </div> : null}
              </CardContent>
            </Card>

            {!productMode ? <Card className="border-slate-200 bg-white shadow-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg text-slate-950">产物与来源</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-3 md:grid-cols-2">
                  <SummaryTile
                    label="来源 Job"
                    value={latestJob.id}
                    detail={`${describeStrategyWorkspaceJobType(latestJob.job_type)} · ${latestJob.status}`}
                  />
                  <SummaryTile
                    label="来源日期"
                    value={jobAsOfDate(latestJob) ?? resultPayload?.as_of_date ?? '未记录'}
                    detail={latestJob.profile_snapshot?.profile_id ? `来源画像 ${latestJob.profile_snapshot.profile_id}` : '来源画像未记录'}
                  />
                </div>

                {!productMode ? (
                  <div className="flex flex-wrap gap-2">
                    <Link
                      className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-sky-700 transition-colors hover:bg-slate-50"
                      to={`/system/jobs/${encodeURIComponent(latestJob.id)}`}
                    >
                      查看任务详情
                    </Link>
                    <Link
                      className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-sky-700 transition-colors hover:bg-slate-50"
                      to={`/artifacts?jobId=${encodeURIComponent(latestJob.id)}`}
                    >
                      前往产物中心
                    </Link>
                  </div>
                ) : null}

                {resultPayload?.html_path ? (
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
                    <p className="text-xs uppercase tracking-[0.16em] text-slate-500">导出 HTML</p>
                    <p className="mt-2 break-all text-slate-950">{resultPayload.html_path}</p>
                  </div>
                ) : !productMode ? (
                  <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                    当前结果未导出 HTML。
                  </div>
                ) : (
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                    当前复盘结果已就绪。
                  </div>
                )}

                {!productMode ? <ArtifactPanel artifacts={(latestJob.artifacts ?? []) as JobArtifactRef[]} /> : null}
              </CardContent>
            </Card> : null}
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <EmptyState
            title="暂无可展示的盘后结果。"
            description="最近盘后 Job 还没有写入结构化 result，或当前画像下暂时没有可用记录。"
          />
        </div>
      )}
    </div>
  );
}

function StrategyAfterCloseBody({ productMode = false, navigationTarget = '/daily' }: StrategyAfterClosePageProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const today = useMemo(() => formatLocalDateInputOffset(0), []);
  const [formState, setFormState] = useState<SubmissionFormState>({
    profileId: '',
    asOfDate: today,
    force: false,
    exportHtml: false,
  });
  const [submissionState, setSubmissionState] = useState<SubmissionState | null>(null);
  const [submissionError, setSubmissionError] = useState<string | null>(null);

  const profilesQuery = useQuery({
    queryKey: ['strategy-after-close', 'profiles'],
    queryFn: () => listProfiles({ skip: 0, limit: 50 }),
    staleTime: 30_000,
  });

  const jobsQuery = useQuery({
    queryKey: ['strategy-after-close', 'jobs'],
    queryFn: () => listJobs({ job_type: 'run-after-close', limit: 20 }),
    staleTime: 15_000,
  });

  const profileItems = profilesQuery.data?.items ?? [];
  useEffect(() => {
    if (!formState.profileId && profileItems.length > 0) {
      setFormState((current) => ({ ...current, profileId: profileItems[0].profile_id }));
      return;
    }
    if (formState.profileId && !profileItems.some((item) => item.profile_id === formState.profileId)) {
      setFormState((current) => ({ ...current, profileId: profileItems[0]?.profile_id ?? '' }));
    }
  }, [formState.profileId, profileItems]);

  const visibleJobs = useMemo(
    () => sortJobsByCreatedAtDesc((jobsQuery.data?.items ?? []).filter((job) => jobMatchesProfile(job, formState.profileId))),
    [formState.profileId, jobsQuery.data?.items],
  );
  const latestJob = visibleJobs[0] ?? null;
  const queryError = profilesQuery.error ?? jobsQuery.error;
  const permissionDenied = isWorkspacePermissionDenied(queryError);
  const isLoading = profilesQuery.isLoading || jobsQuery.isLoading;
  const hasProfiles = profileItems.length > 0;

  const submissionMutation = useMutation({
    mutationFn: async (payload: SubmissionFormState) => createJob(buildAfterCloseRequest(payload)),
    onSuccess: async (result) => {
      setSubmissionError(null);
      setSubmissionState({
        jobId: result.job.id,
        submittedAt: new Date().toISOString(),
      });
      await Promise.all([
        jobsQuery.refetch(),
        queryClient.invalidateQueries({ queryKey: ['jobs'] }),
      ]);
    },
    onError: () => {
      setSubmissionState(null);
      setSubmissionError('盘后复盘提交失败，请稍后重试。');
    },
  });

  if (productMode) {
    const hasPartialData = false;
    const queryState = isLoading ? 'loading' : permissionDenied ? 'permission_denied' : queryError ? 'error' : !hasProfiles ? 'empty' : hasPartialData ? 'partial' : 'ready';
    const selectedProfile = profileItems.find((item) => item.profile_id === formState.profileId) ?? profileItems[0] ?? null;
    const latestProductJob = visibleJobs[0] ?? null;

    return (
      <ProductPageAdapter
        title="今日盘后"
        queryState={queryState}
        purpose="复盘今日执行结果，整理收盘后的观察、归因和下一步优化建议。"
        inputDescription="需要当前可用画像和盘后复盘日期。"
        processingDescription="系统会根据今日结果整理复盘内容，并保留最近复盘记录。"
        outputDescription="输出今日盘后复盘摘要、最近结果和下一步操作。"
        input={
          <div className="grid gap-3 md:grid-cols-2">
            <label className="space-y-2 text-sm text-slate-700">
              <span>目标画像</span>
              <Select
                aria-label="目标画像"
                value={formState.profileId}
                onChange={(event) => setFormState((current) => ({ ...current, profileId: event.target.value }))}
              >
                {profileItems.map((profile) => (
                  <option key={profile.profile_id} value={profile.profile_id}>
                    {profile.name}
                  </option>
                ))}
              </Select>
            </label>

            <label className="space-y-2 text-sm text-slate-700">
              <span>复盘日期</span>
              <Input
                aria-label="复盘日期"
                type="date"
                value={formState.asOfDate}
                onChange={(event) => setFormState((current) => ({ ...current, asOfDate: event.target.value }))}
              />
            </label>

          </div>
        }
        businessAction={{ label: '生成盘后复盘', onClick: () => void submissionMutation.mutateAsync(formState) }}
        result={
          <div className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">目标画像</p>
                <p className="mt-2 text-sm font-medium text-slate-950">{selectedProfile?.name ?? '未选择'}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">复盘日期</p>
                <p className="mt-2 text-sm font-medium text-slate-950">{formState.asOfDate}</p>
              </div>
            </div>

            <ResultSummaryCard latestJob={latestProductJob} productMode />

            <div className="flex flex-wrap gap-2">
              <Link
                className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-sky-700 transition-colors hover:bg-slate-50"
                to={navigationTarget}
              >
                返回今日总览
              </Link>
            </div>
          </div>
        }
      />
    );
  }

  if (isLoading) {
    return (
      <main className="page-stack">
      <PageHeader
        kicker="盘后复盘"
        title="盘后复盘"
        description="盘后复盘页负责展示结果、归因、表现与产物。"
        actionLabel="返回概览"
          onAction={() => {
            navigate('/daily');
          }}
        />
        <LoadingState label="正在加载盘后复盘" description="正在读取画像、盘后任务和最近结果。" />
      </main>
    );
  }

  if (queryError) {
    return (
      <main className="page-stack">
        <PageHeader
          kicker="盘后复盘"
          title="盘后复盘"
          description="盘后复盘页负责展示结果、归因、表现与产物。"
          actionLabel="返回概览"
          onAction={() => {
            navigate('/daily');
          }}
        />
        <ErrorState
          {...buildErrorRecoveryState(queryError, 'strategy')}
          onRetry={permissionDenied ? undefined : () => void Promise.all([profilesQuery.refetch(), jobsQuery.refetch()])}
          actions={[
            { label: '查看任务列表', to: '/system/jobs?job_type=run-after-close' },
            { label: '前往配置管理', to: '/profiles' },
          ]}
        />
      </main>
    );
  }

  if (!hasProfiles) {
    return (
      <main className="page-stack">
        <PageHeader
          kicker="盘后复盘"
          title="盘后复盘"
          description="盘后复盘页负责展示结果、归因、表现与产物。"
          actionLabel="返回概览"
          onAction={() => {
            navigate('/daily');
          }}
        />
        <EmptyState
          title="暂无可用画像。"
          description="先到配置管理创建或导入画像，再提交盘后复盘。"
          actionLabel="前往配置管理"
          onAction={() => {
            navigate('/profiles');
          }}
        />
      </main>
    );
  }

  return (
    <main className="page-stack">
      <PageHeader
        kicker="盘后复盘"
        title="盘后复盘"
        description="盘后复盘页负责展示后端结果、信号归因、今日表现与产物链接。"
        actionLabel="返回概览"
        onAction={() => {
          navigate('/daily');
        }}
      />

      {submissionState ? (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm leading-6 text-emerald-950">
          <p className="font-medium">盘后复盘已提交</p>
          <p className="mt-1">
            Job {submissionState.jobId} · {formatWorkspaceTimestamp(submissionState.submittedAt)}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
              <Link className="text-sm font-medium text-emerald-700 hover:underline" to={`/system/jobs/${encodeURIComponent(submissionState.jobId)}`}>
              打开任务详情
            </Link>
            <Link className="text-sm font-medium text-emerald-700 hover:underline" to="/system/jobs?job_type=run-after-close">
              查看任务列表
            </Link>
          </div>
        </div>
      ) : null}

      {submissionError ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm leading-6 text-rose-900">
          <p className="font-medium">提交失败</p>
          <p className="mt-1">{submissionError}</p>
        </div>
      ) : null}

      <section className="grid gap-4 xl:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
        <SectionCard
          title="盘后执行"
          description="选择画像和执行日期，提交盘后复盘任务，结果会回到任务详情。"
        >
          <form
            className="space-y-4"
            onSubmit={(event) => {
              event.preventDefault();
              if (!formState.profileId) {
                return;
              }
              setSubmissionError(null);
              setSubmissionState(null);
              void submissionMutation.mutateAsync(formState);
            }}
          >
            <div className="grid gap-4 md:grid-cols-2">
              <label className="space-y-2">
                <span className="text-sm font-medium text-slate-700">画像</span>
                <Select
                  aria-label="画像"
                  value={formState.profileId}
                  onChange={(event) => setFormState((current) => ({ ...current, profileId: event.target.value }))}
                >
                  {profileItems.map((profile) => (
                    <option key={profile.profile_id} value={profile.profile_id}>
                      {profile.name} · {profile.profile_id}
                    </option>
                  ))}
                </Select>
              </label>

              <label className="space-y-2">
                <span className="text-sm font-medium text-slate-700">执行日期</span>
                <Input
                  aria-label="执行日期"
                  type="date"
                  value={formState.asOfDate}
                  onChange={(event) => setFormState((current) => ({ ...current, asOfDate: event.target.value }))}
                />
              </label>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                <input
                  aria-label="强制执行"
                  checked={formState.force}
                  className="size-4 rounded border-slate-300 text-sky-600 focus:ring-sky-400"
                  onChange={(event) => setFormState((current) => ({ ...current, force: event.target.checked }))}
                  type="checkbox"
                />
                <span>强制</span>
              </label>

              <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                <input
                  aria-label="导出网页"
                  checked={formState.exportHtml}
                  className="size-4 rounded border-slate-300 text-sky-600 focus:ring-sky-400"
                  onChange={(event) => setFormState((current) => ({ ...current, exportHtml: event.target.checked }))}
                  type="checkbox"
                />
                <span>导出网页</span>
              </label>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <Button type="submit" disabled={submissionMutation.isPending || !formState.profileId}>
                {submissionMutation.isPending ? '提交中' : '提交盘后复盘'}
              </Button>
              <Link
                className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
                to="/profiles"
              >
                前往配置管理
              </Link>
            </div>
          </form>
        </SectionCard>

        <SectionCard
          title="最近盘后结果"
          description="仅展示当前画像对应的最近盘后 Job 结果。"
          action={<StatusBadge value={latestJob?.status ?? 'pending'} />}
        >
          <ResultSummaryCard latestJob={latestJob} />
        </SectionCard>
      </section>

      <SectionCard
        title="最近盘后任务"
        description="失败任务可以直接进入任务详情。"
      >
        {visibleJobs.length ? (
          <StrategyWorkspaceHistory jobs={visibleJobs} isLoading={false} error={null} onRetry={() => void jobsQuery.refetch()} />
        ) : (
          <EmptyState
            title="暂无盘后任务。"
            description="提交盘后复盘任务后，这里会显示最近执行记录。"
          />
        )}
      </SectionCard>
    </main>
  );
}

export function StrategyAfterClosePage(props: StrategyAfterClosePageProps) {
  return <StrategyAfterCloseBody {...props} />;
}
