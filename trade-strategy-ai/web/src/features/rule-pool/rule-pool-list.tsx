import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowRight, Search } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { PageHeader } from '@/components/layout/page-header';
import { EmptyState, ErrorState, LoadingState, SectionCard, StatusBadge } from '@/components/kit';
import { listRulePool, listRulePoolFilterOptions } from '@/lib/api/rule-pool';
import { buildErrorRecoveryState } from '@/lib/error-recovery';
import type { RulePoolQuery, RuleSummaryItem } from '@/types/rule-pool';

const DEFAULT_FILTERS: RulePoolQuery = {
  status: 'pending',
  rule_type: '',
  mapping_status: '',
  source_type: '',
  instrument_focus: '',
  skip_no_mapped: false,
  skip: 0,
  limit: 18,
};

function formatConfidence(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return 'n/a';
  }
  return `${(value * 100).toFixed(1)}%`;
}

function mapLabel(value: string, mapping: Record<string, string>) {
  return mapping[value] || value;
}

const REVIEW_STATUS_LABELS: Record<string, string> = {
  pending: '待审核',
  approved: '已通过',
  rejected: '已拒绝',
};

const MAPPING_STATUS_LABELS: Record<string, string> = {
  unmapped: '未映射',
  pending: '待映射',
  mapped: '已映射',
  unmappable: '不可映射',
};

const SOURCE_TYPE_LABELS: Record<string, string> = {
  standalone: '规则型文章',
  derived: '交易推导',
  experience: '经验规则',
};

function RuleRow({ item, onClick }: { item: RuleSummaryItem; onClick: () => void }) {
  return (
    <button
      type="button"
      aria-label={`查看详情 ${item.rule_id}`}
      onClick={onClick}
      className="w-full rounded-2xl border border-slate-200 bg-white p-4 text-left transition-colors hover:border-sky-200 hover:bg-slate-50"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-semibold text-slate-950">{item.rule_id}</p>
            <StatusBadge value={item.review_status} />
          </div>
          <p className="text-xs text-slate-500">
            {item.rule_type} · {item.instrument_focus} · {mapLabel(item.source_type, SOURCE_TYPE_LABELS)}
          </p>
        </div>
        <div className="flex items-center gap-2 text-slate-400">
          <span className="text-xs font-medium text-slate-600">查看详情</span>
          <ArrowRight className="h-4 w-4" />
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
        <span className="rounded-full border border-slate-200 px-2 py-1">映射 {mapLabel(item.mapping_status, MAPPING_STATUS_LABELS)}</span>
        <span className="rounded-full border border-slate-200 px-2 py-1">置信度 {formatConfidence(item.validated_confidence ?? item.initial_confidence)}</span>
        <span className="rounded-full border border-slate-200 px-2 py-1">回测样本 {item.backtest_samples}</span>
        <span className="rounded-full border border-slate-200 px-2 py-1">审核 {mapLabel(item.review_status, REVIEW_STATUS_LABELS)}</span>
      </div>
    </button>
  );
}

function SummaryStat({ label, value }: { label: string; value: string | number | null | undefined }) {
  const renderedValue = value === null || value === undefined ? 'n/a' : value;
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 break-all text-lg font-semibold text-slate-950">{renderedValue}</p>
    </div>
  );
}

function FilterSelect({
  label,
  ariaLabel,
  value,
  onChange,
  options,
  optionLabels,
  placeholder = '全部',
}: {
  label: string;
  ariaLabel: string;
  value: string;
  onChange: (value: string) => void;
  options: string[];
  optionLabels?: Record<string, string>;
  placeholder?: string;
}) {
  return (
    <label className="space-y-2 text-sm text-slate-700">
      <span className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</span>
      <Select
        aria-label={ariaLabel}
        className="border-slate-200 bg-white text-slate-900"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {mapLabel(option, optionLabels ?? {})}
            {optionLabels?.[option] ? ` (${option})` : ''}
          </option>
        ))}
      </Select>
    </label>
  );
}

