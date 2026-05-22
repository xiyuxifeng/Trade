import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { PageHeader } from '@/components/layout/page-header';
import { EmptyState, LoadingState } from '@/components/kit';
import { ErrorState } from '@/components/state/ErrorState';
import { buildErrorRecoveryState } from '@/lib/error-recovery';
import { formatLocalDateInputOffset } from '@/lib/date';
import { getProfile, listProfiles } from '@/lib/api/profiles';
import { getStrategyVersion, listStrategyVersions } from '@/lib/api/strategyStudio';
import type { StrategyVersionSummaryItem } from '@/types/strategyStudio';
import { StrategyWorkspaceCandidate } from '@/features/strategy-workspace';
import { isWorkspacePermissionDenied, selectLatestProfileSnapshot } from '@/features/strategy-workspace';

function sortByDateDesc<T extends { created_at?: string | null; strategy_date?: string | null; version_id?: string }>(items: T[]) {
  return [...items].sort((left, right) => {
    const leftKey = left.strategy_date ?? left.created_at ?? left.version_id ?? '';
    const rightKey = right.strategy_date ?? right.created_at ?? right.version_id ?? '';
    return String(rightKey).localeCompare(String(leftKey));
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

export function StrategyCandidatesPage() {
  const navigate = useNavigate();
  const today = useMemo(() => formatLocalDateInputOffset(0), []);
  const [traderId, setTraderId] = useState('trader_a');
  const [strategyDate, setStrategyDate] = useState(today);
  const [selectedProfileId, setSelectedProfileId] = useState('');
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);

  const profilesQuery = useQuery({
    queryKey: ['strategy-candidates-page', 'profiles'],
    queryFn: () => listProfiles({ skip: 0, limit: 50 }),
    staleTime: 30_000,
  });

  const profileItems = profilesQuery.data?.items ?? [];

  useEffect(() => {
    if (!selectedProfileId && profileItems.length > 0) {
      setSelectedProfileId(profileItems[0].profile_id);
    }
  }, [profileItems, selectedProfileId]);

  useEffect(() => {
    if (selectedProfileId && !profileItems.some((item) => item.profile_id === selectedProfileId)) {
      setSelectedProfileId(profileItems[0]?.profile_id ?? '');
    }
  }, [profileItems, selectedProfileId]);

  const profileDetailQuery = useQuery({
    queryKey: ['strategy-candidates-page', 'profile-detail', selectedProfileId],
    queryFn: () => getProfile(selectedProfileId),
    enabled: Boolean(selectedProfileId),
    staleTime: 30_000,
  });

  const selectedProfileDetailRaw = profileDetailQuery.data ?? null;
  const selectedProfileDetail =
    selectedProfileDetailRaw?.profile.profile_id === selectedProfileId ? selectedProfileDetailRaw : null;
  const latestSnapshot = selectLatestProfileSnapshot(selectedProfileDetail);

  const versionsQuery = useQuery({
    queryKey: ['strategy-candidates-page', 'versions', traderId, strategyDate],
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
    queryKey: ['strategy-candidates-page', 'version-detail', selectedVersionIdResolved],
    queryFn: () => getStrategyVersion(selectedVersionIdResolved ?? ''),
    enabled: Boolean(selectedVersionIdResolved),
    staleTime: 30_000,
  });

  const selectedVersionDetail = versionDetailQuery.data?.item ?? null;
  const pageError = profilesQuery.error ?? profileDetailQuery.error ?? versionsQuery.error ?? versionDetailQuery.error;
  const permissionDenied = isWorkspacePermissionDenied(pageError);

  if (profilesQuery.isLoading) {
    return (
      <main className="page-stack">
        <PageHeader
          kicker="策略"
          title="候选版本"
          description="生成、审核和追踪候选版本，只保留 Profile 入口。"
          actionLabel="返回策略首页"
          onAction={() => navigate('/strategies')}
        />
        <LoadingState label="正在加载候选版本页" description="正在读取 Profile 与策略版本。" />
      </main>
    );
  }

  if (pageError) {
    return (
      <main className="page-stack">
        <PageHeader
          kicker="策略"
          title="候选版本"
          description="生成、审核和追踪候选版本，只保留 Profile 入口。"
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
          title="候选版本"
          description="生成、审核和追踪候选版本，只保留 Profile 入口。"
          actionLabel="返回策略首页"
          onAction={() => navigate('/strategies')}
        />
        <EmptyState
          title="暂无可用 Profile。"
          description="先到配置管理创建或导入 Profile，再回到这里生成候选版本。"
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
        title="候选版本"
        description="生成、审核和追踪候选版本，只保留 Profile 入口。"
        actionLabel="返回策略首页"
        onAction={() => navigate('/strategies')}
      />

      <section className="grid gap-4 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
        <Card className="border-slate-200 bg-white shadow-sm xl:col-span-2">
          <CardHeader>
            <Badge variant="info" className="w-fit">
              运行参数
            </Badge>
            <CardTitle className="mt-2 text-slate-950">trader / date / profile</CardTitle>
            <CardDescription className="text-slate-600">候选版本页面只使用 Profile、交易员和策略日期。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
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
              <SummaryTile label="版本数" value={versionItems.length} />
              <SummaryTile label="最新版本" value={versionItems[0]?.version_id ?? '暂无'} />
              <SummaryTile label="最新快照" value={latestSnapshot?.snapshot_id ?? '暂无'} />
            </div>
          </CardContent>
        </Card>
      </section>

      <StrategyWorkspaceCandidate
        traderId={traderId}
        selectedVersion={selectedVersionDetail}
        onCandidateCreated={() => {
          void versionsQuery.refetch();
        }}
        onReviewSubmitted={() => {
          void versionsQuery.refetch();
        }}
      />
    </main>
  );
}
