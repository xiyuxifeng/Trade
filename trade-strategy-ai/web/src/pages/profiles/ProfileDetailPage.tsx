import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowRight, PencilLine, RefreshCw } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { useAuth } from '@/features/auth/auth-context';
import { ApiError } from '@/lib/api/http';
import { getProfile } from '@/lib/api/profiles';
import type { ProfileDetailResponse, ProfileLinkedJob, ProfileSnapshotRecord } from '@/types/profile';
import { ProfileSectionsPanel } from '@/components/profiles/ProfileSectionsPanel';
import { ProfileStatusBadge } from '@/components/profiles/ProfileStatusBadge';

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
  return '配置详情加载失败';
}

function MetaCard({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 shadow-sm">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 break-all text-sm text-slate-900">{value ?? '未记录'}</p>
    </div>
  );
}

function LinkedJobCard({ job, onOpen }: { job: ProfileLinkedJob; onOpen: () => void }) {
  return (
    <button className="w-full text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400/40" onClick={onOpen} type="button">
      <Card className="border-slate-200 bg-white text-slate-900 shadow-sm transition-colors hover:border-sky-200 hover:bg-slate-50">
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle className="text-base text-slate-900">{job.job_id}</CardTitle>
              <CardDescription className="text-slate-600">任务类型：{job.job_type}</CardDescription>
            </div>
            <Badge variant={job.status === 'success' ? 'success' : job.status === 'failed' ? 'destructive' : 'info'}>
              {job.status}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="text-sm text-slate-600">
          <div className="flex items-center justify-between gap-3">
            <span>创建时间：{formatTimestamp(job.created_at)}</span>
            <span>更新时间：{formatTimestamp(job.updated_at)}</span>
          </div>
        </CardContent>
      </Card>
    </button>
  );
}

function SnapshotCard({
  snapshot,
  onOpen,
}: {
  snapshot: ProfileSnapshotRecord;
  onOpen: () => void;
}) {
  return (
    <button className="w-full text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400/40" onClick={onOpen} type="button">
      <Card className="border-slate-200 bg-white text-slate-900 shadow-sm transition-colors hover:border-sky-200 hover:bg-slate-50">
        <CardHeader>
          <div className="flex items-start justify-between gap-3">
            <div>
              <CardTitle className="text-base text-slate-900">{snapshot.snapshot_id}</CardTitle>
              <CardDescription className="text-slate-600">{snapshot.source}</CardDescription>
            </div>
            <ProfileStatusBadge status={snapshot.validation_status} />
          </div>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-slate-600">
          <p>配置哈希：{snapshot.config_hash}</p>
          <p>捕获时间：{formatTimestamp(snapshot.captured_at)}</p>
          <p>脱敏分区：{snapshot.masked_sections.length ? snapshot.masked_sections.join('、') : '无'}</p>
        </CardContent>
      </Card>
    </button>
  );
}

