import { useQuery } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowRight, RefreshCw } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { useAuth } from '@/features/auth/auth-context';
import { ApiError } from '@/lib/api/http';
import { getProfileSnapshot } from '@/lib/api/profiles';
import type { ProfileSnapshotResponse } from '@/types/profile';

function formatTimestamp(value: string | null | undefined) {
  if (!value) return '未记录';
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return '配置快照加载失败';
}

function MetaCard({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 shadow-sm">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 break-all text-sm text-slate-900">{value ?? '未记录'}</p>
    </div>
  );
}

export function ProfileSnapshotPage() {
  const params = useParams<{ profileId?: string; snapshotId?: string }>();
  const navigate = useNavigate();
  const { canAccess, principal } = useAuth();
  const profileId = params.profileId?.trim() || '';
  const snapshotId = params.snapshotId?.trim() || '';

  const canViewProfiles = canAccess('viewer');

  const snapshotQuery = useQuery<ProfileSnapshotResponse, ApiError>({
    queryKey: ['profile-snapshot', profileId, snapshotId],
    queryFn: () => getProfileSnapshot(profileId, snapshotId),
    enabled: Boolean(profileId) && Boolean(snapshotId) && canViewProfiles,
    staleTime: 10_000,
  });

  const profile = snapshotQuery.data?.profile ?? null;
  const snapshot = snapshotQuery.data?.snapshot ?? null;

  if (!canViewProfiles) {
    return (
      <main className="page-stack">
        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-lg font-semibold text-slate-900">没有权限查看配置快照</p>
          <p className="mt-2 text-sm text-slate-600">当前身份为 {principal.role}，至少需要 viewer 权限。</p>
        </section>
      </main>
    );
  }

  const permissionDenied = snapshotQuery.error instanceof ApiError && (snapshotQuery.error.status === 401 || snapshotQuery.error.status === 403);
  const notFound = snapshotQuery.error instanceof ApiError && snapshotQuery.error.status === 404;

  return (
    <main className="page-stack">
      <section className="rounded-[28px] border border-slate-200 bg-white/90 p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-3xl">
            <Badge variant="info">配置快照</Badge>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">配置快照</h1>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              这是只读页面，用于查看历史 Job 对应的冻结配置和脱敏内容。
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50" variant="outline" onClick={() => snapshotQuery.refetch()} disabled={snapshotQuery.isFetching}>
              <RefreshCw className="mr-2 h-4 w-4" />
              {snapshotQuery.isFetching ? '刷新中' : '刷新'}
            </Button>
            <Button className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50" variant="outline" onClick={() => navigate(`/profiles/${encodeURIComponent(profileId)}`)}>
              返回详情
            </Button>
          </div>
        </div>
      </section>

      {snapshotQuery.isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-72 w-full" />
        </div>
      ) : snapshotQuery.error ? (
        <section
          className={`rounded-3xl border p-6 ${
            permissionDenied ? 'border-amber-200 bg-amber-50 text-amber-900' : 'border-rose-200 bg-rose-50 text-rose-800'
          }`}
        >
          <p className="font-medium">{notFound ? '快照不存在' : getErrorMessage(snapshotQuery.error)}</p>
          <p className="mt-2 text-sm text-slate-600">
            {notFound ? '请检查配置 ID 和快照 ID 是否正确。' : '请稍后重试或检查访问权限。'}
          </p>
        </section>
      ) : snapshot ? (
        <>
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <MetaCard label="配置 ID" value={profile?.profile_id ?? snapshot.profile_id} />
            <MetaCard label="快照 ID" value={snapshot.snapshot_id} />
            <MetaCard label="配置哈希" value={snapshot.config_hash} />
            <MetaCard label="校验状态" value={snapshot.validation_status} />
          </section>

          <section className="grid gap-4 md:grid-cols-3">
            <MetaCard label="来源" value={snapshot.source} />
            <MetaCard label="捕获时间" value={formatTimestamp(snapshot.captured_at)} />
            <MetaCard label="关联任务" value={snapshot.job_id ?? '无'} />
          </section>

          <section className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-xl font-semibold text-slate-950">脱敏分区</h2>
                <p className="mt-1 text-sm text-slate-600">只展示脱敏后的内容，不回写到配置。</p>
              </div>
              <Badge variant="info">{snapshot.masked_sections.length} 个分区</Badge>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {snapshot.masked_sections.length ? (
                snapshot.masked_sections.map((section) => (
                  <Badge key={section} variant="info">
                    {section}
                  </Badge>
                ))
              ) : (
                <span className="text-sm text-slate-500">暂无脱敏分区。</span>
              )}
            </div>
          </section>

          <section className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-xl font-semibold text-slate-950">脱敏快照内容</h2>
                <p className="mt-1 text-sm text-slate-600">用于复盘，不包含原始 secret。</p>
              </div>
              <Badge variant="warning">只读</Badge>
            </div>
            <pre className="mt-4 max-h-[32rem] overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-4 text-xs leading-6 text-slate-800 shadow-sm">
              {JSON.stringify(snapshot.masked_snapshot, null, 2)}
            </pre>
          </section>

          {snapshot.job_id ? (
            <Card className="border-slate-200 bg-white text-slate-900 shadow-sm">
              <CardHeader>
                <CardTitle className="text-slate-950">关联任务</CardTitle>
                <CardDescription className="text-slate-600">可以继续跳回任务详情查看上下文。</CardDescription>
              </CardHeader>
              <CardContent>
                <Button className="bg-sky-500 text-slate-950 hover:bg-sky-400" onClick={() => navigate(`/jobs/${encodeURIComponent(snapshot.job_id as string)}`)}>
                  查看关联任务 <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </CardContent>
            </Card>
          ) : null}
        </>
      ) : null}
    </main>
  );
}
