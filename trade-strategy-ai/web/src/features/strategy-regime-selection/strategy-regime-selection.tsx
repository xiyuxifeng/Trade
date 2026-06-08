import { useEffect, useMemo, useState } from 'react';
import dayjs from 'dayjs';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { PageHeader } from '@/components/layout/page-header';
import { TraderIdSelect } from '@/components/inputs/trader-id-select';
import { EmptyState, LoadingState, SectionCard, StatusBadge } from '@/components/kit';
import { ErrorState } from '@/components/state/ErrorState';
import { buildErrorRecoveryState } from '@/lib/error-recovery';
import { getStrategyVersion, listStrategyVersions } from '@/lib/api/strategyStudio';
import type { StrategyVersionDetailItem, StrategyVersionSummaryItem } from '@/types/strategyStudio';

type RegimeSelectionRecord = {
  rule_id?: string;
  decision?: string;
  score?: number;
  reason?: string;
  evidence?: string[];
  regime_version?: string;
  applicability_profile_version?: string | null;
  rule_applicability_profile_id?: string | null;
  sample_count?: number;
  profile_confidence?: number;
  override_applied?: boolean;
};

type RegimeSelectionPayload = {
  selection_id?: string;
  strategy_version_id?: string;
  snapshot_id?: string;
  market_regime_version?: string;
  source_feature_version?: string;
  applicability_profile_version?: string | null;
  selected_rules?: RegimeSelectionRecord[];
  skipped_rules?: RegimeSelectionRecord[];
  blocked_rules?: RegimeSelectionRecord[];
  selection_reason?: string;
  evidence?: string[];
  override?: {
    operator?: string;
    reason?: string;
    timestamp?: string;
    risk_level?: string;
  } | null;
  confidence?: number;
  quality_status?: string;
  warnings?: string[];
  created_at?: string;
  selected_by?: string;
};

const decisionLabelMap: Record<string, { label: string; variant: 'default' | 'success' | 'warning' | 'destructive' | 'info' }> = {
  selected: { label: '已选中', variant: 'success' },
  skipped: { label: '已跳过', variant: 'warning' },
  blocked: { label: '已阻断', variant: 'destructive' },
  applicable: { label: '适用', variant: 'success' },
  neutral: { label: '中性', variant: 'info' },
  partial: { label: '部分可用', variant: 'warning' },
  ok: { label: '正常', variant: 'success' },
  low_confidence: { label: '低置信度', variant: 'warning' },
};

function formatDate(value: string | null | undefined) {
  if (!value) return '暂无';
  return dayjs(value).format('YYYY-MM-DD HH:mm');
}

function formatNumber(value: number | null | undefined, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '暂无';
  }
  return value.toFixed(digits);
}

function formatRegimeText(value: string | null | undefined, fallback = '无说明') {
  if (!value) return fallback;
  return value.replaceAll('Market Regime', '市场状态').replaceAll('market regime', '市场状态');
}

function toSelectionPayload(value: StrategyVersionDetailItem['regime_selection']): RegimeSelectionPayload | null {
  if (!value || typeof value !== 'object') return null;
  return value as RegimeSelectionPayload;
}

