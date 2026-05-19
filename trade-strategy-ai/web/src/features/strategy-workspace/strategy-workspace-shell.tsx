import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { PageHeader } from '@/components/layout/page-header';
import { ErrorState } from '@/components/state/ErrorState';
import { formatLocalDateInputOffset } from '@/lib/date';
import { getProfile, listProfiles } from '@/lib/api/profiles';
import { listJobs } from '@/lib/api/jobs';
import { listArtifacts } from '@/lib/api/artifacts';
import { getStrategyVersion, listStrategyVersions } from '@/lib/api/strategyStudio';
import { buildErrorRecoveryState } from '@/lib/error-recovery';
import type { ProfileDetailResponse, ProfileRecord } from '@/types/profile';
import type { JobRecord } from '@/types/jobs';
import type { ArtifactRecord } from '@/types/artifacts';
import type { StrategyVersionSummaryItem } from '@/types/strategyStudio';
import { StrategyWorkspaceActions } from './strategy-workspace-actions';
import { StrategyWorkspaceArtifacts } from './strategy-workspace-artifacts';
import { StrategyWorkspaceHistory } from './strategy-workspace-history';
import { StrategyWorkspaceCandidate } from './strategy-workspace-candidate';
import {
  formatWorkspaceTimestamp,
  isWorkspacePermissionDenied,
  selectLatestProfileSnapshot,
  selectLatestSnapshotConfigPath,
} from './strategy-workspace-utils';

const STRATEGY_JOB_TYPES = new Set(['strategy-build', 'run-pre-market', 'run-after-close']);

function sortByDateDesc<
  T extends {
    created_at?: string | null;
    strategy_date?: string | null;
    version_id?: string;
    id?: string;
    modified_at?: string | null;
    name?: string;
    kind?: string;
    source?: string;
  },
>(items: T[]) {
  return [...items].sort((left, right) => {
    const leftDate = left.strategy_date ?? left.created_at ?? left.modified_at ?? left.version_id ?? left.id ?? '';
    const rightDate = right.strategy_date ?? right.created_at ?? right.modified_at ?? right.version_id ?? right.id ?? '';
    return String(leftDate).localeCompare(String(rightDate));
  });
}

function SummaryTile({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 break-all text-sm font-medium text-slate-950">{value}</p>
    </div>
  );
}

function ProfilesLoadingCard() {
  return <Skeleton className="h-52 w-full bg-slate-100" />;
}

