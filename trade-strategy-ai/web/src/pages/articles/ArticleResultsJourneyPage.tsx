import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ExternalLink } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { BusinessPageShell } from '@/components/layout/business-page-shell';
import { PageHeader } from '@/components/layout/page-header';
import { LoadingState, EmptyState, ErrorState, SectionCard } from '@/components/kit';
import { ApiError } from '@/lib/api/http';
import { listArticles } from '@/lib/api/articles';
import { getArticleAnalysis, reviewExtractionItem, runArticleAnalysis, updateArticleProcessingStatus } from '@/lib/api/article-analysis';
import type { ArticleAnalysisDetail, ArticleExtractionItem, PrimaryExtractionType } from '@/types/article-analysis';
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

const typeLabels: Record<PrimaryExtractionType, string> = {
  executable_rule: '可执行规则',
  rule_candidate: '待修复规则雏形',
  research_hypothesis: '研究假设',
  semantic_experience: '语义经验',
  risk_control_hint: '风控提示',
  data_requirement_hint: '数据需求',
  unusable_noise: '不可用内容',
};

function itemVariant(item: ArticleExtractionItem) {
  if (item.quality_state === 'invalid' || item.quality_state === 'rejected') return 'destructive' as const;
  if (item.primary_type === 'executable_rule' && item.backtest_eligibility.eligible) return 'success' as const;
  if (item.quality_state === 'partial' || item.quality_state === 'needs_review') return 'warning' as const;
  return 'info' as const;
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
  const [processingStatus, setProcessingStatus] = useState<'all' | 'processed' | 'unprocessed' | 'failed' | 'manual_review_required' | 'ignored'>('all');
  const [selectedArticleId, setSelectedArticleId] = useState<string | null>(null);
  const pageSize = 8;
  const scrollHeightClass = 'h-[calc(100vh-330px)] overflow-y-auto';

  const articlesQuery = useQuery<ArticleListResponse, ApiError>({
    queryKey: ['articles', 'analysis-results', page, processingStatus],
    queryFn: () => listArticles({ page, page_size: pageSize, processing_status: processingStatus }),
    staleTime: 20_000,
  });

  const articles = articlesQuery.data?.items ?? [];
  const totalCount = articlesQuery.data?.total ?? 0;
  const totalPages = articlesQuery.data?.pages ?? 0;
  const selectedArticle = useMemo(() => {
    if (!selectedArticleId) return articles[0] ?? null;
    return articles.find((item) => item.id === selectedArticleId) ?? articles[0] ?? null;
  }, [articles, selectedArticleId]);
  const selectedArticleProcessingStatus = selectedArticle?.processing_status ?? 'unprocessed';
  const selectedArticleNeedsManualPanel = selectedArticleProcessingStatus === 'failed'
    || selectedArticleProcessingStatus === 'manual_review_required'
    || selectedArticleProcessingStatus === 'ignored';

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
    enabled: Boolean(selectedArticle?.id) && !selectedArticleNeedsManualPanel,
    staleTime: 20_000,
  });

  const runAnalysisMutation = useMutation({
    mutationFn: async (articleId: string) => runArticleAnalysis(articleId),
    onSuccess: async (detail) => {
      setMessage('文章分析已更新。');
      queryClient.setQueryData(['article-analysis', detail.article.article_id], detail);
      await queryClient.invalidateQueries({ queryKey: ['article-analysis', detail.article.article_id] });
      await queryClient.invalidateQueries({ queryKey: ['articles', 'analysis-results'] });
    },
    onError: (error: unknown) => setMessage(getErrorMessage(error)),
  });

  const reviewMutation = useMutation({
    mutationFn: async (payload: { articleId: string; itemId: string; decision: 'accept' | 'reject' }) =>
      reviewExtractionItem(payload.articleId, payload.itemId, {
        decision: payload.decision,
        reason: payload.decision === 'accept' ? '已按当前分类通道确认。' : '证据或分类不满足保留要求。',
      }),
    onSuccess: async (detail) => {
      setMessage('人工审核结果已保存。');
      queryClient.setQueryData(['article-analysis', detail.article.article_id], detail);
      await queryClient.invalidateQueries({ queryKey: ['article-analysis', detail.article.article_id] });
    },
    onError: (error: unknown) => setMessage(getErrorMessage(error)),
  });

  const updateProcessingStatusMutation = useMutation({
    mutationFn: async (payload: { articleId: string; action: 'ignored' | 'manual_review_required'; note: string }) =>
      updateArticleProcessingStatus(payload.articleId, { action: payload.action, note: payload.note }),
    onSuccess: async () => {
      setMessage('文章状态已更新。');
      await queryClient.invalidateQueries({ queryKey: ['articles', 'analysis-results'] });
    },
    onError: (error: unknown) => setMessage(getErrorMessage(error)),
  });

  const availability = resolveAvailability({
    loading: articlesQuery.isLoading || (Boolean(selectedArticle?.id) && !selectedArticleNeedsManualPanel && detailQuery.isLoading && !detailQuery.data),
    error: articlesQuery.error ?? detailQuery.error ?? null,
    empty: !articlesQuery.isLoading && !articlesQuery.error && articles.length === 0,
    partial: detailQuery.data?.status === 'partial',
  });

  const manualStatusLabel =
    selectedArticleProcessingStatus === 'ignored'
      ? '已忽略'
      : selectedArticleProcessingStatus === 'manual_review_required'
        ? '待人工补录'
        : '提取失败';

  const detailPanel = !selectedArticle ? (
    <EmptyState title="请选择一篇文章" description="从左侧列表选择文章后，右侧会展示分析结果和审核动作。" />
  ) : selectedArticleNeedsManualPanel ? (
    <div className="space-y-6">
      <div className="rounded-[24px] border border-rose-200 bg-rose-50 p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-lg font-semibold tracking-tight text-slate-950">{selectedArticle.title}</p>
            <p className="mt-1 text-xs text-slate-600">
              {selectedArticle.author_name ?? selectedArticle.author_id ?? '未记录'} · {selectedArticle.source}
            </p>
            <p className="mt-1 break-all text-[11px] text-slate-500">{selectedArticle.source_url}</p>
          </div>
          <Badge variant={selectedArticleProcessingStatus === 'ignored' ? 'default' : selectedArticleProcessingStatus === 'manual_review_required' ? 'warning' : 'destructive'}>
            {manualStatusLabel}
          </Badge>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-2xl border border-rose-200 bg-white p-4 text-sm text-slate-700">失败类型：{selectedArticle.failure_type ?? '未记录'}</div>
          <div className="rounded-2xl border border-rose-200 bg-white p-4 text-sm text-slate-700">失败时间：{selectedArticle.failed_at ? formatTimestamp(selectedArticle.failed_at) : '未记录'}</div>
          <div className="rounded-2xl border border-rose-200 bg-white p-4 text-sm text-slate-700">失败次数：{selectedArticle.failed_retry_count ?? 0}</div>
          <div className="rounded-2xl border border-rose-200 bg-white p-4 text-sm text-slate-700">当前状态：{manualStatusLabel}</div>
        </div>
        <div className="mt-4 rounded-xl border border-rose-200 bg-white px-4 py-3 text-sm text-rose-900">
          {selectedArticle.processing_note ?? selectedArticle.failure_message ?? '当前文章提取失败，请重试或稍后人工复核。'}
        </div>
      </div>

      <div className="rounded-[24px] border border-slate-200 bg-white p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-base font-semibold tracking-tight text-slate-950">人工处理</p>
            <p className="mt-1 text-xs text-slate-600">这篇文章没有进入正式结构化结果。可以重新分析，或将其标记为忽略、待人工补录。</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" onClick={() => selectedArticle && runAnalysisMutation.mutate(selectedArticle.id)} disabled={!selectedArticle || runAnalysisMutation.isPending}>
              {runAnalysisMutation.isPending ? '重试中' : '重新分析此文章'}
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() =>
                selectedArticle &&
                updateProcessingStatusMutation.mutate({
                  articleId: selectedArticle.id,
                  action: 'manual_review_required',
                  note: '需要人工补录',
                })
              }
              disabled={!selectedArticle || updateProcessingStatusMutation.isPending}
            >
              标记需人工补录
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() =>
                selectedArticle &&
                updateProcessingStatusMutation.mutate({
                  articleId: selectedArticle.id,
                  action: 'ignored',
                  note: '非目标文章，人工忽略',
                })
              }
              disabled={!selectedArticle || updateProcessingStatusMutation.isPending}
            >
              标记忽略
            </Button>
          </div>
        </div>
        <div className="mt-4 grid gap-3 text-xs text-slate-600 md:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">处理人：{selectedArticle.processing_updated_by ?? '未记录'}</div>
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">处理时间：{selectedArticle.processing_updated_at ? formatTimestamp(selectedArticle.processing_updated_at) : '未记录'}</div>
        </div>
      </div>
    </div>
  ) : detailQuery.isLoading ? (
    <LoadingState label="正在加载文章分析" description="正在读取当前文章的结构化结果、分类抽取项和处理状态。" />
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
        <p className="text-base font-semibold tracking-tight text-slate-950">分类抽取结果</p>
        <p className="mt-1 text-xs text-slate-600">结果按真实含义进入各自处理通道；只有通过严格校验的可执行规则才能进入规则治理和正式回测。</p>
        <div className="mt-4 flex flex-wrap gap-2">
          {(Object.entries(detailQuery.data.extraction_summary.by_primary_type) as Array<[PrimaryExtractionType, number]>).map(([type, count]) => (
            <Badge key={type} variant="info">{typeLabels[type]} {count}</Badge>
          ))}
        </div>
        <div className="mt-4 space-y-4">
          {detailQuery.data.extraction_items.length === 0 ? (
            <EmptyState title="暂无分类抽取项" description="当前文章没有可保留的交易语义、规则、假设或提示。" />
          ) : detailQuery.data.extraction_items.map((item) => (
            <div key={item.item_id} className="rounded-2xl border border-slate-200 bg-white p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-slate-950">{item.display_title}</p>
                  <p className="mt-1 text-xs leading-5 text-slate-600">{item.display_summary}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge variant={itemVariant(item)}>{typeLabels[item.primary_type]}</Badge>
                  <Badge variant={item.quality_state === 'valid' ? 'success' : 'warning'}>{item.quality_state}</Badge>
                  <Badge variant="default">{item.review_state}</Badge>
                </div>
              </div>
              <div className="mt-3 grid gap-3 text-[11px] text-slate-600 md:grid-cols-3">
                <span>处理通道：{item.review_destination}</span>
                <span>正式回测：{item.backtest_eligibility.eligible ? '可进入下一步' : '不可进入'}</span>
                <span>正式规则：{item.rule_version_id ? '已建立追溯' : '未创建'}</span>
              </div>
              {!item.backtest_eligibility.eligible ? (
                <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
                  {item.backtest_eligibility.reason}；下一步：{item.backtest_eligibility.required_next_step}
                </div>
              ) : null}
              <div className="mt-4 grid gap-4 xl:grid-cols-2">
                <div>
                  <p className="text-xs font-medium text-slate-900">原文证据</p>
                  <pre className="mt-2 overflow-x-auto rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs">{formatJsonBlock(item.source_evidence)}</pre>
                </div>
                <div>
                  <p className="text-xs font-medium text-slate-900">分类内容</p>
                  <pre className="mt-2 overflow-x-auto rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs">{formatJsonBlock(item.taxonomy_payload)}</pre>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap gap-3">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => selectedArticle && reviewMutation.mutate({ articleId: selectedArticle.id, itemId: item.item_id, decision: 'accept' })}
                  disabled={reviewMutation.isPending || item.review_state === 'accepted' || item.review_state === 'promoted'}
                >
                  按当前通道确认
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => selectedArticle && reviewMutation.mutate({ articleId: selectedArticle.id, itemId: item.item_id, decision: 'reject' })}
                  disabled={reviewMutation.isPending || item.review_state === 'rejected'}
                >
                  拒绝此项
                </Button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const content = (
    <div className="space-y-6">
      {message ? <div className="rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-800">{message}</div> : null}
      <SectionCard title="文章分析与审核" description="左侧选择文章，右侧查看结构化分析、自动审核和人工审核动作。">
        <div className="grid items-start gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
          <div className="overflow-hidden rounded-[28px] border border-slate-200 bg-slate-50/80 shadow-sm">
            <div className="border-b border-slate-200 bg-white/80 p-4 backdrop-blur">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-base font-semibold tracking-tight text-slate-950">文章列表</p>
                  <p className="mt-1 text-xs text-slate-600">选择一篇文章后，右侧展示单篇分析和分类抽取结果。</p>
                </div>
                <Badge variant="info" className="shrink-0 whitespace-nowrap self-start">{totalCount} 篇</Badge>
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-3">
                <span className="text-xs text-slate-500">筛选</span>
                <Tabs value={processingStatus} onValueChange={(value) => {
                  if (
                    value === 'all'
                    || value === 'processed'
                    || value === 'unprocessed'
                    || value === 'failed'
                    || value === 'manual_review_required'
                    || value === 'ignored'
                  ) {
                    setProcessingStatus(value);
                    setPage(1);
                  }
                }}>
                  <TabsList>
                    <TabsTrigger value="all">全部</TabsTrigger>
                    <TabsTrigger value="processed">已处理</TabsTrigger>
                    <TabsTrigger value="unprocessed">未处理</TabsTrigger>
                    <TabsTrigger value="failed">提取失败</TabsTrigger>
                    <TabsTrigger value="manual_review_required">待人工补录</TabsTrigger>
                    <TabsTrigger value="ignored">已忽略</TabsTrigger>
                  </TabsList>
                </Tabs>
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
                    const failed = article.processing_status === 'failed';
                    const manualReviewRequired = article.processing_status === 'manual_review_required';
                    const ignored = article.processing_status === 'ignored';
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
                          {failed ? <Badge variant="destructive">提取失败</Badge> : null}
                          {manualReviewRequired ? <Badge variant="warning">待人工补录</Badge> : null}
                          {ignored ? <Badge variant="default">已忽略</Badge> : null}
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
                  <p className="mt-1 text-xs text-slate-600">显示原文、清洗结果、结构化事实、分类抽取项和处理边界。</p>
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
      <BusinessPageShell
        title="文章分析与审核"
        purpose="查看单篇文章的混合分类抽取结果，并按类型进入正确处理通道。"
        inputDescription="从左侧文章列表选择当前文章。"
        processingDescription="系统会读取对应内容版本及其分类抽取结果。"
        outputDescription="返回原文、清洗内容、显式事实、混合分类结果、证据和处理状态。"
        availability={availability}
        showPurposeSection={false}
        nextAction={{ label: '返回文章库', to: navigationTargets?.library ?? '/research/articles' }}
        recoveryAction={recoveryAction}
        stateTitle={availability === 'partial' ? '部分完成' : undefined}
        stateDescription={availability === 'partial' ? '文章存在，但当前结构化分析尚未完全就绪。' : undefined}
        showInputSection={false}
        showProcessingSection={false}
        showOutputSection={false}
        help="人工批准后只会创建待回测边界内的规则版本，不会直接进入策略使用。"
      >
        {content}
      </BusinessPageShell>
    );
  }

  if (articlesQuery.isLoading) {
    return (
      <ArticlePageShell title="文章分析与审核" description="查看单篇文章的结构化分析与分类结果。" summary="以文章为中心查看抽取类型、原文证据和处理状态。">
        <LoadingState label="正在加载文章分析" description="正在读取文章列表和当前分析状态。" />
      </ArticlePageShell>
    );
  }

  if (articlesQuery.error) {
    return (
      <ArticlePageShell title="文章分析与审核" description="查看单篇文章的结构化分析与分类结果。" summary="以文章为中心查看抽取类型、原文证据和处理状态。">
        <ArticleErrorState error={articlesQuery.error} title="文章分析加载失败" onRetry={() => void articlesQuery.refetch()} />
      </ArticlePageShell>
    );
  }

  return (
    <ArticlePageShell title="文章分析与审核" description="查看单篇文章的结构化分析与分类结果。" summary="以文章为中心查看抽取类型、原文证据和处理状态。">
      {content}
    </ArticlePageShell>
  );
}