function SelectionRecordCard({
  record,
  tone = 'default',
}: {
  record: RegimeSelectionRecord;
  tone?: 'default' | 'selected' | 'skipped' | 'blocked';
}) {
  const toneClass =
    tone === 'selected'
      ? 'border-emerald-200 bg-emerald-50'
      : tone === 'skipped'
        ? 'border-amber-200 bg-amber-50'
        : tone === 'blocked'
          ? 'border-rose-200 bg-rose-50'
          : 'border-slate-200 bg-white';

  return (
    <div className={`rounded-2xl border p-4 ${toneClass}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-base font-medium text-slate-950">{record.rule_id ?? '未命名规则'}</p>
          <p className="mt-1 text-sm text-slate-600">
            适用画像版本 {record.applicability_profile_version ?? '未记录'}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={decisionLabelMap[record.decision ?? '']?.variant ?? 'default'}>
            {decisionLabelMap[record.decision ?? '']?.label ?? record.decision ?? '未知'}
          </Badge>
          {record.override_applied ? <Badge variant="info">人工覆盖</Badge> : null}
        </div>
      </div>
      <div className="mt-3 grid gap-2 text-sm text-slate-700 md:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white px-3 py-2">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">评分</p>
          <p className="mt-1 font-medium text-slate-950">{formatNumber(record.score, 3)}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white px-3 py-2">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">样本数</p>
          <p className="mt-1 font-medium text-slate-950">{record.sample_count ?? '暂无'}</p>
        </div>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-700">{formatRegimeText(record.reason)}</p>
      {record.evidence?.length ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {record.evidence.slice(0, 6).map((item) => (
            <span key={item} className="rounded-full border border-slate-200 bg-white px-2 py-1 text-xs text-slate-600">
              {item}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function StrategyRegimeSelectionWorkspace() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const today = useMemo(() => dayjs().format('YYYY-MM-DD'), []);
  const [traderId, setTraderId] = useState('trader_a');
  const [strategyDate, setStrategyDate] = useState(today);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(searchParams.get('version_id'));
  const [versionStatus, setVersionStatus] = useState('');
  const [versionType, setVersionType] = useState('');

  const versionsQuery = useQuery({
    queryKey: ['strategy-regime-selection', 'versions', traderId, strategyDate, versionStatus, versionType],
    queryFn: () =>
      listStrategyVersions({
        trader_id: traderId || undefined,
        status: versionStatus || undefined,
        version_type: versionType || undefined,
        date_from: strategyDate || undefined,
        date_to: strategyDate || undefined,
        skip: 0,
        limit: 20,
      }),
    staleTime: 10_000,
  });

  const versionItems = versionsQuery.data?.items ?? [];

  useEffect(() => {
    if (!versionItems.length) {
      setSelectedVersionId(null);
      return;
    }
    if (!selectedVersionId || !versionItems.some((item) => item.version_id === selectedVersionId)) {
      setSelectedVersionId(versionItems[0].version_id);
    }
  }, [selectedVersionId, versionItems]);

  const versionDetailQuery = useQuery({
    queryKey: ['strategy-regime-selection', 'version-detail', selectedVersionId],
    queryFn: () => getStrategyVersion(selectedVersionId as string),
    enabled: Boolean(selectedVersionId),
    staleTime: 10_000,
  });

  const selectedVersion = versionDetailQuery.data?.item ?? null;
  const regimeSelection = toSelectionPayload(selectedVersion?.regime_selection);
  const selectedRules = regimeSelection?.selected_rules ?? [];
  const skippedRules = regimeSelection?.skipped_rules ?? [];
  const blockedRules = regimeSelection?.blocked_rules ?? [];
  const qualityMeta = decisionLabelMap[regimeSelection?.quality_status ?? ''] ?? {
    label: regimeSelection?.quality_status ?? '未记录',
    variant: 'default' as const,
  };
  const traceItems = [
    { label: '选择 ID', value: regimeSelection?.selection_id ?? '未记录' },
    { label: '快照 ID', value: regimeSelection?.snapshot_id ?? '未记录' },
    { label: '市场状态版本', value: regimeSelection?.market_regime_version ?? '未记录' },
    { label: '特征版本', value: regimeSelection?.source_feature_version ?? '未记录' },
    { label: '适用画像版本', value: regimeSelection?.applicability_profile_version ?? '未记录' },
    { label: '选择来源', value: regimeSelection?.selected_by ?? '未记录' },
    { label: '置信度', value: formatNumber(regimeSelection?.confidence, 3) },
    { label: '质量状态', value: regimeSelection?.quality_status ?? '未记录' },
  ];

  return (
    <main className="page-stack">
      <PageHeader
        title="规则选择"
        description="用于在规则构建前查看规则为什么被选中、跳过或阻断，并回溯到市场状态与适用性画像版本。"
        actionLabel="返回回测与画像"
        onAction={() => navigate('/backtest')}
      />

      <section className="grid gap-4 xl:grid-cols-4">
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <CardTitle className="text-slate-950">规则版本</CardTitle>
            <CardDescription className="text-slate-600">选择需要查看的规则版本。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <label className="space-y-2 text-sm text-slate-700">
              <span>交易员</span>
              <TraderIdSelect
                ariaLabel="交易员"
                className="border-slate-200 bg-white text-slate-900"
                onChange={setTraderId}
                source="strategy"
                value={traderId}
              />
            </label>
            <label className="space-y-2 text-sm text-slate-700">
                <span>规则日期</span>
              <Input aria-label="规则日期" type="date" value={strategyDate} onChange={(event) => setStrategyDate(event.target.value)} />
            </label>
            <label className="space-y-2 text-sm text-slate-700">
              <span>状态</span>
              <Select aria-label="版本状态" value={versionStatus} onChange={(event) => setVersionStatus(event.target.value)}>
                <option value="">全部</option>
                <option value="draft">草稿</option>
                <option value="released">已发布</option>
                <option value="archived">已存档</option>
              </Select>
            </label>
            <label className="space-y-2 text-sm text-slate-700">
              <span>版本类型</span>
              <Select aria-label="版本类型" value={versionType} onChange={(event) => setVersionType(event.target.value)}>
                <option value="">全部</option>
                <option value="manual">手动</option>
                <option value="candidate">候选</option>
              </Select>
            </label>
            <div className="space-y-3">
              {versionsQuery.isLoading ? (
                <Skeleton className="h-24 w-full" />
              ) : versionItems.length ? (
                <div className="space-y-3">
                  {versionItems.map((item: StrategyVersionSummaryItem) => (
                    <button
                      key={item.version_id}
                      type="button"
                      onClick={() => setSelectedVersionId(item.version_id)}
                      className={`w-full rounded-2xl border p-4 text-left transition-colors ${
                        item.version_id === selectedVersionId
                          ? 'border-sky-300 bg-sky-50'
                          : 'border-slate-200 bg-slate-50 hover:border-sky-200 hover:bg-sky-50/60'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="font-medium text-slate-950">{item.version_id}</p>
                          <p className="mt-1 text-sm text-slate-600">
                            {item.trader_id} · {item.strategy_date}
                          </p>
                        </div>
                        <StatusBadge value={item.status} />
                      </div>
                      <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
                        <span className="rounded-full border border-slate-200 bg-white px-2 py-1">{item.recommendations_count} 条推荐</span>
                        <span className="rounded-full border border-slate-200 bg-white px-2 py-1">{item.has_rules_snapshot ? '含规则快照' : '无规则快照'}</span>
                      </div>
                    </button>
                  ))}
                </div>
              ) : (
                <EmptyState title="暂无规则版本。" description="调整交易员、日期或版本类型后重试。" />
              )}
            </div>
          </CardContent>
        </Card>

        <div className="space-y-4 xl:col-span-3">
          <SectionCard
            title="选择摘要"
            description="当前版本的规则选择结果与回溯字段。"
            action={
              <div className="flex gap-2">
                {/* <Button variant="outline" className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50" onClick={() => navigate('/backtest')}>
                  回测与画像
                </Button> */}
                <Button variant="outline" className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50" onClick={() => navigate('/rule-pool')}>
                  规则池
                </Button>
              </div>
            }
          >
            {versionDetailQuery.isLoading ? (
              <LoadingState label="正在加载选择结果" description="稍后会显示已选中、已跳过和已阻断的规则以及审计信息。" />
            ) : versionDetailQuery.error ? (
              <ErrorState {...buildErrorRecoveryState(versionDetailQuery.error, 'strategy')} onRetry={() => void versionDetailQuery.refetch()} />
            ) : selectedVersion ? (
              <div className="space-y-4">
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                  <Card className="border-slate-200 bg-slate-50 shadow-none">
                    <CardContent className="p-4">
                      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">选择 ID</p>
                      <p className="mt-2 break-all text-sm font-medium text-slate-950">{regimeSelection?.selection_id ?? '未生成'}</p>
                    </CardContent>
                  </Card>
                  <Card className="border-slate-200 bg-slate-50 shadow-none">
                    <CardContent className="p-4">
                      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">质量状态</p>
                      <div className="mt-2">
                        <Badge variant={qualityMeta.variant}>{qualityMeta.label}</Badge>
                      </div>
                    </CardContent>
                  </Card>
                  <Card className="border-slate-200 bg-slate-50 shadow-none">
                    <CardContent className="p-4">
                      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">置信度</p>
                      <p className="mt-2 text-sm font-medium text-slate-950">{formatNumber(regimeSelection?.confidence, 3)}</p>
                    </CardContent>
                  </Card>
                  <Card className="border-slate-200 bg-slate-50 shadow-none">
                    <CardContent className="p-4">
                      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">规则结果</p>
                      <p className="mt-2 text-sm font-medium text-slate-950">
                        {selectedRules.length} / {skippedRules.length} / {blockedRules.length}
                      </p>
                    </CardContent>
                  </Card>
                </div>

                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                  {traceItems.map((item) => (
                    <Card key={item.label} className="border-slate-200 bg-white shadow-sm">
                      <CardContent className="p-4">
                        <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{item.label}</p>
                        <p className="mt-2 break-all text-sm font-medium text-slate-950">{item.value}</p>
                      </CardContent>
                    </Card>
                  ))}
                </div>

                <div className="grid gap-4 xl:grid-cols-3">
                  <SectionCard title={`已选中规则 (${selectedRules.length})`} description="默认可用的候选规则。">
                    <div className="space-y-3">
                      {selectedRules.length ? (
                        selectedRules.map((record, index) => (
                          <SelectionRecordCard key={`${record.rule_id ?? 'selected'}-${index}`} record={record} tone="selected" />
                        ))
                      ) : (
                        <EmptyState title="暂无已选中规则。" description="当前版本没有进入已选中规则列表的规则。" />
                      )}
                    </div>
                  </SectionCard>
                  <SectionCard title={`已跳过规则 (${skippedRules.length})`} description="当前市场状态下没有匹配到有效画像。">
                    <div className="space-y-3">
                      {skippedRules.length ? (
                        skippedRules.map((record, index) => (
                          <SelectionRecordCard key={`${record.rule_id ?? 'skipped'}-${index}`} record={record} tone="skipped" />
                        ))
                      ) : (
                        <EmptyState title="暂无已跳过规则。" description="当前版本没有被跳过的规则。" />
                      )}
                    </div>
                  </SectionCard>
                  <SectionCard title={`已阻断规则 (${blockedRules.length})`} description="默认排除，除非显式人工覆盖。">
                    <div className="space-y-3">
                      {blockedRules.length ? (
                        blockedRules.map((record, index) => (
                          <SelectionRecordCard key={`${record.rule_id ?? 'blocked'}-${index}`} record={record} tone="blocked" />
                        ))
                      ) : (
                        <EmptyState title="暂无已阻断规则。" description="当前版本没有被阻断的规则。" />
                      )}
                    </div>
                  </SectionCard>
                </div>

                <div className="grid gap-4 xl:grid-cols-2">
                  <Card className="border-slate-200 bg-white shadow-sm">
                    <CardHeader>
                      <CardTitle className="text-slate-950">选择原因</CardTitle>
                      <CardDescription className="text-slate-600">说明本次选择的默认规则逻辑。</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm leading-6 text-slate-700">{formatRegimeText(regimeSelection?.selection_reason, '未记录')}</p>
                      {regimeSelection?.evidence?.length ? (
                        <div className="mt-4 flex flex-wrap gap-2">
                          {regimeSelection.evidence.map((item) => (
                            <span key={item} className="rounded-full border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-600">
                              {item}
                            </span>
                          ))}
                        </div>
                      ) : null}
                    </CardContent>
                  </Card>

                  <Card className="border-slate-200 bg-white shadow-sm">
                    <CardHeader>
                      <CardTitle className="text-slate-950">覆盖审计</CardTitle>
                      <CardDescription className="text-slate-600">只有显式人工覆盖时才会出现。</CardDescription>
                    </CardHeader>
                    <CardContent>
                      {regimeSelection?.override ? (
                        <div className="grid gap-3 text-sm text-slate-700 md:grid-cols-2">
                          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">操作人</p>
                            <p className="mt-1 break-all text-slate-950">{regimeSelection.override.operator ?? '未记录'}</p>
                          </div>
                          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">风险等级</p>
                            <p className="mt-1 break-all text-slate-950">{regimeSelection.override.risk_level ?? '未记录'}</p>
                          </div>
                          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 md:col-span-2">
                            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">原因</p>
                            <p className="mt-1 break-all text-slate-950">{formatRegimeText(regimeSelection.override.reason, '未记录')}</p>
                          </div>
                          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 md:col-span-2">
                            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">时间</p>
                            <p className="mt-1 break-all text-slate-950">{formatDate(regimeSelection.override.timestamp)}</p>
                          </div>
                        </div>
                      ) : (
                        <EmptyState title="未启用人工覆盖。" description="当前选择遵循默认适用优先、低权重补充、阻断默认排除。" />
                      )}
                    </CardContent>
                  </Card>
                </div>

                {regimeSelection?.warnings?.length ? (
                  <Card className="border-amber-200 bg-amber-50 shadow-sm">
                    <CardHeader>
                      <CardTitle className="text-amber-950">提示</CardTitle>
                      <CardDescription className="text-amber-800">构建过程中记录的缺失或降级信息。</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      {regimeSelection.warnings.map((item) => (
                        <p key={item} className="text-sm leading-6 text-amber-900">
                          {formatRegimeText(item, item)}
                        </p>
                      ))}
                    </CardContent>
                  </Card>
                ) : null}
              </div>
                ) : (
                  <EmptyState title="请选择一个规则版本。" description="选择版本后，这里会展示已选中、已跳过、已阻断的规则及审计字段。" />
                )}
          </SectionCard>
        </div>
      </section>
    </main>
  );
}
