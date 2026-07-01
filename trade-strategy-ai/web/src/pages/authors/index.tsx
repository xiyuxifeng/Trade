import type { PageAvailability } from '@/components/layout/business-page-shell';
import { ProductPageAdapter } from '@/components/layout/product-page-adapter';
import { useQuery } from '@tanstack/react-query';
import { ApiError } from '@/lib/api/http';
import { listAuthorProfiles } from '@/lib/api/authors';
import type { AuthorProfileVersion } from '@/types/authors';

type AuthorsPageProps = {
  availability?: PageAvailability;
};

export function AuthorsPage({ availability }: AuthorsPageProps = {}) {
  const profilesQuery = useQuery({
    queryKey: ['author-profiles'],
    queryFn: () => listAuthorProfiles(),
    enabled: availability === undefined,
  });
  const permissionDenied = profilesQuery.error instanceof ApiError && (profilesQuery.error.status === 401 || profilesQuery.error.status === 403);
  const unavailable = profilesQuery.error instanceof ApiError && profilesQuery.error.status >= 500;
  const state: PageAvailability = availability ?? (
    profilesQuery.isLoading
      ? 'loading'
      : permissionDenied
        ? 'permission_denied'
        : unavailable
          ? 'unavailable'
          : profilesQuery.error
          ? 'error'
          : profilesQuery.data?.state === 'empty'
            ? 'empty'
            : profilesQuery.data?.state === 'partial'
              ? 'partial'
              : 'ready'
  );
  const items = profilesQuery.data?.items ?? [];
  return (
    <ProductPageAdapter
      title="作者画像"
      queryState={state}
      layoutMode="library"
      purpose="汇总作者文章表达的方法、规则证据和验证观察。"
      inputDescription="输入来自已确认文章、规则证据和回测观察。"
      processingDescription="系统只展示已落库的画像版本、审核状态、证据区间和生效时间段。"
      outputDescription="输出是方法、规则和验证三类画像的版本记录，不代表作者真实实盘表现。"
      businessAction={{ label: '查看规则验证结果', to: '/rules/results' }}
      stateTitle={state === 'empty' ? '暂无正式画像版本' : undefined}
      stateDescription={state === 'empty' ? '当前没有可展示的作者画像版本；新文章、新回测或每日证据只会先形成草稿。' : undefined}
      impact={state === 'empty' ? '策略流程不能把作者画像当作已发布输入。' : undefined}
      result={<AuthorProfileVersions items={items} isLoading={profilesQuery.isLoading} error={profilesQuery.error} />}
    />
  );
}

function formatPeriod(period: { from?: string | null; to?: string | null }) {
  if (!period.from && !period.to) {
    return '未完整绑定';
  }
  return `${period.from ?? '未定'} 至 ${period.to ?? '长期'}`;
}

