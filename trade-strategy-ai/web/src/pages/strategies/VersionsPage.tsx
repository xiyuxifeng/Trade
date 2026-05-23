import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { PageHeader } from '@/components/layout/page-header';
import { EmptyState, LoadingState } from '@/components/kit';
import { ErrorState } from '@/components/state/ErrorState';
import { buildErrorRecoveryState } from '@/lib/error-recovery';
import { formatLocalDateInputOffset } from '@/lib/date';
import { getProfile, listProfiles } from '@/lib/api/profiles';
import { listArtifacts } from '@/lib/api/artifacts';
import { getStrategyVersion, listStrategyVersions } from '@/lib/api/strategyStudio';
import type { ArtifactRecord } from '@/types/artifacts';
import type { StrategyVersionSummaryItem } from '@/types/strategyStudio';
import { StrategyWorkspaceActions } from '@/features/strategy-workspace';
import { StrategyWorkspaceArtifacts } from '@/features/strategy-workspace';
import { isWorkspacePermissionDenied, selectLatestProfileSnapshot } from '@/features/strategy-workspace';
import { TraderIdSelect } from '@/components/inputs/trader-id-select';

function sortByDateDesc<T extends { created_at?: string | null; strategy_date?: string | null; version_id?: string }>(items: T[]) {
  return [...items].sort((left, right) => {
    const leftKey = left.strategy_date ?? left.created_at ?? left.version_id ?? '';
    const rightKey = right.strategy_date ?? right.created_at ?? right.version_id ?? '';
    return String(rightKey).localeCompare(String(leftKey));
  });
}

