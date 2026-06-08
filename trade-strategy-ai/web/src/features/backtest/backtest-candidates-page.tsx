import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select } from '@/components/ui/select';
import { PageHeader } from '@/components/layout/page-header';
import { EmptyState, ErrorState, LoadingState, SectionCard } from '@/components/kit';
import { TraderIdSelect } from '@/components/inputs/trader-id-select';
import { useAuth } from '@/features/auth/auth-context';
import { ApiError } from '@/lib/api/http';
import { buildErrorRecoveryState } from '@/lib/error-recovery';
import { getStrategyVersion, listStrategyVersions } from '@/lib/api/strategyStudio';
import { StrategyWorkspaceCandidate } from '@/features/strategy-workspace';
import type { StrategyVersionSummaryItem } from '@/types/strategyStudio';

export function BacktestCandidatesPage() {
  const navigate = useNavigate();
  const { canAccess, principal } = useAuth();
  const [traderId, setTraderId] = useState('');
  const [strategyVersionId, setStrategyVersionId] = useState('');
  const canViewBacktest = canAccess('viewer');

  const strategyVersionsQuery = useQuery({
    queryKey: ['backtest-candidates', 'strategy-versions'],
    queryFn: () => listStrategyVersions({ skip: 0, limit: 100 }),
    enabled: canViewBacktest,
    staleTime: 60_000,
  });

  const strategyVersionItems = strategyVersionsQuery.data?.items ?? [];
  const filteredVersionItems = useMemo(
    () => strategyVersionItems.filter((item) => !traderId || item.trader_id === traderId),
    [strategyVersionItems, traderId],
  );

  useEffect(() => {
    if (!strategyVersionItems.length) {
      return;
    }
    if (!traderId) {
      setTraderId(strategyVersionItems[0].trader_id);
    }
  }, [strategyVersionItems, traderId]);

  useEffect(() => {
    if (!filteredVersionItems.length) {
      setStrategyVersionId('');
      return;
    }
    if (!strategyVersionId || !filteredVersionItems.some((item) => item.version_id === strategyVersionId)) {
      setStrategyVersionId(filteredVersionItems[0].version_id);
    }
  }, [filteredVersionItems, strategyVersionId]);

  const selectedVersionDetailQuery = useQuery({
    queryKey: ['backtest-candidates', 'version-detail', strategyVersionId],
    queryFn: () => getStrategyVersion(strategyVersionId),
    enabled: Boolean(strategyVersionId) && canViewBacktest,
    staleTime: 30_000,
  });

  const selectedVersion = selectedVersionDetailQuery.data?.item ?? null;
  const selectedVersionLoading = selectedVersionDetailQuery.isLoading && Boolean(strategyVersionId);
  const queryError = strategyVersionsQuery.error ?? selectedVersionDetailQuery.error;
  const permissionDenied = queryError instanceof ApiError && (queryError.status === 401 || queryError.status === 403);

  if (!canViewBacktest) {
    return (
      <main className="page-stack">
        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-lg font-semibold text-slate-900">没有权限访问候选版本</p>
          <p className="mt-2 text-sm text-slate-600">当前身份为 {principal.role}，查看候选版本至少需要 viewer 权限。</p>
        </section>
      </main>
    );
  }

  if (queryError) {
    return (
      <main className="page-stack">
        <PageHeader
          kicker="回测与画像"
          title="候选版本"
          description="在独立页面里生成候选规则版本、查看候选列表并提交审核。"
          actionLabel="返回回测与画像"
          onAction={() => navigate('/backtest')}
        />
        <ErrorState
          {...buildErrorRecoveryState(queryError, 'backtest')}
          onRetry={
            permissionDenied
              ? undefined
              : () => {
                  void strategyVersionsQuery.refetch();
                  void selectedVersionDetailQuery.refetch();
                }
          }
        />
      </main>
    );
  }

  return (
    <main className="page-stack">
      <div className="flex flex-wrap items-center justify-start gap-3">
        <Link
          className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-sky-700 transition-colors hover:bg-slate-50"
          to="/backtest"
        >
          返回回测与画像
        </Link>
        <Badge variant="info">{strategyVersionItems.length} 个规则版本可选</Badge>
      </div>

      <PageHeader
        kicker="回测与画像"
        title="候选版本"
        description="候选版本生成与审核放在独立页面中，回测页只保留轻入口。"
      />

      <section className="grid gap-6 xl:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <CardTitle className="text-slate-950">选择候选来源</CardTitle>
            <CardDescription className="text-slate-600">先选交易员，再选要生成候选的规则版本。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <label className="space-y-2">
              <span className="text-xs uppercase tracking-[0.16em] text-slate-500">交易员 ID</span>
              <TraderIdSelect
                ariaLabel="交易员 ID"
                className="border-slate-200 bg-white text-slate-900"
                onChange={(value) => setTraderId(value)}
                source="strategy"
                value={traderId}
              />
            </label>

            <label className="space-y-2">
              <span className="text-xs uppercase tracking-[0.16em] text-slate-500">规则版本 ID</span>
              <Select
                aria-label="规则版本 ID"
                className="border-slate-200 bg-white text-slate-900"
                value={strategyVersionId}
                onChange={(event) => setStrategyVersionId(event.target.value)}
                disabled={filteredVersionItems.length === 0}
              >
                {filteredVersionItems.length === 0 ? <option value="">暂无可用规则版本</option> : null}
                {filteredVersionItems.map((item: StrategyVersionSummaryItem) => (
                  <option key={item.version_id} value={item.version_id}>
                    {item.version_id}
                  </option>
                ))}
              </Select>
            </label>

            {selectedVersion ? (
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">当前候选来源</p>
                <p className="mt-2 text-sm font-medium text-slate-950">{selectedVersion.version_id}</p>
                <p className="mt-1 text-xs text-slate-500">
                  交易员 {selectedVersion.trader_id} · 分析日期 {selectedVersion.strategy_date} · 状态 {selectedVersion.status}
                </p>
                <p className="mt-2 text-xs text-slate-500">选中后，下方会展示候选生成、列表和审核动作。</p>
              </div>
            ) : (
              <EmptyState
                title="请选择规则版本"
                description="选定交易员后，选择一个规则版本即可继续生成候选。"
              />
            )}

            {strategyVersionsQuery.isLoading ? (
              <LoadingState label="正在加载规则版本" description="会读取当前交易员下可用的规则版本。" />
            ) : null}
          </CardContent>
        </Card>

        <SectionCard
          title="候选工作区"
          description="生成候选规则版本、对比父版本并提交审核任务。"
          action={<Badge variant="info">{selectedVersion ? selectedVersion.version_id : '未选择版本'}</Badge>}
        >
          {selectedVersionLoading ? (
            <LoadingState label="正在加载候选工作区" description="会读取当前规则版本的候选生成与审核信息。" />
          ) : selectedVersion ? (
            <StrategyWorkspaceCandidate traderId={traderId} selectedVersion={selectedVersion} />
          ) : (
            <EmptyState title="选择一个规则版本" description="在左侧选择交易员和规则版本后，这里会显示候选生成与审核工作区。" />
          )}
        </SectionCard>
      </section>
    </main>
  );
}