export function ProfileDetailPage() {
  const params = useParams<{ profileId?: string }>();
  const navigate = useNavigate();
  const { canAccess, principal } = useAuth();
  const profileId = params.profileId?.trim() || '';

  const canViewProfiles = canAccess('viewer');
  const canEditProfiles = canAccess('operator');

  const profileQuery = useQuery<ProfileDetailResponse, ApiError>({
    queryKey: ['profile-detail', profileId],
    queryFn: () => getProfile(profileId),
    enabled: Boolean(profileId) && canViewProfiles,
    staleTime: 10_000,
  });

  const profile = profileQuery.data?.profile ?? null;
  const linkedJobs = profileQuery.data?.linked_jobs ?? [];
  const snapshots = profileQuery.data?.snapshots ?? [];

  const summary = useMemo(() => {
    const maskedCount = Object.keys(profile?.secret_refs ?? {}).length;
    const sectionCount = Object.keys(profile?.sections ?? {}).length;
    return { maskedCount, sectionCount };
  }, [profile]);

  if (!canViewProfiles) {
    return (
      <main className="page-stack">
        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-lg font-semibold text-slate-900">没有权限查看配置详情</p>
          <p className="mt-2 text-sm text-slate-600">当前身份为 {principal.role}，至少需要 viewer 权限。</p>
        </section>
      </main>
    );
  }

  const permissionDenied = profileQuery.error instanceof ApiError && (profileQuery.error.status === 401 || profileQuery.error.status === 403);
  const notFound = profileQuery.error instanceof ApiError && profileQuery.error.status === 404;

  return (
    <main className="page-stack">
      <section className="rounded-[28px] border border-slate-200 bg-white/90 p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-3xl">
            <Badge variant="info">配置管理</Badge>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">
              {profile?.name ?? '配置详情'}
            </h1>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              查看基础信息、配置分区、脱敏字段、校验结果、关联任务和历史快照。
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50" variant="outline" onClick={() => profileQuery.refetch()} disabled={profileQuery.isFetching}>
              <RefreshCw className="mr-2 h-4 w-4" />
              {profileQuery.isFetching ? '刷新中' : '刷新'}
            </Button>
            {canEditProfiles && profile ? (
              <Button className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50" variant="outline" onClick={() => navigate(`/profiles/${encodeURIComponent(profile.profile_id)}/edit`)}>
                <PencilLine className="mr-2 h-4 w-4" />
                编辑配置
              </Button>
            ) : null}
            <Button className="bg-sky-500 text-slate-950 hover:bg-sky-400" onClick={() => navigate('/profiles')}>
              返回列表
            </Button>
          </div>
        </div>
      </section>

      {profileQuery.isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      ) : profileQuery.error ? (
        <section
          className={`rounded-3xl border p-6 ${
            permissionDenied ? 'border-amber-200 bg-amber-50 text-amber-900' : 'border-rose-200 bg-rose-50 text-rose-800'
          }`}
        >
          <p className="font-medium">{notFound ? '配置不存在' : getErrorMessage(profileQuery.error)}</p>
          <p className="mt-2 text-sm text-slate-600">
            {notFound ? '请检查配置 ID 是否正确。' : '请稍后重试或检查访问权限。'}
          </p>
        </section>
      ) : profile ? (
        <>
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <MetaCard label="配置 ID" value={profile.profile_id} />
            <MetaCard label="运行环境" value={profile.environment} />
            <MetaCard label="版本号" value={profile.version} />
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">校验状态</p>
              <div className="mt-2">
                <ProfileStatusBadge status={profile.validation_status} />
              </div>
            </div>
          </section>

          <section className="grid gap-4 md:grid-cols-3">
            <MetaCard label="最近更新" value={formatTimestamp(profile.updated_at)} />
            <MetaCard label="创建者" value={profile.created_by} />
            <MetaCard label="脱敏字段数" value={summary.maskedCount} />
          </section>

          <section className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-xl font-semibold text-slate-950">配置分区</h2>
                <p className="mt-1 text-sm text-slate-600">仅显示脱敏后的内容，用于复盘和问题定位。</p>
              </div>
              <Badge variant="info">{summary.sectionCount} 个分区</Badge>
            </div>
            <div className="mt-6">
              <ProfileSectionsPanel sections={profile.sections} />
            </div>
          </section>

          <section className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-xl font-semibold text-slate-950">脱敏字段</h2>
                <p className="mt-1 text-sm text-slate-600">这些字段不会展示原文，只用于审计和排查。</p>
              </div>
              <Badge variant="warning">{summary.maskedCount} 个字段</Badge>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {Object.keys(profile.secret_refs ?? {}).length ? (
                Object.keys(profile.secret_refs).map((field) => (
                  <Badge key={field} variant="info">
                    {field}
                  </Badge>
                ))
              ) : (
                <span className="text-sm text-slate-500">暂无脱敏字段。</span>
              )}
            </div>
          </section>

          <section className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-xl font-semibold text-slate-950">关联任务</h2>
                <p className="mt-1 text-sm text-slate-600">点击任务卡片进入任务详情继续复盘。</p>
              </div>
              <Badge variant="info">{linkedJobs.length} 条</Badge>
            </div>
            <div className="mt-6 grid gap-4 lg:grid-cols-2">
              {linkedJobs.length ? (
                linkedJobs.map((job) => (
                  <LinkedJobCard key={job.job_id} job={job} onOpen={() => navigate(`/jobs/${encodeURIComponent(job.job_id)}`)} />
                ))
              ) : (
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">暂无关联任务。</div>
              )}
            </div>
          </section>

          <section className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-xl font-semibold text-slate-950">历史快照</h2>
                <p className="mt-1 text-sm text-slate-600">快照是只读的，用于查看历史 Job 对应的冻结配置。</p>
              </div>
              <Badge variant="info">{snapshots.length} 条</Badge>
            </div>
            <div className="mt-6 grid gap-4 lg:grid-cols-2">
              {snapshots.length ? (
                snapshots.map((snapshot) => (
                  <SnapshotCard
                    key={snapshot.snapshot_id}
                    snapshot={snapshot}
                    onOpen={() =>
                      navigate(
                        `/profiles/${encodeURIComponent(profile.profile_id)}/snapshots/${encodeURIComponent(snapshot.snapshot_id)}`,
                      )
                    }
                  />
                ))
              ) : (
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">暂无历史快照。</div>
              )}
            </div>
          </section>
        </>
      ) : null}
    </main>
  );
}
