import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ExternalLink } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { PageHeader } from '@/components/layout/page-header';
import { ProductPageAdapter } from '@/components/layout/product-page-adapter';
import { LoadingState, EmptyState, ErrorState, SectionCard } from '@/components/kit';
import { ApiError } from '@/lib/api/http';
import { listArticles } from '@/lib/api/articles';
import { getArticleAnalysis, reviewArticleCandidate, runArticleAnalysis } from '@/lib/api/article-analysis';
import type { ArticleAnalysisCandidate, ArticleAnalysisDetail } from '@/types/article-analysis';
import type { ArticleListResponse } from '@/types/articles';

type ProductNavigationTargets = {
  back: string;
  library: string;
  add: string;
  results: string;
};

type ResearchModeProps = {
  productMode?: boolean;
  navigationTargets?: Partial<ProductNavigationTargets>;
};

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return '请求失败';
}

function isPermissionDenied(error: unknown) {
  return error instanceof ApiError && (error.status === 401 || error.status === 403);
}

function isUnavailable(error: unknown) {
  return error instanceof ApiError && error.status >= 500;
}

function resolveAvailability({
  loading,
  error,
  empty,
  partial,
}: {
  loading: boolean;
  error: unknown;
  empty?: boolean;
  partial?: boolean;
}): Exclude<import('@/components/layout/business-page-shell').PageAvailability, 'ready'> | 'ready' {
  if (loading) return 'loading';
  if (isPermissionDenied(error)) return 'permission_denied';
  if (isUnavailable(error)) return 'unavailable';
  if (error) return 'error';
  if (partial) return 'partial';
  if (empty) return 'empty';
  return 'ready';
}

