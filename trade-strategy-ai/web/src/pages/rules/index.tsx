import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { PageAvailability } from '@/components/layout/business-page-shell';
import { ProductPageAdapter } from '@/components/layout/product-page-adapter';
import { PageHeader } from '@/components/layout/page-header';
import { EmptyState, ErrorState, LoadingState, SectionCard } from '@/components/kit';
import { ApiError } from '@/lib/api/http';
import { getRuleReviewCandidate, listRuleReviewCandidates } from '@/lib/api/rule-review';
import { FormalBacktestResults } from '@/features/backtest/formal-backtest-results';
import { FormalBacktestWorkbench } from '@/features/backtest/formal-backtest-workbench';
import { RulePoolPage } from '@/pages/rule-pool';
import type { RuleReviewCandidateListItem } from '@/types/rule-review';

type FormalPageProps = {
  availability?: PageAvailability;
};

const dependencyLabels: Record<string, string> = {
  ohlcv_1d: '历史行情',
  ohlcv: '历史行情',
  kaipan: '盘前增强数据',
  market_state: '市场状态',
};

const relationLabels: Record<string, string> = {
  exact_duplicate: '完全重复',
  parameter_variant: '参数变体',
  conflict: '冲突规则',
  similar_rule: '相近规则',
  distinct: '不同规则',
};

function formatDependencyLabel(value: string) {
  return dependencyLabels[value] ?? value;
}

function formatRelationLabel(value: string) {
  return relationLabels[value] ?? '待人工确认';
}

export function RulesReviewPage({ availability }: FormalPageProps = {}) {
  const state = availability ?? undefined;
  if (state) {
    return (
      <ProductPageAdapter
        title="历史候选审计"
        queryState={state}
        purpose="只读查看旧抽取候选；新内容从文章分类抽取结果进入对应通道。"
        inputDescription="输入来自文章提取结果和当前规则证据。"
        processingDescription="系统读取真实候选规则、证据和审核状态。"
        outputDescription="输出为不可变历史证据，不提供晋级或回测动作。"
        businessAction={{ label: '查看分类抽取结果', to: '/research/results' }}
      />
    );
  }
  return <RulesReviewWorkbench />;
}