export function RulePoolListPage({ productMode = false }: { productMode?: boolean } = {}) {
  const navigate = useNavigate();
  const [draftFilters, setDraftFilters] = useState<RulePoolQuery>(DEFAULT_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<RulePoolQuery>(DEFAULT_FILTERS);

  const filterOptionsQuery = useQuery({
    queryKey: ['rule-pool', 'filter-options'],
    queryFn: () => listRulePoolFilterOptions(),
    staleTime: 60_000,
  });

  const rulesQuery = useQuery({
    queryKey: ['rule-pool', appliedFilters],
    queryFn: () =>
      listRulePool({
        status: appliedFilters.status || undefined,
        rule_type: appliedFilters.rule_type || undefined,
        mapping_status: appliedFilters.mapping_status || undefined,
        source_type: appliedFilters.source_type || undefined,
        instrument_focus: appliedFilters.instrument_focus || undefined,
        skip: appliedFilters.skip,
        limit: appliedFilters.limit,
      }),
    staleTime: 30_000,
  });

  const filterOptions = filterOptionsQuery.data ?? {
    status: 'success',
    review_statuses: Object.keys(REVIEW_STATUS_LABELS),
    mapping_statuses: Object.keys(MAPPING_STATUS_LABELS),
    source_types: Object.keys(SOURCE_TYPE_LABELS),
    rule_types: [],
    instrument_focuses: [],
  };

  const ruleItems = rulesQuery.data?.items ?? [];
  const summary = useMemo(
    () => ({
      total: rulesQuery.data?.total ?? 0,
      pageCount: ruleItems.length,
      pending: ruleItems.filter((item) => item.review_status === 'pending').length,
      approved: ruleItems.filter((item) => item.review_status === 'approved').length,
      mapped: ruleItems.filter((item) => item.mapped).length,
    }),
    [ruleItems, rulesQuery.data?.total],
  );

  const queryError = rulesQuery.error;

  if (queryError) {
    return (
      <main className="page-stack">
        <PageHeader kicker="正式入口" title="规则池审核中心" description="在 Web 中查看规则证据、回测结果和审核动作。" />
        <ErrorState
          {...buildErrorRecoveryState(queryError, 'strategy')}
          onRetry={() => {
            void rulesQuery.refetch();
            void filterOptionsQuery.refetch();
          }}
        />
      </main>
    );
  }

  return (
    <main className="page-stack">
      {!productMode ? (
        <PageHeader
          kicker="正式入口"
          title="规则池审核中心"
          description="查看规则列表、回测证据与审核入口，并在规则详情页完成审核和回测操作。"
        />
      ) : null}

      <SectionCard
        title="规则筛选"
        description="所有筛选项都来自全量规则池，不再依赖当前页数据。"
      >
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            setAppliedFilters({ ...draftFilters, skip: 0 });
          }}
        >
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <FilterSelect
              label="审核状态"
              ariaLabel="审核状态"
              value={draftFilters.status ?? ''}
              onChange={(value) => setDraftFilters((current) => ({ ...current, status: value || undefined }))}
              options={filterOptions.review_statuses}
              optionLabels={REVIEW_STATUS_LABELS}
            />
            <FilterSelect
              label="规则类型"
              ariaLabel="规则类型"
              value={draftFilters.rule_type ?? ''}
              onChange={(value) => setDraftFilters((current) => ({ ...current, rule_type: value || undefined }))}
              options={filterOptions.rule_types}
            />
            <FilterSelect
              label="映射状态"
              ariaLabel="映射状态"
              value={draftFilters.mapping_status ?? ''}
              onChange={(value) => setDraftFilters((current) => ({ ...current, mapping_status: value || undefined }))}
              options={filterOptions.mapping_statuses}
              optionLabels={MAPPING_STATUS_LABELS}
            />
            <FilterSelect
              label="来源类型"
              ariaLabel="来源类型"
              value={draftFilters.source_type ?? ''}
              onChange={(value) => setDraftFilters((current) => ({ ...current, source_type: value || undefined }))}
              options={filterOptions.source_types}
              optionLabels={SOURCE_TYPE_LABELS}
            />
            <FilterSelect
              label="标的范围"
              ariaLabel="标的范围"
              value={draftFilters.instrument_focus ?? ''}
              onChange={(value) => setDraftFilters((current) => ({ ...current, instrument_focus: value || undefined }))}
              options={filterOptions.instrument_focuses}
            />
          </div>

          <div className="flex flex-wrap gap-3">
            <Button type="submit">
              <Search className="mr-2 h-4 w-4" />
              搜索
            </Button>
            <Button
              type="button"
              variant="outline"
              className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
              onClick={() => {
                setDraftFilters(DEFAULT_FILTERS);
                setAppliedFilters(DEFAULT_FILTERS);
              }}
            >
              重置
            </Button>
          </div>
        </form>
      </SectionCard>

      <SectionCard title="规则概览与列表" description="当前筛选的统计和列表都在这个卡片里。">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <SummaryStat label="总数" value={summary.total} />
          <SummaryStat label="本页数量" value={summary.pageCount} />
          <SummaryStat label="待审核" value={summary.pending} />
          <SummaryStat label="已通过 / 已映射" value={`${summary.approved} / ${summary.mapped}`} />
        </div>

        <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-slate-950">规则列表</p>
              <p className="text-xs text-slate-500">{rulesQuery.data?.total ?? 0} 条匹配记录，列表区域可独立滚动。</p>
            </div>
            <Badge variant="info">{rulesQuery.data?.total ?? 0} 条可见</Badge>
          </div>

          <div className="mt-4 max-h-[40rem] overflow-auto pr-1">
            {rulesQuery.isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-24 w-full bg-slate-100" />
                <Skeleton className="h-24 w-full bg-slate-100" />
                <Skeleton className="h-24 w-full bg-slate-100" />
              </div>
            ) : ruleItems.length ? (
              <div className="grid gap-3">
                {ruleItems.map((item) => (
                  <RuleRow
                    key={item.rule_id}
                    item={item}
                    onClick={() => navigate(`/rule-pool/${encodeURIComponent(item.rule_id)}`)}
                  />
                ))}
              </div>
            ) : (
              <EmptyState
                title="没有符合条件的规则"
                description="当前筛选没有返回规则条目，可以调整筛选后重新搜索。"
                actionLabel="重置筛选"
                onAction={() => {
                  setDraftFilters(DEFAULT_FILTERS);
                  setAppliedFilters(DEFAULT_FILTERS);
                }}
              />
            )}
          </div>
        </div>
      </SectionCard>

      {filterOptionsQuery.isError ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          规则筛选选项加载失败，已回退到默认选项。
        </div>
      ) : null}

      {rulesQuery.isFetching ? <LoadingState label="刷新规则列表" description="正在读取规则池列表。" /> : null}
    </main>
  );
}