function formatTimestamp(value: string | null | undefined) {
  if (!value) return '未记录';
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function formatJsonBlock(value: unknown) {
  if (value === null || value === undefined) return '未提供';
  if (Array.isArray(value) && value.length === 0) return '未提供';
  if (typeof value === 'object' && !Array.isArray(value) && Object.keys(value as Record<string, unknown>).length === 0) {
    return '未提供';
  }
  return JSON.stringify(value, null, 2);
}

function automaticReviewLabel(status: ArticleAnalysisCandidate['automatic_review']['status']) {
  if (status === 'pending_backtest') return '待回测';
  if (status === 'needs_human_review') return '需要人工确认';
  return '建议拒绝';
}

function automaticReviewVariant(status: ArticleAnalysisCandidate['automatic_review']['status']) {
  if (status === 'pending_backtest') return 'success' as const;
  if (status === 'needs_human_review') return 'warning' as const;
  return 'destructive' as const;
}

function ArticlePageShell({
  title,
  description,
  summary,
  children,
}: {
  title: string;
  description: string;
  summary: string;
  children: ReactNode;
}) {
  const navigate = useNavigate();
  return (
    <main className="page-stack">
      <PageHeader kicker="文章与规则" title={title} description={description} actionLabel="返回文章与规则" onAction={() => navigate('/articles')} />
      <SectionCard title="页面摘要" description={summary}>
        {children}
      </SectionCard>
    </main>
  );
}

function ArticleErrorState({
  error,
  onRetry,
  title,
}: {
  error: unknown;
  onRetry?: () => void;
  title: string;
}) {
  return (
    <ErrorState
      category={error instanceof ApiError && error.status === 404 ? 'data empty' : 'network error'}
      title={title}
      description={getErrorMessage(error)}
      suggestion="刷新页面或切换文章后重试。"
      retryLabel="重试"
      onRetry={onRetry}
    />
  );
}

export function ArticleResultsPage({ productMode = false, navigationTargets }: ResearchModeProps = {}) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [message, setMessage] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [selectedArticleId, setSelectedArticleId] = useState<string | null>(null);
  const pageSize = 8;
  const scrollHeightClass = 'h-[calc(100vh-330px)] overflow-y-auto';

  const articlesQuery = useQuery<ArticleListResponse, ApiError>({
    queryKey: ['articles', 'analysis-results', page],
    queryFn: () => listArticles({ page, page_size: pageSize }),
    staleTime: 20_000,
  });

  const articles = articlesQuery.data?.items ?? [];
  const totalCount = articlesQuery.data?.total ?? 0;
  const totalPages = articlesQuery.data?.pages ?? 0;
  const selectedArticle = useMemo(() => {
    if (!selectedArticleId) return articles[0] ?? null;
    return articles.find((item) => item.id === selectedArticleId) ?? articles[0] ?? null;
  }, [articles, selectedArticleId]);

  useEffect(() => {
    if (articles.length === 0) {
      setSelectedArticleId(null);
      return;
    }
    if (!selectedArticleId || !articles.some((item) => item.id === selectedArticleId)) {
      setSelectedArticleId(articles[0].id);
    }
  }, [articles, selectedArticleId]);

  const detailQuery = useQuery<ArticleAnalysisDetail, ApiError>({
    queryKey: ['article-analysis', selectedArticle?.id],
    queryFn: () => getArticleAnalysis(selectedArticle?.id ?? ''),
    enabled: Boolean(selectedArticle?.id),
    staleTime: 20_000,
  });

  const runAnalysisMutation = useMutation({
    mutationFn: async (articleId: string) => runArticleAnalysis(articleId),
    onSuccess: async (detail) => {
      setMessage('文章分析已更新。');
      queryClient.setQueryData(['article-analysis', detail.article.article_id], detail);
      await queryClient.invalidateQueries({ queryKey: ['article-analysis', detail.article.article_id] });
    },
    onError: (error: unknown) => setMessage(getErrorMessage(error)),
  });

  const reviewMutation = useMutation({
    mutationFn: async (payload: { articleId: string; candidateId: string; decision: 'approve' | 'reject' }) =>
      reviewArticleCandidate(payload.articleId, payload.candidateId, {
        decision: payload.decision,
        reason: payload.decision === 'approve' ? '人工确认后进入待回测。' : '人工审核后拒绝该候选规则。',
      }),
    onSuccess: async (detail) => {
      setMessage('人工审核结果已保存。');
      queryClient.setQueryData(['article-analysis', detail.article.article_id], detail);
      await queryClient.invalidateQueries({ queryKey: ['article-analysis', detail.article.article_id] });
    },
    onError: (error: unknown) => setMessage(getErrorMessage(error)),
  });

  const availability = resolveAvailability({
    loading: articlesQuery.isLoading || (Boolean(selectedArticle?.id) && detailQuery.isLoading && !detailQuery.data),
    error: articlesQuery.error ?? detailQuery.error ?? null,
    empty: !articlesQuery.isLoading && !articlesQuery.error && articles.length === 0,
    partial: detailQuery.data?.status === 'partial',
  });

  const detailPanel = !selectedArticle ? (
    <EmptyState title="请选择一篇文章" description="从左侧列表选择文章后，右侧会展示分析结果和审核动作。" />
  ) : detailQuery.isLoading ? (
    <LoadingState label="正在加载文章分析" description="正在读取当前文章的结构化结果、候选规则和审核状态。" />
  ) : detailQuery.error ? (
    <ArticleErrorState error={detailQuery.error} title="文章分析加载失败" onRetry={() => void detailQuery.refetch()} />
  ) : !detailQuery.data ? (
    <EmptyState title="暂无分析结果" description="当前文章还没有可展示的分析结果。" />
  ) : (
    <div className="space-y-6">
      <div className="rounded-[24px] border border-slate-200 bg-slate-50 p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-lg font-semibold tracking-tight text-slate-950">{detailQuery.data.article.title}</p>
            <p className="mt-1 text-xs text-slate-600">
              {detailQuery.data.article.author_name ?? detailQuery.data.article.author_id ?? '未记录'} · {detailQuery.data.article.source}
            </p>
            <p className="mt-1 break-all text-[11px] text-slate-500">{detailQuery.data.article.source_url}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={detailQuery.data.status === 'ready' ? 'success' : detailQuery.data.status === 'partial' ? 'warning' : 'default'}>
              {detailQuery.data.status === 'ready' ? '分析已完成' : detailQuery.data.status === 'partial' ? '部分完成' : '暂无结果'}
            </Badge>
            <Button variant="outline" size="sm" onClick={() => window.open(detailQuery.data.article.source_url, '_blank', 'noopener,noreferrer')}>
              <ExternalLink className="mr-2 h-4 w-4" />
              打开原文
            </Button>
          </div>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">发布时间：{formatTimestamp(detailQuery.data.article.published_at)}</div>
          <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">抓取时间：{formatTimestamp(detailQuery.data.article.crawled_at)}</div>
          <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">Prompt：{detailQuery.data.prompt_trace.prompt_version ?? '未记录'}</div>
          <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">Schema：{detailQuery.data.prompt_trace.schema_version ?? '未记录'}</div>
        </div>
        {detailQuery.data.message ? (
          <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">{detailQuery.data.message}</div>
        ) : null}
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <div className="rounded-[24px] border border-slate-200 bg-white p-5">
          <p className="text-base font-semibold tracking-tight text-slate-950">文章内容</p>
          <div className="mt-4 space-y-4">
            <div>
              <p className="text-xs font-medium text-slate-900">原始原文</p>
              <p className="mt-2 whitespace-pre-wrap rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs leading-6 text-slate-700">{detailQuery.data.article.original_text}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-slate-900">清洗后内容</p>
              <p className="mt-2 whitespace-pre-wrap rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs leading-6 text-slate-700">{detailQuery.data.article.cleaned_content}</p>
            </div>
          </div>
        </div>

        <div className="rounded-[24px] border border-slate-200 bg-white p-5">
          <p className="text-base font-semibold tracking-tight text-slate-950">结构化摘要</p>
          <div className="mt-4 space-y-4 text-xs leading-6 text-slate-700">
            <div>
              <p className="font-medium text-slate-900">摘要</p>
              <p className="mt-2">{detailQuery.data.article.summary ?? '未提供摘要'}</p>
            </div>
            <div>
              <p className="font-medium text-slate-900">方法标签</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {detailQuery.data.method_tags.length > 0 ? detailQuery.data.method_tags.map((tag) => <Badge key={tag} variant="info">{tag}</Badge>) : <Badge variant="default">未提供</Badge>}
              </div>
            </div>
            <div>
              <p className="font-medium text-slate-900">显式事实</p>
              <pre className="mt-2 overflow-x-auto rounded-xl border border-slate-200 bg-slate-50 p-3">{formatJsonBlock(detailQuery.data.explicit_facts)}</pre>
            </div>
            <div>
              <p className="font-medium text-slate-900">LLM 假设</p>
              <pre className="mt-2 overflow-x-auto rounded-xl border border-slate-200 bg-slate-50 p-3">{formatJsonBlock(detailQuery.data.hypotheses)}</pre>
            </div>
            <div>
              <p className="font-medium text-slate-900">缺失或未知信息</p>
              <pre className="mt-2 overflow-x-auto rounded-xl border border-slate-200 bg-slate-50 p-3">{formatJsonBlock(detailQuery.data.missing_fields)}</pre>
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-[24px] border border-slate-200 bg-white p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-base font-semibold tracking-tight text-slate-950">运行 Trace</p>
            <p className="mt-1 text-xs text-slate-600">展示 Prompt、Schema、模型和运行痕迹。</p>
          </div>
          <Button size="sm" onClick={() => selectedArticle && runAnalysisMutation.mutate(selectedArticle.id)} disabled={!selectedArticle || runAnalysisMutation.isPending}>
            {runAnalysisMutation.isPending ? '分析中' : '开始分析'}
          </Button>
        </div>
        <div className="mt-4 grid gap-3 text-xs text-slate-700 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">Prompt：{detailQuery.data.prompt_trace.prompt_name ?? '未记录'}</div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">Schema：{detailQuery.data.prompt_trace.schema_name ?? '未记录'}</div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">模型：{detailQuery.data.prompt_trace.model ?? '未记录'}</div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">校验状态：{detailQuery.data.prompt_trace.validation_state ?? '未记录'}</div>
        </div>
      </div>

      <div className="rounded-[24px] border border-slate-200 bg-slate-50 p-5">
        <p className="text-base font-semibold tracking-tight text-slate-950">候选规则与审核</p>
        <p className="mt-1 text-xs text-slate-600">自动审核只给出待回测、人工确认或建议拒绝，不会直接创建正式规则。</p>
        <div className="mt-4 space-y-4">
          {detailQuery.data.candidates.length === 0 ? (
            <EmptyState title="暂无候选规则" description="当前分析结果还没有提取到可展示的候选规则。" />
          ) : (
            detailQuery.data.candidates.map((candidate) => (
              <div key={candidate.candidate_id} className="rounded-2xl border border-slate-200 bg-white p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-slate-950">{candidate.title}</p>
                    <p className="mt-1 text-xs text-slate-600">规则类型：{candidate.rule_type}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Badge variant={automaticReviewVariant(candidate.automatic_review.status)}>{automaticReviewLabel(candidate.automatic_review.status)}</Badge>
                    <Badge variant={candidate.human_review.formal_rule_created ? 'success' : 'default'}>
                      {candidate.human_review.formal_rule_created ? '已创建待回测规则' : '未创建正式规则'}
                    </Badge>
                  </div>
                </div>
                <div className="mt-3 grid gap-3 text-[11px] text-slate-600 md:grid-cols-2 xl:grid-cols-4">
                  <span>回测状态：{candidate.backtestability_status}</span>
                  <span>Kaipan 依赖：{candidate.kaipan_dependency ? '是' : '否'}</span>
                  <span>市场状态声明：{candidate.market_state_declaration_status}</span>
                  <span>人工审核状态：{candidate.human_review.review_state}</span>
                </div>
                <div className="mt-4 grid gap-4 xl:grid-cols-2">
                  <div>
                    <p className="text-xs font-medium text-slate-900">自动审核原因</p>
                    <ul className="mt-2 list-disc space-y-1 pl-5 text-xs leading-6 text-slate-700">
                      {candidate.automatic_review.reasons.map((reason) => <li key={reason}>{reason}</li>)}
                    </ul>
                    <div className="mt-3 flex flex-wrap gap-3">
                      <Button
                        size="sm"
                        onClick={() => selectedArticle && reviewMutation.mutate({ articleId: selectedArticle.id, candidateId: candidate.candidate_id, decision: 'approve' })}
                        disabled={reviewMutation.isPending || candidate.human_review.formal_rule_created}
                      >
                        {candidate.human_review.formal_rule_created ? '已进入待回测' : '人工批准为待回测规则'}
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => selectedArticle && reviewMutation.mutate({ articleId: selectedArticle.id, candidateId: candidate.candidate_id, decision: 'reject' })}
                        disabled={reviewMutation.isPending}
                      >
                        驳回候选规则
                      </Button>
                    </div>
                  </div>
                  <div className="space-y-3">
                    <div>
                      <p className="text-xs font-medium text-slate-900">显式事实</p>
                      <pre className="mt-2 overflow-x-auto rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs">{formatJsonBlock(candidate.explicit_facts)}</pre>
                    </div>
                    <div>
                      <p className="text-xs font-medium text-slate-900">LLM 假设</p>
                      <pre className="mt-2 overflow-x-auto rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs">{formatJsonBlock(candidate.hypotheses)}</pre>
                    </div>
                  </div>
                </div>
                <div className="mt-4 grid gap-4 xl:grid-cols-3">
                  <div>
                    <p className="text-xs font-medium text-slate-900">原文证据</p>
                    <pre className="mt-2 overflow-x-auto rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs">{formatJsonBlock(candidate.evidence)}</pre>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-slate-900">数据依赖</p>
                    <pre className="mt-2 overflow-x-auto rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs">{formatJsonBlock(candidate.data_dependencies)}</pre>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-slate-900">缺失项</p>
                    <pre className="mt-2 overflow-x-auto rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs">{formatJsonBlock(candidate.missing_fields)}</pre>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );

  const content = (
    <div className="space-y-6">
      {message ? <div className="rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-800">{message}</div> : null}
      <SectionCard title="单篇文章分析与审核" description="左侧选择文章，右侧查看结构化分析、自动审核和人工审核动作。">
        <div className="grid items-start gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
          <div className="overflow-hidden rounded-[28px] border border-slate-200 bg-slate-50/80 shadow-sm">
            <div className="border-b border-slate-200 bg-white/80 p-4 backdrop-blur">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-base font-semibold tracking-tight text-slate-950">文章列表</p>
                  <p className="mt-1 text-xs text-slate-600">选择一篇文章后，右侧展示单篇分析和候选规则审核。</p>
                </div>
                <Badge variant="info">{totalCount} 篇</Badge>
              </div>
            </div>
            <div className={scrollHeightClass + ' p-4'}>
              {articlesQuery.isLoading ? (
                <LoadingState label="正在加载文章列表" description="正在读取当前页文章。" />
              ) : articlesQuery.error ? (
                <ArticleErrorState error={articlesQuery.error} title="文章列表加载失败" onRetry={() => void articlesQuery.refetch()} />
              ) : articles.length === 0 ? (
                <EmptyState title="暂无文章" description="当前还没有可分析的文章。" actionLabel="返回工作台" onAction={() => navigate('/articles')} />
              ) : (
                <div className="space-y-3">
                  {articles.map((article) => {
                    const active = article.id === selectedArticle?.id;
                    return (
                      <button
                        key={article.id}
                        type="button"
                        onClick={() => setSelectedArticleId(article.id)}
                        className={`w-full rounded-2xl border p-4 text-left transition ${
                          active
                            ? 'border-sky-400 bg-white shadow-md ring-2 ring-sky-200'
                            : 'border-slate-200 bg-white hover:border-sky-200 hover:shadow-sm'
                        }`}
                      >
                        <p className="text-sm font-medium text-slate-950">{article.title}</p>
                        <p className="mt-1 text-xs text-slate-600">{article.author_name ?? article.author_id ?? '未记录'} · {article.source}</p>
                        <p className="mt-2 line-clamp-2 text-xs leading-5 text-slate-700">{article.summary ?? '暂无摘要'}</p>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {article.tags.slice(0, 3).map((tag) => <Badge key={tag} variant="info">{tag}</Badge>)}
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
            <div className="flex items-center justify-between border-t border-slate-200 bg-white/80 px-4 py-3 text-sm text-slate-600">
              <span>第 {page} / {totalPages || 1} 页</span>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" onClick={() => setPage((current) => Math.max(1, current - 1))} disabled={page <= 1}>上一页</Button>
                <Button variant="outline" size="sm" onClick={() => setPage((current) => current + 1)} disabled={!(totalPages > 0 && page < totalPages)}>下一页</Button>
              </div>
            </div>
          </div>
          <div className="overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-200 bg-gradient-to-r from-slate-50 to-white p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-base font-semibold tracking-tight text-slate-950">当前文章详情</p>
                  <p className="mt-1 text-xs text-slate-600">显示原文、清洗结果、结构化事实、候选规则和人工审核边界。</p>
                </div>
                <Badge variant={availability === 'ready' ? 'success' : availability === 'partial' ? 'warning' : 'default'}>
                  {availability === 'ready' ? '可审核' : availability === 'partial' ? '部分完成' : '等待处理'}
                </Badge>
              </div>
            </div>
            <div className={scrollHeightClass + ' p-5'}>{detailPanel}</div>
          </div>
        </div>
      </SectionCard>
    </div>
  );

  if (productMode) {
    const recoveryAction =
      availability === 'permission_denied'
        ? { label: '返回研究首页', to: navigationTargets?.back ?? '/research' }
        : availability === 'unavailable' || availability === 'error' || availability === 'partial'
          ? { label: '重新加载', to: navigationTargets?.results ?? '/research/results' }
          : undefined;
    return (
      <ProductPageAdapter
        title="文章分析与审核"
        queryState={availability}
        purpose="查看单篇文章的结构化分析结果，并只在人工确认后创建待回测规则。"
        inputDescription="从左侧文章列表选择当前文章。"
        processingDescription="系统会读取对应内容版本的 PromptRun、ArticleStructure 和 RuleCandidate。"
        outputDescription="返回原文、清洗内容、显式事实、LLM 假设、候选规则、证据和审核状态。"
        businessAction={{ label: '返回文章库', to: navigationTargets?.library ?? '/research/articles' }}
        recoveryAction={recoveryAction}
        stateTitle={availability === 'partial' ? '部分完成' : undefined}
        stateDescription={availability === 'partial' ? '文章存在，但当前结构化分析尚未完全就绪。' : undefined}
        input={<span>从左侧列表选择文章后，右侧会显示当前分析结果。</span>}
        progress={<span>自动审核只给出待回测或人工确认建议，不会直接生成正式可用规则。</span>}
        output={content}
        help="人工批准后只会创建待回测边界内的规则版本，不会直接进入策略使用。"
      />
    );
  }

  if (articlesQuery.isLoading) {
    return (
      <ArticlePageShell title="文章分析与审核" description="查看单篇文章的结构化分析结果并完成人工审核。" summary="以文章为中心查看分析结果、候选规则和人工审核状态。">
        <LoadingState label="正在加载文章分析" description="正在读取文章列表和当前分析状态。" />
      </ArticlePageShell>
    );
  }

  if (articlesQuery.error) {
    return (
      <ArticlePageShell title="文章分析与审核" description="查看单篇文章的结构化分析结果并完成人工审核。" summary="以文章为中心查看分析结果、候选规则和人工审核状态。">
        <ArticleErrorState error={articlesQuery.error} title="文章分析加载失败" onRetry={() => void articlesQuery.refetch()} />
      </ArticlePageShell>
    );
  }

  return (
    <ArticlePageShell title="文章分析与审核" description="查看单篇文章的结构化分析结果并完成人工审核。" summary="以文章为中心查看分析结果、候选规则和人工审核状态。">
      {content}
    </ArticlePageShell>
  );
}
