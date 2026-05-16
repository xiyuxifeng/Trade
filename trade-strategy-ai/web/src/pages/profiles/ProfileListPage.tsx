import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, RefreshCw, Upload } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useAuth } from '@/features/auth/auth-context';
import { ApiError } from '@/lib/api/http';
import { listProfiles } from '@/lib/api/profiles';
import type { ProfileListResponse, ProfileRecord } from '@/types/profile';
import { ProfileEmptyState } from '@/components/profiles/ProfileEmptyState';
import { ProfileStatusBadge } from '@/components/profiles/ProfileStatusBadge';

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return '配置数据加载失败';
}

function formatTimestamp(value: string | null | undefined) {
  if (!value) return '未记录';
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function ProfileRow({
  profile,
  onOpen,
}: {
  profile: ProfileRecord;
  onOpen: () => void;
}) {
  return (
    <TableRow>
      <TableCell className="text-slate-700">
        <button className="text-left" onClick={onOpen} type="button">
          <div className="font-medium text-slate-900">{profile.name}</div>
          <div className="mt-1 break-all text-xs text-slate-500">{profile.profile_id}</div>
        </button>
      </TableCell>
      <TableCell className="text-slate-700">{profile.environment}</TableCell>
      <TableCell className="text-slate-700">
        <ProfileStatusBadge status={profile.validation_status} />
      </TableCell>
      <TableCell className="text-slate-700">{formatTimestamp(profile.updated_at)}</TableCell>
      <TableCell className="text-right">
        <Button size="sm" variant="ghost" className="text-slate-700 hover:bg-slate-100 hover:text-slate-900" onClick={onOpen}>
          查看详情 <ArrowRight className="ml-2 h-4 w-4" />
        </Button>
      </TableCell>
    </TableRow>
  );
}

export function ProfileListPage() {
  const navigate = useNavigate();
  const { canAccess, principal } = useAuth();
  const [environment, setEnvironment] = useState('');
  const [validationStatus, setValidationStatus] = useState('');

  const canViewProfiles = canAccess('viewer');

  const profilesQuery = useQuery<ProfileListResponse, ApiError>({
    queryKey: ['profiles', { environment, validationStatus }],
    queryFn: () =>
      listProfiles({
        environment: environment || undefined,
        validation_status: validationStatus || undefined,
        limit: 50,
      }),
    enabled: canViewProfiles,
    staleTime: 10_000,
  });

  const profiles = profilesQuery.data?.items ?? [];
  const summary = useMemo(() => {
    const validated = profiles.filter((profile) => profile.validation_status === 'validated').length;
    const draft = profiles.filter((profile) => profile.validation_status === 'draft').length;
    const archived = profiles.filter((profile) => profile.validation_status === 'archived').length;
    return { validated, draft, archived };
  }, [profiles]);

  if (!canViewProfiles) {
    return (
      <main className="page-stack">
        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-lg font-semibold text-slate-900">没有权限访问配置列表</p>
          <p className="mt-2 text-sm text-slate-600">当前身份为 {principal.role}，查看配置至少需要 viewer 权限。</p>
        </section>
      </main>
    );
  }

  const permissionDenied = profilesQuery.error instanceof ApiError && (profilesQuery.error.status === 401 || profilesQuery.error.status === 403);

  return (
    <main className="page-stack">
      <section className="rounded-[28px] border border-slate-200 bg-white/90 p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-3xl">
            <Badge variant="info">配置管理</Badge>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">配置管理工作台</h1>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              查看正式配置、检查校验状态、进入详情页，并从旧的 config_path 导入新的正式配置。
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
              onClick={() => profilesQuery.refetch()}
              disabled={profilesQuery.isFetching}
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              {profilesQuery.isFetching ? '刷新中' : '刷新'}
            </Button>
            <Button onClick={() => navigate('/profiles/import')}>
              <Upload className="mr-2 h-4 w-4" />
              导入配置
            </Button>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <Card className="border-slate-200 bg-white text-slate-900 shadow-sm">
          <CardHeader>
            <CardDescription>总计</CardDescription>
            <CardTitle className="text-3xl text-slate-950">{profilesQuery.data?.count ?? 0}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="border-slate-200 bg-white text-slate-900 shadow-sm">
          <CardHeader>
            <CardDescription>已校验</CardDescription>
            <CardTitle className="text-3xl text-emerald-600">{summary.validated}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="border-slate-200 bg-white text-slate-900 shadow-sm">
          <CardHeader>
            <CardDescription>草稿 / 归档</CardDescription>
            <CardTitle className="text-3xl text-amber-600">
              {summary.draft} / {summary.archived}
            </CardTitle>
          </CardHeader>
        </Card>
      </section>

      <section className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-slate-950">配置列表</h2>
            <p className="mt-1 text-sm text-slate-600">优先看名称、环境、状态和最近更新时间。</p>
          </div>
          <div className="grid w-full gap-3 md:w-auto md:grid-cols-2">
            <Input
              className="border-slate-200 bg-white text-slate-900 placeholder:text-slate-400"
              placeholder="按环境筛选"
              value={environment}
              onChange={(event) => setEnvironment(event.target.value)}
            />
            <Select
              className="border-slate-200 bg-white text-slate-900"
              value={validationStatus}
              onChange={(event) => setValidationStatus(event.target.value)}
            >
              <option value="">所有状态</option>
              <option value="draft">草稿</option>
              <option value="validated">已校验</option>
              <option value="invalid_config">校验失败</option>
              <option value="archived">已归档</option>
            </Select>
          </div>
        </div>

        <div className="mt-6">
          {profilesQuery.isLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          ) : profilesQuery.error ? (
            <div
              className={`rounded-2xl border p-4 text-sm ${
                permissionDenied ? 'border-amber-200 bg-amber-50 text-amber-900' : 'border-rose-200 bg-rose-50 text-rose-800'
              }`}
            >
              <p>{getErrorMessage(profilesQuery.error)}</p>
              {!permissionDenied ? (
                <Button className="mt-3" variant="outline" onClick={() => profilesQuery.refetch()}>
                  重试
                </Button>
              ) : null}
            </div>
          ) : !profiles.length ? (
            <ProfileEmptyState
              title="暂无配置"
              description="当前没有可用的正式配置。"
              actionLabel="前往导入"
              onAction={() => navigate('/profiles/import')}
            />
          ) : (
            <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
              <Table className="text-slate-900">
                <TableHeader className="bg-slate-50">
                  <TableRow>
                    <TableHead>名称</TableHead>
                    <TableHead>环境</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>最近更新</TableHead>
                    <TableHead className="text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {profiles.map((profile) => (
                    <ProfileRow
                      key={profile.profile_id}
                      profile={profile}
                      onOpen={() => navigate(`/profiles/${encodeURIComponent(profile.profile_id)}`)}
                    />
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
