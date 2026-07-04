import { useMutation, useQuery } from '@tanstack/react-query';
import { ArrowLeft, ArrowRight, Download } from 'lucide-react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArtifactPreview } from '@/components/artifacts/artifact-preview';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { JsonViewer, LoadingState, EmptyState, ErrorState, PageHeader } from '@/components/kit';
import { ApiError } from '@/lib/api/http';
import { buildErrorRecoveryState } from '@/lib/error-recovery';
import { downloadArtifact, getArtifact } from '@/lib/api/artifacts';

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return '产物详情加载失败';
}

function formatBytes(bytes: number | null | undefined) {
  if (bytes == null) return '未知大小';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatTimestamp(value: string | null) {
  if (!value) return '未记录';
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function SummaryTile({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-1 break-all text-sm font-semibold text-slate-950">{value ?? 'n/a'}</p>
    </div>
  );
}

export function ArtifactDetailPage() {
  const params = useParams<{ artifactId?: string }>();
  const navigate = useNavigate();
  const artifactId = params.artifactId?.trim() || '';

  const detailQuery = useQuery({
    queryKey: ['artifact-detail', artifactId],
    queryFn: () => getArtifact(artifactId),
    enabled: Boolean(artifactId),
  });

  const detail = detailQuery.data ?? null;

  const downloadMutation = useMutation({
    mutationFn: async () => {
      if (!detail) {
        throw new Error('No artifact selected');
      }
      const blob = await downloadArtifact(artifactId);
      if (typeof window.URL.createObjectURL !== 'function') {
        return;
      }
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = detail.download_name || detail.name || 'artifact';
      a.click();
      window.URL.revokeObjectURL(url);
    },
  });

  if (!artifactId) {
    return (
      <main className="page-stack">
        <EmptyState
          title="未找到产物"
          description="缺少 artifactId，无法打开产物详情。"
          actionLabel="返回列表"
          onAction={() => navigate('/artifacts')}
        />
      </main>
    );
  }

  if (detailQuery.isLoading) {
    return (
      <main className="page-stack">
        <PageHeader
          kicker="正式工作台"
          title="产物详情"
          description="正在加载产物预览、元数据、来源 Job 和下载信息。"
        />
        <LoadingState label="正在加载产物详情" description="稍后会显示预览、元数据、来源 Job 和下载信息。" />
      </main>
    );
  }

  if (detailQuery.error) {
    return (
      <main className="page-stack">
        <PageHeader
          kicker="正式工作台"
          title="产物详情"
          description="正在加载产物预览、元数据、来源 Job 和下载信息。"
        />
        <ErrorState
          {...buildErrorRecoveryState(detailQuery.error, 'artifact-detail')}
          detail={getErrorMessage(detailQuery.error)}
          onRetry={() => void detailQuery.refetch()}
        />
      </main>
    );
  }

  if (!detail) {
    return (
      <main className="page-stack">
        <PageHeader
          kicker="正式工作台"
          title="产物详情"
          description="正在加载产物预览、元数据、来源 Job 和下载信息。"
        />
        <EmptyState title="暂无产物详情。" description="请选择一个有效的产物再查看详情。" />
      </main>
    );
  }

  return (
    <main className="page-stack">
      <PageHeader
        kicker="正式工作台"
        title={detail.title || detail.name}
        description="查看产物预览、元数据、来源 Job 和安全下载入口。"
      />

      <section className="flex flex-wrap items-center justify-between gap-3">
        <Link
          className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
          to="/artifacts"
        >
          <ArrowLeft className="h-4 w-4" />
          返回列表
        </Link>
        <div className="flex flex-wrap items-center gap-2">
          {detail.job_id ? (
            <Link
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
              to={`/system/jobs/${detail.job_id}`}
            >
              查看来源 Job
              <ArrowRight className="h-4 w-4" />
            </Link>
          ) : null}
          <Button onClick={() => downloadMutation.mutate()} disabled={downloadMutation.isPending}>
            <Download className="h-4 w-4" />
            {downloadMutation.isPending ? '下载中' : '下载产物'}
          </Button>
        </div>
      </section>

      {downloadMutation.error ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          {getErrorMessage(downloadMutation.error)}
        </div>
      ) : null}

      <Card className="border-slate-200 bg-white shadow-sm">
        <CardHeader>
          <CardTitle className="text-slate-900">总览信息</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 lg:grid-cols-2 xl:grid-cols-4">
            <SummaryTile label="名称" value={detail.title || detail.name} />
            <SummaryTile label="kind" value={detail.kind} />
            <SummaryTile label="来源" value={detail.source} />
            <SummaryTile label="来源 Job" value={detail.job_id ?? '无'} />
          </div>
          <div className="mt-3 grid gap-3 lg:grid-cols-2 xl:grid-cols-4">
            <SummaryTile label="job type" value={detail.job_type ?? '未知'} />
            <SummaryTile label="修改时间" value={formatTimestamp(detail.modified_at)} />
            <SummaryTile label="大小" value={formatBytes(detail.size_bytes)} />
            <SummaryTile
              label="存储引用"
              value={detail.storage_ref?.relative_path ?? detail.storage_ref?.logical_id ?? '未提供'}
            />
          </div>
        </CardContent>
      </Card>

      <Card className="border-slate-200 bg-white shadow-sm">
        <CardHeader>
          <CardTitle className="text-slate-900">元数据</CardTitle>
        </CardHeader>
        <CardContent>
          <JsonViewer value={detail.metadata} title="artifact metadata" />
        </CardContent>
      </Card>

      <Card className="border-slate-200 bg-white shadow-sm">
        <CardHeader>
          <CardTitle className="text-slate-900">预览</CardTitle>
        </CardHeader>
        <CardContent>
          {detail.previewable ? (
            <ArtifactPreview kind={detail.kind} content={detail.preview ?? ''} />
          ) : (
            <EmptyState title="暂无可预览内容。" description="该产物当前没有可直接预览的文本内容。" />
          )}
        </CardContent>
      </Card>
    </main>
  );
}