function AuthorProfileVersions({
  items,
  isLoading,
  error,
}: {
  items: AuthorProfileVersion[];
  isLoading: boolean;
  error: Error | null;
}) {
  if (isLoading) {
    return <p className="text-sm text-slate-600">正在读取画像版本...</p>;
  }
  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900">
        <p className="m-0 font-medium">作者画像读取失败</p>
        <p className="mt-1">页面无法确认画像版本状态，请稍后重试或检查权限。</p>
      </div>
    );
  }
  if (!items.length) {
    return (
      <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
        <p className="m-0 font-medium text-slate-900">暂无作者画像版本</p>
        <p className="mt-1">新证据会先生成草稿或修订建议，不会自动覆盖已发布画像。</p>
      </div>
    );
  }
  return (
    <div className="grid gap-3">
      {items.map((item) => (
        <article key={item.author_profile_version_id} className="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="m-0 text-base font-semibold text-slate-950">
                {item.profile_kind_label} v{item.version_no}
              </h2>
              <p className="mt-1 text-sm text-slate-600">
                {item.lifecycle_label} · 证据区间：{formatPeriod(item.evidence_period)} · 生效区间：{formatPeriod(item.effective_period)}
              </p>
            </div>
            <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700">
              {item.review_status === 'pending_review' ? '待审核' : item.lifecycle_label}
            </span>
          </div>
          {item.partial_reasons.length ? (
            <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-amber-800">
              {item.partial_reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          ) : null}
          {item.profile_kind === 'method' && item.payload?.method_profile ? (
            <div className="mt-3 grid gap-3 border-t border-slate-100 pt-3">
              <MethodField label="交易风格" values={(item.payload.method_profile as Record<string, unknown>).trading_style} />
              <MethodField label="分析框架" values={(item.payload.method_profile as Record<string, unknown>).analysis_framework} />
              <MethodField label="选股偏好" values={(item.payload.method_profile as Record<string, unknown>).stock_selection_preference} />
              <MethodField label="入场偏好" values={(item.payload.method_profile as Record<string, unknown>).entry_preferences} />
              <MethodField label="退出偏好" values={(item.payload.method_profile as Record<string, unknown>).exit_preferences} />
              <MethodField label="风险表达" values={(item.payload.method_profile as Record<string, unknown>).risk_expressions} />
              <MethodField label="持有周期" values={(item.payload.method_profile as Record<string, unknown>).holding_period_preferences} />
              <MethodField label="数据依赖" values={(item.payload.method_profile as Record<string, unknown>).data_dependency_preferences} />
              <MethodField label="市场状态假设" values={(item.payload.method_profile as Record<string, unknown>).market_state_assumptions} />
            </div>
          ) : null}
          {item.profile_kind === 'rule' && item.payload?.rule_profile ? (
            <div className="mt-3 grid gap-3 border-t border-slate-100 pt-3">
              <RuleProfileSection label="规则类型分布" value={formatRuleTypes((item.payload.rule_profile as Record<string, unknown>).rule_type_distribution)} />
              <RuleProfileSection label="规则族" value={formatRuleFamilies((item.payload.rule_profile as Record<string, unknown>).rule_families)} />
              <RuleProfileSection label="可量化程度" value={formatRuleText((item.payload.rule_profile as Record<string, unknown>).quantifiability, 'label')} />
              <RuleProfileSection label="数据依赖" value={formatRuleDependencies((item.payload.rule_profile as Record<string, unknown>).data_dependencies)} />
              <RuleProfileSection label="重复与冲突" value={formatConflictSummary((item.payload.rule_profile as Record<string, unknown>).repeat_conflict_summary)} />
              <RuleProfileSection label="代表性规则" value={formatRepresentativeRules((item.payload.rule_profile as Record<string, unknown>).representative_rules)} />
            </div>
          ) : null}
          {item.profile_kind === 'validated' && item.payload?.validated_profile ? (
            <div className="mt-3 grid gap-3 border-t border-slate-100 pt-3">
              <RuleProfileSection label="优势规则类型" value={formatRuleTypes((item.payload.validated_profile as Record<string, unknown>).strong_rule_types)} />
              <RuleProfileSection label="弱势规则类型" value={formatRuleTypes((item.payload.validated_profile as Record<string, unknown>).weak_rule_types)} />
              <RuleProfileSection label="优势市场状态" value={formatMarketStates((item.payload.validated_profile as Record<string, unknown>).strong_market_states)} />
              <RuleProfileSection label="弱势市场状态" value={formatMarketStates((item.payload.validated_profile as Record<string, unknown>).weak_market_states)} />
              <RuleProfileSection label="常见失效模式" value={formatFailureModes((item.payload.validated_profile as Record<string, unknown>).common_failure_modes)} />
              <RuleProfileSection label="数据覆盖" value={formatValidatedCoverage((item.payload.validated_profile as Record<string, unknown>).data_coverage)} />
              <RuleProfileSection label="样本量" value={formatValidatedSampleCount((item.payload.validated_profile as Record<string, unknown>).sample_count)} />
              <RuleProfileSection label="置信度" value={formatRuleText((item.payload.validated_profile as Record<string, unknown>).confidence, 'overall')} />
            </div>
          ) : null}
          <p className="mt-3 text-xs text-slate-500">画像来自文章、规则和回测证据版本绑定，不是作者真实实盘收益描述。</p>
          {item.limitations.length ? (
            <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-slate-500">
              {item.limitations.map((limitation) => (
                <li key={limitation}>{limitation}</li>
              ))}
            </ul>
          ) : null}
        </article>
      ))}
    </div>
  );
}

function MethodField({ label, values }: { label: string; values: unknown }) {
  const items = Array.isArray(values)
    ? values
        .map((item) => {
          if (typeof item === 'string') {
            return item;
          }
          if (item && typeof item === 'object' && 'name' in item) {
            return String((item as { name: unknown }).name);
          }
          if (item && typeof item === 'object' && 'market_state' in item) {
            return String((item as { market_state: unknown }).market_state);
          }
          return null;
        })
        .filter((item): item is string => Boolean(item))
    : [];
  if (!items.length) {
    return null;
  }
  return (
    <div className="grid gap-1">
      <p className="m-0 text-xs font-medium text-slate-500">{label}</p>
      <p className="m-0 text-sm text-slate-800">{items.join('、')}</p>
    </div>
  );
}

function RuleProfileSection({ label, value }: { label: string; value: string | null }) {
  if (!value) {
    return null;
  }
  return (
    <div className="grid gap-1">
      <p className="m-0 text-xs font-medium text-slate-500">{label}</p>
      <p className="m-0 text-sm text-slate-800">{value}</p>
    </div>
  );
}