function sortArtifactsByCreatedAtDesc(items: ArtifactRecord[]) {
  return [...items].sort((left, right) => {
    const leftKey = left.modified_at ?? '';
    const rightKey = right.modified_at ?? '';
    return rightKey.localeCompare(leftKey);
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

export function StrategyVersionsPage() {
  const navigate = useNavigate();
  const today = useMemo(() => formatLocalDateInputOffset(0), []);
  const [draftTraderId, setDraftTraderId] = useState('trader_a');
  const [draftStrategyDate, setDraftStrategyDate] = useState(today);
  const [draftSelectedProfileId, setDraftSelectedProfileId] = useState('');
  const [traderId, setTraderId] = useState('trader_a');
  const [strategyDate, setStrategyDate] = useState(today);
  const [selectedProfileId, setSelectedProfileId] = useState('');
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);
  const [submissionMessage, setSubmissionMessage] = useState<string | null>(null);
  const [submissionJobId, setSubmissionJobId] = useState<string | null>(null);

  const profilesQuery = useQuery({
    queryKey: ['strategy-versions-page', 'profiles'],
    queryFn: () => listProfiles({ skip: 0, limit: 50 }),
    staleTime: 30_000,
  });

  const profileItems = profilesQuery.data?.items ?? [];

  useEffect(() => {
    if (!draftSelectedProfileId && profileItems.length > 0) {
      const firstProfileId = profileItems[0].profile_id;
      setDraftSelectedProfileId(firstProfileId);
      setSelectedProfileId(firstProfileId);
    }
  }, [draftSelectedProfileId, profileItems]);

  useEffect(() => {
    if (draftSelectedProfileId && !profileItems.some((item) => item.profile_id === draftSelectedProfileId)) {
      const firstProfileId = profileItems[0]?.profile_id ?? '';
      setDraftSelectedProfileId(firstProfileId);
      setSelectedProfileId(firstProfileId);
    }
  }, [draftSelectedProfileId, profileItems]);

  const handleSearch = () => {
    setTraderId(draftTraderId);
    setStrategyDate(draftStrategyDate);
    setSelectedProfileId(draftSelectedProfileId);
  };

  const handleReset = () => {
    const firstProfileId = profileItems[0]?.profile_id ?? '';
    setDraftTraderId('trader_a');
    setDraftStrategyDate(today);
    setDraftSelectedProfileId(firstProfileId);
    setTraderId('trader_a');
    setStrategyDate(today);
    setSelectedProfileId(firstProfileId);
  };

  const profileDetailQuery = useQuery({
    queryKey: ['strategy-versions-page', 'profile-detail', selectedProfileId],
    queryFn: () => getProfile(selectedProfileId),
    enabled: Boolean(selectedProfileId),
    staleTime: 30_000,
  });

  const selectedProfileDetailRaw = profileDetailQuery.data ?? null;
  const selectedProfileDetail =
    selectedProfileDetailRaw?.profile.profile_id === selectedProfileId ? selectedProfileDetailRaw : null;
  const latestSnapshot = selectLatestProfileSnapshot(selectedProfileDetail);

  const versionsQuery = useQuery({
    queryKey: ['strategy-versions-page', 'versions', traderId, strategyDate],
    queryFn: () =>
      listStrategyVersions({
        trader_id: traderId.trim() || undefined,
        date_from: strategyDate || undefined,
        date_to: strategyDate || undefined,
        limit: 12,
      }),
    staleTime: 30_000,
  });

  const versionItems = useMemo(
    () => sortByDateDesc((versionsQuery.data?.items ?? []) as StrategyVersionSummaryItem[]),
    [versionsQuery.data?.items],
  );

  useEffect(() => {
    if (!versionItems.length) {
      setSelectedVersionId(null);
      return;
    }
    if (!selectedVersionId || !versionItems.some((item) => item.version_id === selectedVersionId)) {
      setSelectedVersionId(versionItems[0].version_id);
    }
  }, [selectedVersionId, versionItems]);

  const selectedVersionIdResolved = selectedVersionId ?? versionItems[0]?.version_id ?? null;

  const versionDetailQuery = useQuery({
    queryKey: ['strategy-versions-page', 'version-detail', selectedVersionIdResolved],
    queryFn: () => getStrategyVersion(selectedVersionIdResolved ?? ''),
    enabled: Boolean(selectedVersionIdResolved),
    staleTime: 30_000,
  });

  const selectedVersionDetail = versionDetailQuery.data?.item ?? null;

  const artifactsQuery = useQuery({
    queryKey: ['strategy-versions-page', 'artifacts'],
    queryFn: () => listArtifacts({ limit: 24 }),
    staleTime: 30_000,
  });

  const strategyArtifacts = useMemo(
    () =>
      sortArtifactsByCreatedAtDesc((artifactsQuery.data?.items ?? []) as ArtifactRecord[]).filter((artifact) => {
        const text = `${artifact.name} ${artifact.kind} ${artifact.source}`.toLowerCase();
        return text.includes('strategy') || text.includes('report') || text.includes('evidence') || text.includes('ranking');
      }),
    [artifactsQuery.data?.items],
  );

  const profileError = profilesQuery.error ?? profileDetailQuery.error;
  const pageError = profileError ?? versionsQuery.error ?? versionDetailQuery.error ?? artifactsQuery.error;
  const permissionDenied = isWorkspacePermissionDenied(pageError);

  if (profilesQuery.isLoading) {
    return (
      <main className="page-stack">
        <PageHeader
          kicker="策略"
          title="策略版本"
          description="构建策略版本：把 Profile、交易员和策略日期固化成正式版本。"
          actionLabel="返回策略首页"
          onAction={() => navigate('/strategies')}
        />
        <LoadingState label="正在加载策略版本页" description="正在读取 Profile、策略版本与产物。" />
      </main>
    );
  }

  if (pageError) {
    return (
      <main className="page-stack">
        <PageHeader
          kicker="策略"
          title="策略版本"
          description="构建策略版本：把 Profile、交易员和策略日期固化成正式版本。"
          actionLabel="返回策略首页"
          onAction={() => navigate('/strategies')}
        />
        <ErrorState
          {...buildErrorRecoveryState(pageError, 'strategy')}
          onRetry={
            permissionDenied
              ? undefined
              : () => {
                  void profilesQuery.refetch();
                  void profileDetailQuery.refetch();
                  void versionsQuery.refetch();
                  void versionDetailQuery.refetch();
                  void artifactsQuery.refetch();
                }
          }
        />
      </main>
    );
  }

  if (profileItems.length === 0) {
    return (
      <main className="page-stack">
        <PageHeader
          kicker="策略"
          title="策略版本"
          description="构建策略版本：把 Profile、交易员和策略日期固化成正式版本。"
          actionLabel="返回策略首页"
          onAction={() => navigate('/strategies')}
        />
        <EmptyState
          title="暂无可用 Profile。"
          description="先到配置管理创建或导入 Profile，再回到这里构建策略版本。"
          actionLabel="前往配置管理"
          onAction={() => navigate('/profiles')}
        />
      </main>
    );
  }

  return (
    <main className="page-stack">
      <PageHeader
        kicker="策略"
        title="策略版本"
        description="构建策略版本：把 Profile、交易员和策略日期固化成正式版本。"
        actionLabel="返回策略首页"
        onAction={() => navigate('/strategies')}
      />

      {submissionMessage ? (
        <section className="rounded-[28px] border border-sky-200 bg-sky-50 px-6 py-4 text-sky-900 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="font-medium">{submissionMessage}</p>
              <p className="mt-1 text-sm text-sky-700">任务已提交，可直接打开任务详情查看进度。</p>
            </div>
            {submissionJobId ? (
              <button
                className="rounded-lg border border-sky-200 bg-white px-4 py-2 text-sm font-medium text-sky-700 hover:bg-sky-50"
                onClick={() => navigate(`/jobs/${submissionJobId}`)}
                type="button"
              >
                打开任务详情
              </button>
            ) : null}
          </div>
        </section>
      ) : null}

      <section className="grid gap-4">
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <Badge variant="info" className="w-fit">
              运行参数
            </Badge>
            <CardTitle className="mt-2 text-slate-950">trader / date / profile</CardTitle>
            <CardDescription className="text-slate-600">构建入口只使用 Profile、交易员和策略日期。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-3">
              <label className="space-y-2">
                <span className="text-sm font-medium text-slate-700">Trader ID</span>
                <TraderIdSelect
                  ariaLabel="Trader ID"
                  className="border-slate-200 bg-white text-slate-900"
                  onChange={setDraftTraderId}
                  source="strategy"
                  value={draftTraderId}
                />
              </label>
              <label className="space-y-2">
                <span className="text-sm font-medium text-slate-700">策略日期</span>
                <Input
                  className="border-slate-200 bg-white text-slate-900 placeholder:text-slate-400"
                  onChange={(event) => setDraftStrategyDate(event.target.value)}
                  type="date"
                  value={draftStrategyDate}
                />
              </label>
              <label className="space-y-2">
                <span className="text-sm font-medium text-slate-700">Profile</span>
                <Select
                  className="border-slate-200 bg-white text-slate-900"
                  onChange={(event) => setDraftSelectedProfileId(event.target.value)}
                  value={draftSelectedProfileId}
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
              <SummaryTile label="策略版本" value={versionItems.length} />
              <SummaryTile label="最新版本" value={versionItems[0]?.version_id ?? '暂无'} />
              <SummaryTile label="最新快照" value={latestSnapshot?.snapshot_id ?? '暂无'} />
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <Button onClick={handleSearch} type="button">
                搜索
              </Button>
              <Button className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50" onClick={handleReset} type="button" variant="outline">
                重置
              </Button>
            </div>
          </CardContent>
        </Card>
      </section>

      <StrategyWorkspaceActions
        disabled={!selectedProfileId || !traderId.trim() || !strategyDate}
        onSubmitted={({ jobType, jobId }) => {
          setSubmissionMessage(`已提交 ${jobType}，可打开任务详情查看进度。`);
          setSubmissionJobId(jobId);
          void versionsQuery.refetch();
          void versionDetailQuery.refetch();
          void artifactsQuery.refetch();
        }}
        profileId={selectedProfileId}
        snapshotId={latestSnapshot?.snapshot_id ?? null}
        strategyDate={strategyDate}
        traderId={traderId}
      />

      <section>
        <StrategyWorkspaceArtifacts
          artifacts={strategyArtifacts}
          artifactsError={artifactsQuery.error}
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
          versionDetailError={versionDetailQuery.error}
          versions={versionItems}
          versionsError={versionsQuery.error}
        />
      </section>
    </main>
  );
}
