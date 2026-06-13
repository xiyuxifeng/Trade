import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { ApiError } from '@/lib/api/http';
import { ProfileBootstrapWarning, isBootstrapDefaultProfile } from '@/components/profiles/profile-bootstrap-warning';
import { useSystemStatus } from './use-system-status';

function statusVariant(status: string) {
  if (status === 'ok') {
    return 'success';
  }
  if (status === 'warning' || status === 'partial') {
    return 'warning';
  }
  if (status === 'error') {
    return 'destructive';
  }
  return 'info';
}

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 401 || error.status === 403) return '当前账号没有权限查看系统状态。';
    return '系统状态加载失败，请稍后重试。';
  }

  if (error instanceof Error) {
    return '系统状态加载失败，请稍后重试。';
  }

  if (typeof error === 'object' && error !== null && 'message' in error) {
    const value = (error as { message?: unknown }).message;
    if (typeof value === 'string' && value.trim()) {
      return value;
    }
  }

  return '无法获取系统状态';
}

export function SystemStatusPanel({ productMode = false }: { productMode?: boolean } = {}) {
  const { data, error, isLoading, refetch, isFetching } = useSystemStatus();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>系统状态</CardTitle>
          <CardDescription>正在获取当前运行环境信息。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton className="h-5 w-2/5" />
          <Skeleton className="h-5 w-3/5" />
          <Skeleton className="h-24 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    const message = getErrorMessage(error as unknown);
    return (
      <Card>
        <CardHeader>
          <CardTitle>系统状态</CardTitle>
          <CardDescription>当前状态接口请求失败。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
            {message}
          </div>
          <Button variant="outline" onClick={() => refetch()} disabled={isFetching}>
            {isFetching ? '重试中' : '重试'}
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>系统状态</CardTitle>
          <CardDescription>暂无可显示的数据。</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const directoryEntries = Object.entries(data.directories);
  const profileContext = data.profile_context ?? null;
  const runtimeProfileId = profileContext?.profile_id ?? data.profile_id ?? null;
  const runtimeProfileSnapshotId = profileContext?.profile_snapshot_id ?? data.profile_snapshot_id ?? null;
  const isBootstrapDefault = isBootstrapDefaultProfile(runtimeProfileId, runtimeProfileSnapshotId);

  if (productMode) {
    const unavailableDirectories = directoryEntries.filter(([, info]) => !info.exists).length;
    return (
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle>业务可用状态</CardTitle>
              <CardDescription>检查当前服务和关键依赖是否支持业务操作。</CardDescription>
            </div>
            <Button variant="outline" onClick={() => refetch()} disabled={isFetching}>
              {isFetching ? '刷新中' : '刷新状态'}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-3">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <p className="text-xs text-slate-500">核心服务</p>
            <p className="mt-2 font-medium text-slate-950">{data.database.status === 'ok' ? '可用' : data.database.status === 'warning' ? '部分可用' : '不可用'}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <p className="text-xs text-slate-500">当前画像</p>
            <p className="mt-2 font-medium text-slate-950">{runtimeProfileId ? '已绑定' : '未绑定'}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <p className="text-xs text-slate-500">依赖检查</p>
            <p className="mt-2 font-medium text-slate-950">{unavailableDirectories ? `${unavailableDirectories} 项需处理` : '全部可用'}</p>
          </div>
          {data.warnings.length ? (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 md:col-span-3">
              当前有 {data.warnings.length} 项依赖异常，受影响操作应在修复后重试。
            </div>
          ) : null}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle>系统状态</CardTitle>
            <CardDescription>实时查看当前运行配置、数据库和关键目录。</CardDescription>
          </div>
          <Button variant="outline" onClick={() => refetch()} disabled={isFetching}>
            {isFetching ? '刷新中' : '刷新'}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="grid gap-5">
        {isBootstrapDefault ? (
          <ProfileBootstrapWarning
            className="border-amber-300 bg-amber-50/90"
            profileId={runtimeProfileId}
            profileSnapshotId={runtimeProfileSnapshotId}
          />
        ) : null}
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">运行模式</p>
            <p className="mt-2 text-base font-semibold">{data.run_mode}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">数据库</p>
            <div className="mt-2 flex items-center gap-2">
              <Badge variant={statusVariant(data.database.status)}>{data.database.status}</Badge>
              {data.database.latency_ms != null ? (
                <span className="text-sm text-slate-600">{data.database.latency_ms} ms</span>
              ) : null}
            </div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Profile 运行态</p>
            <p className="mt-2 break-all text-sm text-slate-900">{profileContext?.profile_id ?? data.profile_id ?? '未绑定'}</p>
            <p className="mt-1 break-all text-xs text-slate-500">
              snapshot: {profileContext?.profile_snapshot_id ?? data.profile_snapshot_id ?? '未绑定'} · source: {profileContext?.source ?? 'unset'}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Profile</p>
            <p className="mt-2 text-base font-semibold text-slate-950">{profileContext?.profile_id ?? data.profile_id ?? '未绑定'}</p>
            <p className="mt-1 break-all text-xs text-slate-500">
              snapshot: {profileContext?.profile_snapshot_id ?? data.profile_snapshot_id ?? '未绑定'} · source: {profileContext?.source ?? 'unset'}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">项目根目录</p>
            <p className="mt-2 break-all text-sm text-slate-900">{data.project_root}</p>
          </div>
        </div>

        <div className="grid gap-3">
          <p className="text-sm font-medium text-slate-800">关键目录</p>
          <div className="grid gap-2">
            {directoryEntries.map(([name, info]) => (
              <div
                className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3"
                key={name}
              >
                <div>
                  <p className="font-medium">{name}</p>
                  <p className="text-xs text-slate-500 break-all">{info.path}</p>
                </div>
                <Badge variant={info.exists ? 'success' : 'warning'}>
                  {info.exists ? '存在' : '缺失'}
                </Badge>
              </div>
            ))}
          </div>
        </div>

        <div className="grid gap-2">
          <p className="text-sm font-medium text-slate-800">告警与提示</p>
          {data.warnings.length ? (
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-100">
              <p className="font-medium">发现 {data.warnings.length} 个目录异常</p>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-amber-50/90">
                {data.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          ) : (
            <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-100">
              关键目录检查通过。
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