function formatRuleTypes(value: unknown) {
  if (!Array.isArray(value)) {
    return null;
  }
  const items = value
    .map((item) => {
      if (!item || typeof item !== 'object') {
        return null;
      }
      const ruleType = 'rule_type' in item ? String((item as { rule_type: unknown }).rule_type) : null;
      const count = 'count' in item ? String((item as { count: unknown }).count) : null;
      return ruleType && count ? `${ruleType}：${count} 条` : null;
    })
    .filter((item): item is string => Boolean(item));
  return items.length ? items.join('；') : null;
}

function formatRuleFamilies(value: unknown) {
  if (!Array.isArray(value)) {
    return null;
  }
  const items = value
    .map((item) => {
      if (!item || typeof item !== 'object') {
        return null;
      }
      const name = 'name' in item ? String((item as { name: unknown }).name) : null;
      const count = 'member_count' in item ? String((item as { member_count: unknown }).member_count) : null;
      return name && count ? `${name}（${count} 条）` : null;
    })
    .filter((item): item is string => Boolean(item));
  return items.length ? items.join('；') : null;
}

function formatRuleDependencies(value: unknown) {
  if (!Array.isArray(value)) {
    return null;
  }
  const items = value
    .map((item) => {
      if (!item || typeof item !== 'object') {
        return null;
      }
      const name = 'name' in item ? String((item as { name: unknown }).name) : null;
      const count = 'count' in item ? String((item as { count: unknown }).count) : null;
      return name && count ? `${name}（${count} 条规则）` : null;
    })
    .filter((item): item is string => Boolean(item));
  return items.length ? items.join('；') : null;
}

function formatConflictSummary(value: unknown) {
  if (!value || typeof value !== 'object') {
    return null;
  }
  const count = 'conflict_pair_count' in value ? Number((value as { conflict_pair_count: unknown }).conflict_pair_count) : 0;
  if (count > 0) {
    return `发现 ${count} 组冲突规则`;
  }
  const duplicateCount = 'exact_duplicate_pair_count' in value ? Number((value as { exact_duplicate_pair_count: unknown }).exact_duplicate_pair_count) : 0;
  if (duplicateCount > 0) {
    return `发现 ${duplicateCount} 组完全重复规则`;
  }
  return '当前未发现明显冲突';
}

function formatRepresentativeRules(value: unknown) {
  if (!Array.isArray(value)) {
    return null;
  }
  const items = value
    .map((item) => {
      if (!item || typeof item !== 'object' || !('title' in item)) {
        return null;
      }
      return String((item as { title: unknown }).title);
    })
    .filter((item): item is string => Boolean(item));
  return items.length ? items.join('、') : null;
}

function formatRuleText(value: unknown, key: string) {
  if (!value || typeof value !== 'object' || !(key in value)) {
    return null;
  }
  return String((value as Record<string, unknown>)[key]);
}

function formatMarketStates(value: unknown) {
  if (!Array.isArray(value)) {
    return null;
  }
  const items = value
    .map((item) => {
      if (!item || typeof item !== 'object') {
        return null;
      }
      const marketState = 'market_state' in item ? String((item as { market_state: unknown }).market_state) : null;
      const count = 'count' in item ? String((item as { count: unknown }).count) : null;
      return marketState && count ? `${marketState}：${count} 次` : null;
    })
    .filter((item): item is string => Boolean(item));
  return items.length ? items.join('；') : null;
}

function formatFailureModes(value: unknown) {
  if (!Array.isArray(value)) {
    return null;
  }
  const items = value
    .map((item) => {
      if (!item || typeof item !== 'object') {
        return null;
      }
      const reason = 'reason' in item ? String((item as { reason: unknown }).reason) : null;
      const count = 'count' in item ? String((item as { count: unknown }).count) : null;
      return reason && count ? `${reason}（${count} 次）` : null;
    })
    .filter((item): item is string => Boolean(item));
  return items.length ? items.join('；') : null;
}

function formatValidatedCoverage(value: unknown) {
  if (!value || typeof value !== 'object') {
    return null;
  }
  const coverage = value as Record<string, unknown>;
  const profiles = typeof coverage.total_applicability_profiles === 'number' ? coverage.total_applicability_profiles : null;
  const kaipan = typeof coverage.kaipan_limitation_profiles === 'number' ? coverage.kaipan_limitation_profiles : null;
  if (profiles === null) {
    return null;
  }
  return kaipan !== null ? `正式适用性画像 ${profiles} 条，Kaipan 覆盖限制 ${kaipan} 条` : `正式适用性画像 ${profiles} 条`;
}

function formatValidatedSampleCount(value: unknown) {
  if (!value || typeof value !== 'object') {
    return null;
  }
  const counts = value as Record<string, unknown>;
  const total = typeof counts.total === 'number' ? counts.total : null;
  const insufficient = typeof counts.insufficient_sample_profiles === 'number' ? counts.insufficient_sample_profiles : null;
  if (total === null) {
    return null;
  }
  return insufficient !== null ? `${total}（样本不足画像 ${insufficient} 条）` : String(total);
}