function RulesReviewWorkbench() {
  const [requireHumanOnly, setRequireHumanOnly] = useState(false);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null);

  const candidatesQuery = useQuery({
    queryKey: ['rule-review', 'candidates', requireHumanOnly],
    queryFn: () => listRuleReviewCandidates({ require_human_review_only: requireHumanOnly }),
    staleTime: 30_000,
  });

  const candidateItems = candidatesQuery.data?.items ?? [];

  useEffect(() => {
    if (!candidateItems.length) {
      setSelectedCandidateId(null);
      return;
    }
    if (!selectedCandidateId || !candidateItems.some((item) => item.candidate_id === selectedCandidateId)) {
      setSelectedCandidateId(candidateItems[0].candidate_id);
    }
  }, [candidateItems, selectedCandidateId]);

  const detailQuery = useQuery({
    queryKey: ['rule-review', 'candidate', selectedCandidateId],
    queryFn: () => getRuleReviewCandidate(selectedCandidateId as string),
    enabled: Boolean(selectedCandidateId),
    staleTime: 30_000,
  });

  const selectedCandidate = detailQuery.data;
  const partialState = Boolean(
    selectedCandidate &&
      (selectedCandidate.source_article.summary_status === 'unavailable' || selectedCandidate.automatic_review.blocked_reason),
  );

  if (candidatesQuery.isLoading) {
    return (
      <main className="page-stack">
        <PageHeader kicker="正式入口" title="规则审核工作台" description="查看候选规则、来源证据、自动判断和人工处理动作。" />
        <LoadingState label="正在加载页面" description="系统正在读取候选规则和审核状态。" />
      </main>
    );
  }

  if (candidatesQuery.error) {
    const error = candidatesQuery.error as ApiError;
    const permissionDenied = error.status === 403;
    return (
      <main className="page-stack">
        <PageHeader kicker="正式入口" title="规则审核工作台" description="查看候选规则、来源证据、自动判断和人工处理动作。" />
        <ErrorState
          category={permissionDenied ? 'permission denied' : 'provider unavailable'}
          title={permissionDenied ? '没有权限' : '加载失败'}
          description={permissionDenied ? '当前账号不能执行规则审核。' : '候选规则列表暂时无法加载。'}
          suggestion={permissionDenied ? '请联系管理员开通审核权限。' : '请稍后重试；如果问题持续，请检查后端服务和数据状态。'}
        />
      </main>
    );
  }

  if (!candidateItems.length) {
    return (
      <main className="page-stack">
        <PageHeader kicker="正式入口" title="规则审核工作台" description="查看候选规则、来源证据、自动判断和人工处理动作。" />
        <EmptyState
          title="当前没有需要处理的候选规则"
          description="候选规则已经处理完成，或当前筛选条件下没有待审核项目。"
        />
      </main>
    );
  }

  return (
    <main className="page-stack">
      <PageHeader
        kicker="正式入口"
        title="历史候选审计"
        description="旧候选保持只读，用于追溯原文、旧判断和失败模式；不再从此入口晋级。"
      />

      <SectionCard
        title="筛选条件"
        description="这里只展示正式审核入口，不再使用旧入口直接改状态。"
      >
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input
            checked={requireHumanOnly}
            onChange={(event) => setRequireHumanOnly(event.target.checked)}
            type="checkbox"
          />
          仅看需要人工判断的候选规则
        </label>
      </SectionCard>

      <section className="grid gap-6 lg:grid-cols-[320px,1fr]">
        <SectionCard title="历史候选列表" description="这些记录仅作审计证据，不代表当前分类结论。">
          <div className="space-y-3">
            {candidateItems.map((item: RuleReviewCandidateListItem) => (
              <button
                key={item.candidate_id}
                type="button"
                onClick={() => setSelectedCandidateId(item.candidate_id)}
                className={`w-full rounded-lg border p-4 text-left ${
                  selectedCandidateId === item.candidate_id ? 'border-sky-300 bg-sky-50' : 'border-slate-200 bg-white'
                }`}
              >
                <p className="text-sm font-semibold text-slate-950">{item.title}</p>
                <p className="mt-1 text-xs text-slate-500">{item.source_article_title}</p>
                <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-600">
                  <span className="rounded-full border border-slate-200 px-2 py-1">{item.automatic_review.label}</span>
                  <span className="rounded-full border border-slate-200 px-2 py-1">{item.current_review_state}</span>
                </div>
              </button>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="历史候选详情" description="展示原文摘要、旧判断理由和数据缺口；所有写入动作已停用。">
          {detailQuery.isLoading || !selectedCandidate ? (
            <LoadingState label="正在加载候选规则" description="系统正在读取来源证据和审核详情。" />
          ) : (
            <div className="space-y-5">
              {partialState ? (
                <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                  <p className="font-medium">部分信息暂不可用</p>
                  <p className="mt-1">当前候选规则的部分来源摘要或依赖证据无法证明，系统保持真实不可用状态。</p>
                </div>
              ) : null}

              <div className="space-y-2">
                <h2 className="text-xl font-semibold text-slate-950">{selectedCandidate.title}</h2>
                <div className="flex flex-wrap gap-2 text-sm text-slate-600">
                  <span className="rounded-full border border-slate-200 px-2 py-1">{selectedCandidate.automatic_review.label}</span>
                  <span className="rounded-full border border-slate-200 px-2 py-1">{selectedCandidate.current_review_state}</span>
                  {selectedCandidate.current_lifecycle_state ? (
                    <span className="rounded-full border border-slate-200 px-2 py-1">{selectedCandidate.current_lifecycle_state}</span>
                  ) : null}
                </div>
              </div>

              <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">来源文章</p>
                <p className="mt-2 text-sm font-medium text-slate-950">{selectedCandidate.source_article.title}</p>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  {selectedCandidate.source_article.summary ?? '摘要暂不可用'}
                </p>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-lg border border-slate-200 bg-white p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">自动审核理由</p>
                  <ul className="mt-2 space-y-2 text-sm text-slate-700">
                    {selectedCandidate.automatic_review.reasons.map((reason) => (
                      <li key={reason}>{reason}</li>
                    ))}
                  </ul>
                </div>
                <div className="rounded-lg border border-slate-200 bg-white p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">数据依赖与缺失项</p>
                  <p className="mt-2 text-sm text-slate-700">
                    数据依赖：{selectedCandidate.data_dependencies.length ? selectedCandidate.data_dependencies.map(formatDependencyLabel).join('、') : '无'}
                  </p>
                  <p className="mt-2 text-sm text-slate-700">
                    缺失字段：{selectedCandidate.missing_fields.length ? selectedCandidate.missing_fields.join('、') : '无'}
                  </p>
                </div>
              </div>

              <div className="rounded-lg border border-slate-200 bg-white p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">重复与冲突发现</p>
                {selectedCandidate.governance.related_rules.length ? (
                  <div className="mt-2 space-y-3">
                    {selectedCandidate.governance.related_rules.map((item, index) => (
                      <div key={`${item.relation}-${index}`} className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
                        <p className="font-medium text-slate-950">{item.title}</p>
                        <p className="mt-1">关系：{formatRelationLabel(item.relation)}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="mt-2 text-sm text-slate-600">当前没有发现重复、参数变体或冲突规则。</p>
                )}
              </div>

              <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
                历史候选为只读审计证据。请在文章的“分类抽取结果”中处理新项目。
              </div>
            </div>
          )}
        </SectionCard>
      </section>
    </main>
  );
}

export function RulesLibraryPage({ availability }: FormalPageProps = {}) {
  const state = availability ?? 'partial';
  return (
    <ProductPageAdapter
      title="正式规则"
      queryState={state}
      layoutMode="library"
      purpose="查看已经通过人工审核的规则，并说明当前版本化边界。"
      inputDescription="输入来自现有规则库中的真实审核状态。"
      processingDescription="系统按真实审核结果展示规则，不推断尚未建立的正式版本。"
      outputDescription="当前输出为已审核规则；完整规则版本能力仍待后续任务建立。"
      businessAction={{ label: '查看待审核规则', to: '/rules/review' }}
      result={availability ? undefined : <RulePoolPage productMode />}
    />
  );
}

export function RulesBacktestsPage({ availability }: FormalPageProps = {}) {
  const state = availability ?? 'partial';
  return (
    <ProductPageAdapter
      title="回测实验"
      queryState={state}
      purpose="检查规则回测所需数据，并创建可追溯的正式回测记录。"
      inputDescription="选择规则或规则族、回测区间、标的范围、基准、回测模式和数据等级。"
      processingDescription="系统只核对正式规则版本、正式数据快照和所需市场状态，不用临时文件或实时数据补齐。"
      outputDescription="输出为可运行、可降级、需修复或不可运行的依赖结论，以及正式回测记录入口。"
      businessAction={{ label: '查看作者画像', to: '/authors' }}
      result={availability ? undefined : <FormalBacktestWorkbench />}
    />
  );
}

export function RulesResultsPage({ availability }: FormalPageProps = {}) {
  const state = availability ?? 'partial';
  return (
    <ProductPageAdapter
      title="回测结果"
      queryState={state}
      layoutMode="detail"
      purpose="查看全周期及分市场状态的回测验证结果。"
      inputDescription="输入来自已经完成且可追溯的回测记录。"
      processingDescription="系统只展示已保存的真实结果和明确的数据缺口。"
      outputDescription="输出为全周期和分市场状态结果、覆盖情况、限制说明和可复现证据。"
      businessAction={{ label: '返回回测实验', to: '/rules/backtests' }}
      result={availability ? undefined : <FormalBacktestResults />}
    />
  );
}
