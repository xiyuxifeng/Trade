import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { Archive, RefreshCw, Save, ShieldAlert } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { useAuth } from '@/features/auth/auth-context';
import { ApiError } from '@/lib/api/http';
import { archiveProfile, getProfileEdit, updateProfile, validateProfileUpdate } from '@/lib/api/profiles';
import type {
  ProfileEditDraft,
  ProfileEditResponse,
  ProfileEditSectionGuide,
  ProfileValidationIssue,
  ProfileValidationStatus,
} from '@/types/profile';
import { ProfileStatusBadge } from '@/components/profiles/ProfileStatusBadge';

type SectionDraftMap = Record<string, string>;
type SectionErrorMap = Record<string, string>;

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
  return '配置编辑失败';
}

function stringifyJson(value: unknown) {
  try {
    return JSON.stringify(value ?? {}, null, 2);
  } catch {
    return JSON.stringify(String(value), null, 2);
  }
}

function parseSectionText(value: string, sectionKey: string) {
  const trimmed = value.trim();
  if (!trimmed) {
    return {};
  }

  try {
    return JSON.parse(trimmed) as unknown;
  } catch {
    throw new Error(`${sectionKey} 分区的 JSON 格式无效，请修正后再保存。`);
  }
}

function normalizeSectionDrafts(sectionDrafts: SectionDraftMap) {
  const sections: Record<string, unknown> = {};
  const errors: SectionErrorMap = {};

  Object.entries(sectionDrafts).forEach(([key, text]) => {
    try {
      sections[key] = parseSectionText(text, key);
    } catch (error) {
      errors[key] = error instanceof Error ? error.message : 'JSON 格式无效';
    }
  });

  return { sections, errors };
}

function buildSectionDraftMap(sectionGuide: ProfileEditSectionGuide[]) {
  const nextDrafts: SectionDraftMap = {};
  sectionGuide.forEach((guide) => {
    nextDrafts[guide.key] = stringifyJson(guide.draft_value ?? guide.current_value ?? {});
  });
  return nextDrafts;
}