function ProfileDetailState({
  profile,
  detail,
  isLoading,
  error,
  onRetry,
}: {
  profile: ProfileRecord | null;
  detail: ProfileDetailResponse | null;
  isLoading: boolean;
  error: unknown;
  onRetry: () => void;
}) {
  const snapshot = selectLatestProfileSnapshot(detail);
  const configPath = selectLatestSnapshotConfigPath(detail);
  const permissionDenied = isWorkspacePermissionDenied(error);

  return (
    <Card className="border-slate-200 bg-white shadow-sm">
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <Badge variant="info" className="w-fit">
              运行上下文
            </Badge>
            <CardTitle className="mt-2 text-slate-950">trader / date / profile</CardTitle>
            <CardDescription className="text-slate-600">
              选择正式 profile 后，会自动读取最新 snapshot 并带出 config_path。
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <SummaryTile label="Profile" value={profile ? `${profile.name} · ${profile.profile_id}` : '未选择'} />
          <SummaryTile label="环境" value={profile?.environment ?? '未选择'} />
          <SummaryTile label="版本" value={profile?.version ?? '未选择'} />
          <SummaryTile label="最新快照" value={snapshot?.snapshot_id ?? '暂无'} />
        </div>

        {isLoading ? (
          <ProfilesLoadingCard />
        ) : error ? (
          <ErrorState
            {...buildErrorRecoveryState(error, 'strategy')}
            onRetry={permissionDenied ? undefined : onRetry}
          />
        ) : detail ? (
          <div className="grid gap-3 xl:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">config_path</p>
              <p className="mt-2 break-all text-slate-950">{configPath ?? '暂无最新 snapshot'}</p>
              <p className="mt-3 text-slate-600">
                最新快照：{snapshot ? `${snapshot.snapshot_id} · ${formatWorkspaceTimestamp(snapshot.captured_at)}` : '暂无'}
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">说明</p>
              <p className="mt-2 leading-6 text-slate-700">
                该页面只读取 profile 的最新 snapshot，不会把服务器绝对路径暴露到前端，也不会在前端计算策略结果。
              </p>
            </div>
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
            选择一个 profile 后，这里会展示最新 snapshot 与 config_path。
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function StrategyWorkspaceShell() {
  const navigate = useNavigate();
  const [traderId, setTraderId] = useState('trader_a');
  const [strategyDate, setStrategyDate] = useState(formatLocalDateInputOffset(0));
  const [selectedProfileId, setSelectedProfileId] = useState('');
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);
  const [submissionMessage, setSubmissionMessage] = useState<string | null>(null);
  const [submissionJobId, setSubmissionJobId] = useState<string | null>(null);

  const profilesQuery = useQuery({
    queryKey: ['strategy-workspace', 'profiles'],
    queryFn: () => listProfiles({ skip: 0, limit: 50 }),
    staleTime: 30_000,
  });

  const profileItems = profilesQuery.data?.items ?? [];

  useEffect(() => {
    if (!selectedProfileId && profileItems.length > 0) {
      setSelectedProfileId(profileItems[0].profile_id);
    }
  }, [profileItems, selectedProfileId]);

  const selectedProfile = useMemo(
    () => profileItems.find((item) => item.profile_id === selectedProfileId) ?? null,
    [profileItems, selectedProfileId],
  );

  const profileDetailQuery = useQuery({
    queryKey: ['strategy-workspace', 'profile-detail', selectedProfileId],
    queryFn: () => getProfile(selectedProfileId),
    enabled: Boolean(selectedProfileId),
    staleTime: 30_000,
  });

  const selectedProfileDetailRaw = profileDetailQuery.data ?? null;
  const selectedProfileDetail =
    selectedProfileDetailRaw?.profile.profile_id === selectedProfileId ? selectedProfileDetailRaw : null;
  const latestSnapshot = selectLatestProfileSnapshot(selectedProfileDetail);
  const configPath = selectLatestSnapshotConfigPath(selectedProfileDetail) ?? '';
  const profileDetailLoading = profileDetailQuery.isLoading || (profileDetailQuery.isFetching && !selectedProfileDetail);

  const jobsQuery = useQuery({
    queryKey: ['strategy-workspace', 'jobs'],
    queryFn: () => listJobs({ limit: 30 }),
    staleTime: 30_000,
  });

  const strategyJobs = useMemo(
    () =>
      sortByDateDesc((jobsQuery.data?.items ?? []).filter((job) => STRATEGY_JOB_TYPES.has(job.job_type))) as JobRecord[],
    [jobsQuery.data?.items],
  );

  const versionsQuery = useQuery({
    queryKey: ['strategy-workspace', 'versions', traderId],
    queryFn: () => listStrategyVersions({ trader_id: traderId.trim() || undefined, limit: 12 }),
    staleTime: 30_000,
  });

  const versionItems = useMemo(
    () => sortByDateDesc(versionsQuery.data?.items ?? []) as StrategyVersionSummaryItem[],
    [versionsQuery.data?.items],
  );

  useEffect(() => {
    if (versionItems.length === 0) {
      if (selectedVersionId) {
        setSelectedVersionId(null);
      }
      return;
    }

    if (!selectedVersionId || !versionItems.some((item) => item.version_id === selectedVersionId)) {
      setSelectedVersionId(versionItems[0].version_id);
    }
  }, [selectedVersionId, versionItems]);

  const selectedVersionIdResolved = selectedVersionId ?? versionItems[0]?.version_id ?? null;

  const versionDetailQuery = useQuery({
    queryKey: ['strategy-workspace', 'version-detail', selectedVersionIdResolved],
    queryFn: () => getStrategyVersion(selectedVersionIdResolved ?? ''),
    enabled: Boolean(selectedVersionIdResolved),
    staleTime: 30_000,
  });

  const selectedVersionDetail = versionDetailQuery.data?.item ?? null;

  const artifactsQuery = useQuery({
    queryKey: ['strategy-workspace', 'artifacts'],
    queryFn: () => listArtifacts({ limit: 24 }),
    staleTime: 30_000,
  });

  const recentArtifacts = useMemo(
    () =>
      sortByDateDesc((artifactsQuery.data?.items ?? []) as ArtifactRecord[]).filter((artifact) => {
        const text = `${artifact.name} ${artifact.kind} ${artifact.source}`.toLowerCase();
        return text.includes('strategy') || text.includes('report') || text.includes('evidence') || text.includes('ranking');
      }),
    [artifactsQuery.data?.items],
  );

  const strategyJobCount = strategyJobs.length;
  const versionCount = versionItems.length;
  const artifactCount = recentArtifacts.length;

  const profileError = profilesQuery.error ?? profileDetailQuery.error;

  return (
    <main className="page-stack">
      <div className="flex flex-wrap items-center justify-start gap-3">
        <Link
          className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-sky-700 transition-colors hover:bg-slate-50"
          to="/strategies/regime-selection"
        >
          进入规则选择
        </Link>
      </div>

      <PageHeader
        description="在 Web 中构建策略版本、运行盘前和盘后任务，并通过 Job、Artifact 和 Report 解释结果。"
      />

      {submissionMessage ? (
        <section className="rounded-[28px] border border-sky-200 bg-sky-50 px-6 py-4 text-sky-900 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="font-medium">{submissionMessage}</p>
              <p className="mt-1 text-sm text-sky-700">任务已通过 Job Center 创建，不需要 CLI。</p>
            </div>
            {submissionJobId ? (
              <button
                className="rounded-lg border border-sky-200 bg-white px-4 py-2 text-sm font-medium text-sky-700 hover:bg-sky-50"
                onClick={() => {
                  navigate(`/jobs/${submissionJobId}`);
                }}
                type="button"
              >
                打开 Job 详情
              </button>
            ) : null}
          </div>
        </section>
      ) : null}

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,0.9fr)]">
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <Badge variant="info" className="w-fit">
              运行参数
            </Badge>
            <CardTitle className="mt-2 text-slate-950">trader / date / profile</CardTitle>
            <CardDescription className="text-slate-600">
              只选择正式 Web 参数，不强化任何 CLI 入口。
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {profilesQuery.isLoading ? (
              <Skeleton className="h-44 w-full bg-slate-100" />
            ) : profilesQuery.error ? (
              <ErrorState
                {...buildErrorRecoveryState(profilesQuery.error, 'strategy')}
                onRetry={isWorkspacePermissionDenied(profilesQuery.error) ? undefined : () => void profilesQuery.refetch()}
              />
            ) : profileItems.length ? (
              <>
                <div className="grid gap-3 md:grid-cols-3">
                  <label className="space-y-2">
                    <span className="text-sm font-medium text-slate-700">Trader ID</span>
                    <Input
                      className="border-slate-200 bg-white text-slate-900 placeholder:text-slate-400"
                      onChange={(event) => setTraderId(event.target.value)}
                      placeholder="例如 trader_a"
                      value={traderId}
                    />
                  </label>
                  <label className="space-y-2">
                    <span className="text-sm font-medium text-slate-700">策略日期</span>
                    <Input
                      className="border-slate-200 bg-white text-slate-900 placeholder:text-slate-400"
                      onChange={(event) => setStrategyDate(event.target.value)}
                      type="date"
                      value={strategyDate}
                    />
                  </label>
                  <label className="space-y-2">
                    <span className="text-sm font-medium text-slate-700">Profile</span>
                    <Select
                      className="border-slate-200 bg-white text-slate-900"
                      onChange={(event) => setSelectedProfileId(event.target.value)}
                      value={selectedProfileId}
                    >
                      {profileItems.map((profile) => (
                        <option key={profile.profile_id} value={profile.profile_id}>
                          {profile.name} · {profile.profile_id} · v{profile.version}
                        </option>
                      ))}
                    </Select>
                  </label>
                </div>

                <div className="grid gap-3 md:grid-cols-3">
                  <SummaryTile label="策略任务" value={strategyJobCount} />
                  <SummaryTile label="策略版本" value={versionCount} />
                  <SummaryTile label="相关产物" value={artifactCount} />
                </div>
              </>
            ) : (
              <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                当前没有可用 profile。请先导入或创建 profile，再继续提交策略任务。
              </div>
            )}
          </CardContent>
        </Card>

        <StrategyWorkspaceActions
          configPath={configPath}
          disabled={!configPath || !traderId.trim() || !strategyDate}
          onSubmitted={({ jobType, jobId }) => {
            setSubmissionMessage(`已提交 ${jobType}，可打开 Job 详情查看进度。`);
            setSubmissionJobId(jobId);
            void jobsQuery.refetch();
            void versionsQuery.refetch();
            void artifactsQuery.refetch();
          }}
          profileId={selectedProfileId}
          profileName={selectedProfile?.name ?? ''}
          snapshotId={latestSnapshot?.snapshot_id ?? null}
          snapshotCapturedAt={latestSnapshot?.captured_at ?? null}
          strategyDate={strategyDate}
          traderId={traderId}
        />
      </section>

      <StrategyWorkspaceCandidate
        traderId={traderId}
        selectedVersion={selectedVersionDetail}
        onCandidateCreated={() => {
          void versionsQuery.refetch();
        }}
        onReviewSubmitted={() => {
          void jobsQuery.refetch();
        }}
      />

      <ProfileDetailState
        detail={selectedProfileDetail}
        error={profileError}
        isLoading={profileDetailLoading}
        onRetry={() => {
          void profilesQuery.refetch();
          void profileDetailQuery.refetch();
        }}
        profile={selectedProfile}
      />

      <StrategyWorkspaceHistory
        error={jobsQuery.error}
        isLoading={jobsQuery.isLoading}
        jobs={strategyJobs}
        onRetry={() => {
          void jobsQuery.refetch();
        }}
      />

        <StrategyWorkspaceArtifacts
          artifacts={recentArtifacts}
          isArtifactsLoading={artifactsQuery.isLoading}
          isVersionDetailLoading={versionDetailQuery.isLoading || versionDetailQuery.isFetching}
          isVersionsLoading={versionsQuery.isLoading}
        onRetryArtifacts={() => {
          void artifactsQuery.refetch();
        }}
        onRetryVersionDetail={() => {
          void versionDetailQuery.refetch();
        }}
        onRetryVersions={() => {
          void versionsQuery.refetch();
        }}
        onSelectVersion={(versionId) => {
          setSelectedVersionId(versionId);
        }}
          selectedVersionDetail={selectedVersionDetail}
          selectedVersionId={selectedVersionIdResolved}
          artifactsError={artifactsQuery.error}
          versionDetailError={versionDetailQuery.error}
          versions={versionItems}
        versionsError={versionsQuery.error}
      />
    </main>
  );
}

export function StrategyWorkspacePage() {
  return <StrategyWorkspaceShell />;
}