function ValidationSummary({
  status,
  issues,
}: {
  status: ProfileValidationStatus;
  issues: ProfileValidationIssue[];
}) {
  const issueCount = issues.length;
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">当前校验结果</p>
          <p className="mt-2 text-sm text-slate-700">保存前必须先通过校验，才能生成新的配置版本。</p>
        </div>
        <ProfileStatusBadge status={status} />
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <Badge variant={issueCount ? 'warning' : 'success'}>{issueCount ? `${issueCount} 个问题` : '无问题'}</Badge>
        <Badge variant="info">保存前校验</Badge>
      </div>
      {issueCount ? (
        <ul className="mt-3 space-y-2 text-sm text-slate-700">
          {issues.map((issue) => (
            <li key={`${issue.field}-${issue.message}`} className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2">
              <span className="font-medium text-amber-900">{issue.field}</span>
              <span className="ml-2 text-amber-800">{issue.message}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function SectionEditor({
  guide,
  value,
  onChange,
  error,
}: {
  guide: ProfileEditSectionGuide;
  value: string;
  onChange: (next: string) => void;
  error?: string;
}) {
  return (
    <Card className="border-slate-200 bg-white text-slate-900 shadow-sm">
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle className="text-base text-slate-950">{guide.title}</CardTitle>
            <CardDescription className="mt-1 text-slate-600">{guide.description}</CardDescription>
          </div>
          <Badge variant="info">{guide.source}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid gap-3 md:grid-cols-2">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">当前值</p>
            <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap break-words rounded-xl border border-slate-200 bg-white p-3 text-xs leading-6 text-slate-800">
              {stringifyJson(guide.current_value)}
            </pre>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">默认值</p>
            <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap break-words rounded-xl border border-slate-200 bg-white p-3 text-xs leading-6 text-slate-800">
              {stringifyJson(guide.default_value)}
            </pre>
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium text-slate-700" htmlFor={`section-${guide.key}`}>
            编辑内容
          </label>
          <Textarea
            id={`section-${guide.key}`}
            className="min-h-40 border-slate-200 bg-white font-mono text-sm text-slate-900 placeholder:text-slate-400"
            value={value}
            onChange={(event) => onChange(event.target.value)}
            placeholder={stringifyJson(guide.current_value)}
          />
          {error ? <p className="text-sm text-rose-700">{error}</p> : null}
        </div>
      </CardContent>
    </Card>
  );
}

export function ProfileEditPage() {
  const params = useParams<{ profileId?: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { canAccess, principal } = useAuth();
  const profileId = params.profileId?.trim() || '';

  const canEditProfiles = canAccess('operator');
  const canArchiveProfiles = canAccess('admin');

  const editQuery = useQuery<ProfileEditResponse, ApiError>({
    queryKey: ['profile-edit', profileId],
    queryFn: () => getProfileEdit(profileId),
    enabled: Boolean(profileId) && canEditProfiles,
    staleTime: 5_000,
  });

  const [profileName, setProfileName] = useState('');
  const [environment, setEnvironment] = useState('');
  const [sectionDrafts, setSectionDrafts] = useState<SectionDraftMap>({});
  const [draftErrors, setDraftErrors] = useState<SectionErrorMap>({});
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const [validationState, setValidationState] = useState<ProfileEditResponse['validation'] | null>(null);
  const [draftDirty, setDraftDirty] = useState(false);

  useEffect(() => {
    if (!editQuery.data) {
      return;
    }

    setProfileName(editQuery.data.draft.name);
    setEnvironment(editQuery.data.draft.environment);
    setSectionDrafts(buildSectionDraftMap(editQuery.data.section_guide));
    setValidationState(editQuery.data.validation);
    setDraftErrors({});
    setValidationMessage(null);
    setDraftDirty(false);
  }, [editQuery.data]);

  const sections = useMemo(() => editQuery.data?.section_guide ?? [], [editQuery.data]);
  const profile = editQuery.data?.profile ?? null;
  const preview = editQuery.data?.preview ?? null;
  const validation =
    validationState ??
    (draftDirty
      ? {
          valid: false,
          issues: [],
          next_version: profile?.version ? profile.version + 1 : 1,
          validation_status: 'draft' as ProfileValidationStatus,
        }
      : editQuery.data?.validation ?? null);

  function markDraftDirty() {
    setValidationState(null);
    setValidationMessage(null);
    setDraftDirty(true);
  }

  function updateSectionDraft(sectionKey: string, nextValue: string) {
    setSectionDrafts((current) => ({
      ...current,
      [sectionKey]: nextValue,
    }));
    setDraftErrors((current) => {
      if (!current[sectionKey]) {
        return current;
      }
      const nextErrors = { ...current };
      delete nextErrors[sectionKey];
      return nextErrors;
    });
    markDraftDirty();
  }

  const validateMutation = useMutation({
    mutationFn: async () => {
      const normalized = normalizeSectionDrafts(sectionDrafts);
      if (Object.keys(normalized.errors).length) {
        setDraftErrors(normalized.errors);
        throw new Error('请先修正分区 JSON 格式。');
      }
      const draft = {
        name: profileName.trim(),
        environment: environment.trim(),
        sections: normalized.sections,
      } satisfies ProfileEditDraft;
      return validateProfileUpdate(profileId, draft);
    },
    onSuccess: (result) => {
      setValidationState(result.validation);
      setDraftErrors({});
      setDraftDirty(false);
      if (result.validation.valid) {
        setValidationMessage('配置校验通过，可以保存新版本。');
      } else {
        setValidationMessage('配置存在问题，请先修复后再保存。');
      }
    },
    onError: (error) => {
      setValidationMessage(getErrorMessage(error));
    },
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      const normalized = normalizeSectionDrafts(sectionDrafts);
      if (Object.keys(normalized.errors).length) {
        setDraftErrors(normalized.errors);
        throw new Error('请先修正分区 JSON 格式。');
      }
      const draft = {
        name: profileName.trim(),
        environment: environment.trim(),
        sections: normalized.sections,
      };
      const validationResult = await validateProfileUpdate(profileId, draft);
      setValidationState(validationResult.validation);
      if (!validationResult.validation.valid) {
        throw new Error('请先修复校验问题后再保存。');
      }
      return updateProfile(profileId, {
        ...draft,
        confirmed: true,
      });
    },
    onSuccess: async (result) => {
      setValidationMessage('已保存为新版本，正在返回配置详情。');
      setDraftDirty(false);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['profile-detail', profileId] }),
        queryClient.invalidateQueries({ queryKey: ['profiles'] }),
        queryClient.invalidateQueries({ queryKey: ['profile-edit', profileId] }),
      ]);
      navigate(`/profiles/${encodeURIComponent(result.profile.profile_id)}`);
    },
    onError: (error) => {
      setValidationMessage(getErrorMessage(error));
    },
  });

  const archiveMutation = useMutation({
    mutationFn: async () => {
      if (!window.confirm(`确定归档配置「${profile?.name ?? profileId}」吗？归档后将保留历史快照，但不会再作为默认配置使用。`)) {
        throw new Error('已取消归档。');
      }
      return archiveProfile(profileId, { archived_by: principal.role || 'web' });
    },
    onSuccess: async () => {
      setValidationMessage('配置已归档。');
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['profile-detail', profileId] }),
        queryClient.invalidateQueries({ queryKey: ['profiles'] }),
        queryClient.invalidateQueries({ queryKey: ['profile-edit', profileId] }),
      ]);
      navigate(`/profiles/${encodeURIComponent(profileId)}`);
    },
    onError: (error) => {
      if (error instanceof Error && error.message === '已取消归档。') {
        setValidationMessage('已取消归档。');
        return;
      }
      setValidationMessage(getErrorMessage(error));
    },
  });

  const isArchived = profile?.validation_status === 'archived';

  if (!canEditProfiles) {
    return (
      <main className="page-stack">
        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-lg font-semibold text-slate-900">没有权限编辑配置</p>
          <p className="mt-2 text-sm text-slate-600">当前身份为 {principal.role}，至少需要 operator 权限。</p>
        </section>
      </main>
    );
  }

  const permissionDenied = editQuery.error instanceof ApiError && (editQuery.error.status === 401 || editQuery.error.status === 403);
  const notFound = editQuery.error instanceof ApiError && editQuery.error.status === 404;

  return (
    <main className="page-stack">
      <section className="rounded-[28px] border border-slate-200 bg-white/90 p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-3xl">
            <Badge variant="info">配置编辑</Badge>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">{profile?.name ?? '配置编辑'}</h1>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              按分区编辑正式配置，先校验再保存，保存后会生成新的版本，不会影响历史 Job 快照。
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
              variant="outline"
              onClick={() => editQuery.refetch()}
              disabled={editQuery.isFetching}
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              {editQuery.isFetching ? '刷新中' : '刷新'}
            </Button>
            <Button className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50" variant="outline" onClick={() => navigate(`/profiles/${encodeURIComponent(profileId)}`)}>
              返回详情
            </Button>
          </div>
        </div>
      </section>

      {validationMessage ? (
        <div className="rounded-2xl border border-sky-500/30 bg-sky-500/10 px-4 py-3 text-sm text-sky-900">
          {validationMessage}
        </div>
      ) : null}

      {editQuery.isLoading ? (
        <section className="rounded-3xl border border-slate-200 bg-white p-6 text-sm text-slate-500 shadow-sm">正在加载编辑数据...</section>
      ) : editQuery.error ? (
        <section
          className={`rounded-3xl border p-6 ${
            permissionDenied ? 'border-amber-200 bg-amber-50 text-amber-900' : 'border-rose-200 bg-rose-50 text-rose-800'
          }`}
        >
          <p className="font-medium">{notFound ? '配置不存在' : getErrorMessage(editQuery.error)}</p>
          <p className="mt-2 text-sm text-slate-600">
            {notFound ? '请检查配置 ID 是否正确。' : '请稍后重试或检查访问权限。'}
          </p>
        </section>
      ) : profile ? (
        <section className="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(340px,0.85fr)]">
          <Card className="border-slate-200 bg-white text-slate-900 shadow-sm">
            <CardHeader>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <CardTitle className="text-slate-950">基础信息</CardTitle>
                  <CardDescription className="text-slate-600">先编辑名称和环境，再逐个调整分区。</CardDescription>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="info">
                    版本 {profile.version} → {validation?.next_version ?? profile.version + 1}
                  </Badge>
                  <ProfileStatusBadge status={profile.validation_status} />
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-700" htmlFor="profile_name">
                    配置名称
                  </label>
                  <Input
                    id="profile_name"
                    className="border-slate-200 bg-white text-slate-900 placeholder:text-slate-400"
                    value={profileName}
                    onChange={(event) => {
                      setProfileName(event.target.value);
                      markDraftDirty();
                    }}
                    placeholder="请输入配置名称"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-700" htmlFor="environment">
                    运行环境
                  </label>
                  <Input
                    id="environment"
                    className="border-slate-200 bg-white text-slate-900 placeholder:text-slate-400"
                    value={environment}
                    onChange={(event) => {
                      setEnvironment(event.target.value);
                      markDraftDirty();
                    }}
                    placeholder="production / staging / dev"
                  />
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-3">
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 shadow-sm">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">配置 ID</p>
                  <p className="mt-2 break-all text-sm text-slate-900">{profile.profile_id}</p>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 shadow-sm">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">最近更新</p>
                  <p className="mt-2 text-sm text-slate-900">{formatTimestamp(profile.updated_at)}</p>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 shadow-sm">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">当前状态</p>
                  <div className="mt-2">
                    <ProfileStatusBadge status={profile.validation_status} />
                  </div>
                </div>
              </div>

              <ValidationSummary status={validation?.validation_status ?? profile.validation_status} issues={validation?.issues ?? []} />

              {isArchived ? (
                <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                  该配置已归档。你仍可以查看历史，但保存操作不会作为默认工作流继续使用。
                </div>
              ) : null}
            </CardContent>
          </Card>

          <Card className="border-slate-200 bg-white text-slate-900 shadow-sm">
            <CardHeader>
              <CardTitle className="text-slate-950">保存前检查</CardTitle>
              <CardDescription className="text-slate-600">先校验再保存，避免写入无效配置。</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 shadow-sm">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">预览版本</p>
                <p className="mt-2 text-sm text-slate-900">下一版本号：{validation?.next_version ?? profile.version + 1}</p>
                <p className="mt-2 text-sm text-slate-600">预览校验状态：{preview?.validation_status ?? validation?.validation_status ?? profile.validation_status}</p>
                <p className="mt-2 text-sm text-slate-600">预览名称：{preview?.name ?? profileName ?? profile.name}</p>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 shadow-sm">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">配置摘要</p>
                <p className="mt-2 text-sm text-slate-900">当前预览来自正式 Profile 的脱敏副本，不会暴露 secret 原文。</p>
                <pre className="mt-3 max-h-72 overflow-auto rounded-xl border border-slate-200 bg-white p-3 text-xs leading-6 text-slate-800">
                  {stringifyJson({
                    name: profileName || profile.name,
                    environment: environment || profile.environment,
                    sections: sectionDrafts,
                  })}
                </pre>
              </div>

              <div className="flex flex-wrap gap-2">
                <Button
                  className="bg-sky-500 text-slate-950 hover:bg-sky-400"
                  onClick={() => validateMutation.mutate()}
                  disabled={validateMutation.isPending || saveMutation.isPending || archiveMutation.isPending}
                >
                  <ShieldAlert className="mr-2 h-4 w-4" />
                  {validateMutation.isPending ? '校验中' : '校验配置'}
                </Button>
                <Button
                  className="bg-emerald-500 text-slate-950 hover:bg-emerald-400"
                  onClick={() => saveMutation.mutate()}
                  disabled={saveMutation.isPending || archiveMutation.isPending}
                >
                  <Save className="mr-2 h-4 w-4" />
                  {saveMutation.isPending ? '保存中' : '保存新版本'}
                </Button>
                {canArchiveProfiles ? (
                  <Button
                    className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                    variant="outline"
                    onClick={() => archiveMutation.mutate()}
                    disabled={archiveMutation.isPending || saveMutation.isPending}
                  >
                    <Archive className="mr-2 h-4 w-4" />
                    {archiveMutation.isPending ? '归档中' : '归档配置'}
                  </Button>
                ) : null}
              </div>
            </CardContent>
          </Card>

          <div className="xl:col-span-2 space-y-4">
            {sections.length ? (
              sections.map((guide) => (
                <SectionEditor
                  key={guide.key}
                  guide={guide}
                  value={sectionDrafts[guide.key] ?? stringifyJson(guide.current_value)}
                  error={draftErrors[guide.key]}
                  onChange={(next) => updateSectionDraft(guide.key, next)}
                />
              ))
            ) : (
              <Card className="border-slate-200 bg-white text-slate-900 shadow-sm">
                <CardContent className="p-6 text-sm text-slate-500">当前配置没有可编辑分区。</CardContent>
              </Card>
            )}
          </div>
        </section>
      ) : null}
    </main>
  );
}
