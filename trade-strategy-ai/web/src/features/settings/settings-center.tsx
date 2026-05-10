import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Textarea } from '@/components/ui/textarea';
import { useAuth } from '@/features/auth/auth-context';
import { ApiError } from '@/lib/api/http';
import {
  getSettingsConfig,
  getSettingsSchema,
  listSettingsBackups,
  restoreSettingsBackup,
  saveSettings,
  validateSettingsDraft,
} from '@/lib/api/settings';
import type { SettingsBackupItem, SettingsConfigResponse, SettingsSectionSummary } from '@/types/settings';
import { PageHeader } from '@/components/layout/page-header';

type ValueKind = 'json' | 'string' | 'number' | 'boolean' | 'null';

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return '配置数据加载失败';
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function getValueKind(value: unknown): ValueKind {
  if (value === null || value === undefined) return 'null';
  if (Array.isArray(value) || isPlainObject(value)) return 'json';
  if (typeof value === 'boolean') return 'boolean';
  if (typeof value === 'number') return 'number';
  return 'string';
}

function stringifyValue(value: unknown): string {
  if (value === null || value === undefined) return 'null';
  if (Array.isArray(value) || isPlainObject(value)) return JSON.stringify(value, null, 2);
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  return String(value);
}

function prettyJson(value: unknown) {
  return JSON.stringify(value, null, 2);
}

function formatBytes(bytes: number | null | undefined) {
  if (bytes == null) return '未知';
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

function sectionBadgeVariant(kind: ValueKind) {
  if (kind === 'boolean') return 'success';
  if (kind === 'number') return 'info';
  if (kind === 'json') return 'warning';
  return 'default';
}

function parseSectionDraft(value: string, kind: ValueKind): unknown {
  if (kind === 'json') {
    const trimmed = value.trim();
    if (!trimmed) return null;
    return JSON.parse(trimmed);
  }
  if (kind === 'boolean') {
    return value === 'true';
  }
  if (kind === 'number') {
    const trimmed = value.trim();
    if (!trimmed) return null;
    const parsed = Number(trimmed);
    if (Number.isNaN(parsed)) {
      throw new Error('数字格式不合法');
    }
    return parsed;
  }
  if (kind === 'null') {
    const trimmed = value.trim();
    if (!trimmed || trimmed === 'null') return null;
    return trimmed;
  }
  return value;
}

function buildDraftPayload(
  sections: SettingsSectionSummary[],
  draftValues: Record<string, string>,
  draftKinds: Record<string, ValueKind>,
  dirtySections: Set<string>,
) {
  const draft: Record<string, unknown> = {};
  for (const section of sections) {
    if (!dirtySections.has(section.key)) continue;
    const kind = draftKinds[section.key] ?? 'string';
    const rawValue = draftValues[section.key] ?? '';
    draft[section.key] = parseSectionDraft(rawValue, kind);
  }
  return draft;
}

function SectionEditor({
  section,
  kind,
  value,
  dirty,
  onChange,
}: {
  section: SettingsSectionSummary;
  kind: ValueKind;
  value: string;
  dirty: boolean;
  onChange: (nextValue: string) => void;
}) {
  const inputId = `setting-${section.key}`;
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <label className="font-medium text-slate-100" htmlFor={inputId}>
            {section.title}
          </label>
          <p className="mt-1 text-sm text-slate-400">{section.summary}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge variant={dirty ? 'warning' : 'default'}>{dirty ? '已修改' : '未修改'}</Badge>
          <Badge variant={sectionBadgeVariant(kind)}>{kind}</Badge>
        </div>
      </div>

      <div className="mt-4">
        {kind === 'boolean' ? (
          <Select id={inputId} value={value} onChange={(event) => onChange(event.target.value)}>
            <option value="true">true</option>
            <option value="false">false</option>
          </Select>
        ) : kind === 'number' ? (
          <Input
            id={inputId}
            onChange={(event) => onChange(event.target.value)}
            placeholder="0"
            type="number"
            value={value}
          />
        ) : kind === 'json' ? (
          <Textarea
            id={inputId}
            className="min-h-40 font-mono text-xs"
            onChange={(event) => onChange(event.target.value)}
            placeholder='{"key": "value"}'
            value={value}
          />
        ) : (
          <Input
            id={inputId}
            onChange={(event) => onChange(event.target.value)}
            placeholder={kind === 'null' ? 'null' : ''}
            value={value}
          />
        )}
      </div>

      {kind === 'json' ? (
        <p className="mt-3 text-xs text-slate-500">
          JSON 仅需包含你想修改的字段。敏感项保持为空或改成环境变量引用。
        </p>
      ) : null}
    </div>
  );
}

function BackupCard({
  item,
  disabled,
  onRestore,
}: {
  item: SettingsBackupItem;
  disabled: boolean;
  onRestore: () => void;
}) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-medium text-slate-100">{item.name}</p>
          <p className="mt-1 break-all text-xs text-slate-500">{item.path}</p>
        </div>
        <Badge variant="info">{formatBytes(item.size_bytes)}</Badge>
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-slate-500">{formatTimestamp(item.modified_at)}</p>
        <Button variant="outline" size="sm" onClick={onRestore} disabled={disabled}>
          Restore
        </Button>
      </div>
    </div>
  );
}

export function SettingsCenter() {
  const queryClient = useQueryClient();
  const { canAccess, principal } = useAuth();
  const [configPathInput, setConfigPathInput] = useState('config/app.yaml');
  const [configPath, setConfigPath] = useState('config/app.yaml');
  const [activeSectionKey, setActiveSectionKey] = useState<string | null>(null);
  const [draftValues, setDraftValues] = useState<Record<string, string>>({});
  const [draftKinds, setDraftKinds] = useState<Record<string, ValueKind>>({});
  const [dirtySections, setDirtySections] = useState<Set<string>>(() => new Set());
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const [lastValidation, setLastValidation] = useState<Record<string, unknown> | null>(null);
  const [lastValidationKey, setLastValidationKey] = useState<string | null>(null);
  const [saveConfirmOpen, setSaveConfirmOpen] = useState(false);
  const [restoreTarget, setRestoreTarget] = useState<SettingsBackupItem | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const configQuery = useQuery<SettingsConfigResponse, ApiError>({
    queryKey: ['settings-config', configPath],
    queryFn: () => getSettingsConfig(configPath),
    staleTime: 10_000,
  });

  const schemaQuery = useQuery({
    queryKey: ['settings-schema', configPath],
    queryFn: () => getSettingsSchema(configPath),
    staleTime: 10_000,
  });

  const backupsQuery = useQuery({
    queryKey: ['settings-backups', configPath],
    queryFn: () => listSettingsBackups(configPath),
    staleTime: 10_000,
  });

  const sections = schemaQuery.data?.sections ?? configQuery.data?.sections ?? [];
  const currentConfig = configQuery.data?.config ?? {};
  const activeSection = sections.find((section) => section.key === activeSectionKey) ?? sections[0] ?? null;
  const canEditSettings = canAccess('admin');

  useEffect(() => {
    const nextDrafts: Record<string, string> = {};
    const nextKinds: Record<string, ValueKind> = {};
    for (const section of sections) {
      const value = currentConfig[section.key];
      nextKinds[section.key] = getValueKind(value);
      nextDrafts[section.key] = stringifyValue(value);
    }
    if (sections.length) {
      setDraftValues(nextDrafts);
      setDraftKinds(nextKinds);
      setDirtySections(new Set());
      setActiveSectionKey((current) => (current && sections.some((section) => section.key === current) ? current : sections[0].key));
      setLastValidation(null);
      setLastValidationKey(null);
      setValidationMessage(null);
      setStatusMessage(null);
    }
  }, [configPath, currentConfig, sections]);

  const dirtyCount = dirtySections.size;
  const backupCount = backupsQuery.data?.count ?? 0;
  const validationDiff = lastValidation?.diff ?? null;
  const currentDraftKey = useMemo(() => {
    try {
      return JSON.stringify(buildDraftPayload(sections, draftValues, draftKinds, dirtySections));
    } catch {
      return 'invalid-draft';
    }
  }, [draftKinds, dirtySections, draftValues, sections]);

  const validateMutation = useMutation({
    mutationFn: async () => {
      const draft = buildDraftPayload(sections, draftValues, draftKinds, dirtySections);
      return validateSettingsDraft({ config_path: configPath, draft });
    },
    onSuccess: (data) => {
      setLastValidation(data);
      setLastValidationKey(currentDraftKey);
      setValidationMessage(null);
      setStatusMessage('配置草稿已校验');
    },
    onError: (error: unknown) => {
      setLastValidation(null);
      setValidationMessage(getErrorMessage(error));
    },
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      const draft = buildDraftPayload(sections, draftValues, draftKinds, dirtySections);
      return saveSettings({ config_path: configPath, draft, confirmed: true });
    },
    onSuccess: async (data) => {
      setSaveConfirmOpen(false);
      setRestoreTarget(null);
      setStatusMessage(
        data.reload_message ? `已保存，备份路径：${data.backup_path}。${data.reload_message}` : `已保存，备份路径：${data.backup_path}`,
      );
      setValidationMessage(null);
      setLastValidation(null);
      setLastValidationKey(null);
      setDirtySections(new Set());
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['settings-config', configPath] }),
        queryClient.invalidateQueries({ queryKey: ['settings-schema', configPath] }),
        queryClient.invalidateQueries({ queryKey: ['settings-backups', configPath] }),
      ]);
    },
    onError: (error: unknown) => {
      setStatusMessage(null);
      setValidationMessage(getErrorMessage(error));
    },
  });

  const restoreMutation = useMutation({
    mutationFn: async (backupPath: string) => {
      return restoreSettingsBackup({ config_path: configPath, backup_path: backupPath, confirmed: true });
    },
    onSuccess: async (data) => {
      setRestoreTarget(null);
      setStatusMessage(
        data.reload_message ? `已从备份恢复：${data.backup_path}。${data.reload_message}` : `已从备份恢复：${data.backup_path}`,
      );
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['settings-config', configPath] }),
        queryClient.invalidateQueries({ queryKey: ['settings-schema', configPath] }),
        queryClient.invalidateQueries({ queryKey: ['settings-backups', configPath] }),
      ]);
    },
    onError: (error: unknown) => {
      setValidationMessage(getErrorMessage(error));
    },
  });

  const openSaveDialog = () => {
    if (!canEditSettings) {
      setValidationMessage('当前身份需要 admin 权限才能保存配置。');
      return;
    }
    if (currentDraftKey === 'invalid-draft') {
      setValidationMessage('配置草稿格式不合法，请先修正 JSON 或数值输入。');
      return;
    }
    if (lastValidationKey !== currentDraftKey) {
      setValidationMessage('请先点击“预览差异”，确认 diff 后再保存。');
      return;
    }
    setSaveConfirmOpen(true);
  };

  const handleResetDraft = () => {
    const nextDrafts: Record<string, string> = {};
    const nextKinds: Record<string, ValueKind> = {};
    for (const section of sections) {
      const value = currentConfig[section.key];
      nextKinds[section.key] = getValueKind(value);
      nextDrafts[section.key] = stringifyValue(value);
    }
    setDraftValues(nextDrafts);
    setDraftKinds(nextKinds);
    setDirtySections(new Set());
    setLastValidation(null);
    setLastValidationKey(null);
    setValidationMessage('已重置为当前配置快照。');
  };

  return (
    <main className="page-stack">
      <PageHeader
        kicker="Settings"
        title="Configuration Studio"
        description="Inspect the masked runtime configuration, edit targeted sections, preview diffs, and manage backups with explicit confirmation."
      />

      <section className="grid gap-6 xl:grid-cols-[minmax(300px,0.8fr)_minmax(0,1.2fr)]">
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle>Configuration path</CardTitle>
                <CardDescription>Load the project config you want to inspect or edit.</CardDescription>
                {!canEditSettings ? (
                  <p className="mt-2 text-sm text-amber-100">当前身份为 {principal.role}，仅可查看和预览配置。</p>
                ) : null}
              </div>
              <Button
                variant="outline"
                onClick={() => {
                  queryClient.invalidateQueries({ queryKey: ['settings-config', configPath] });
                  queryClient.invalidateQueries({ queryKey: ['settings-schema', configPath] });
                  queryClient.invalidateQueries({ queryKey: ['settings-backups', configPath] });
                }}
                disabled={configQuery.isFetching || schemaQuery.isFetching}
              >
                {configQuery.isFetching || schemaQuery.isFetching ? '刷新中' : '刷新'}
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto]">
              <Input value={configPathInput} onChange={(event) => setConfigPathInput(event.target.value)} placeholder="config/app.yaml" />
              <Button
                onClick={() => {
                  setConfigPath(configPathInput.trim() || 'config/app.yaml');
                }}
              >
                Load
              </Button>
            </div>

            <div className="grid gap-3 md:grid-cols-3">
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Sections</p>
                <p className="mt-2 text-2xl font-semibold text-slate-100">{sections.length}</p>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Dirty</p>
                <p className="mt-2 text-2xl font-semibold text-amber-300">{dirtyCount}</p>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Backups</p>
                <p className="mt-2 text-2xl font-semibold text-emerald-300">{backupCount}</p>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Section navigator</p>
              <div className="mt-3 grid gap-2">
                {sections.map((section) => (
                  <button
                    className={[
                      'rounded-xl border px-3 py-3 text-left transition-colors',
                      section.key === activeSection?.key
                        ? 'border-sky-500/40 bg-sky-500/10'
                        : 'border-slate-800 bg-slate-950/60 hover:border-slate-700 hover:bg-slate-900/80',
                    ].join(' ')}
                    key={section.key}
                    onClick={() => setActiveSectionKey(section.key)}
                    type="button"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="font-medium text-slate-100">{section.title}</p>
                        <p className="mt-1 text-xs text-slate-500">{section.summary}</p>
                      </div>
                      <Badge variant={dirtySections.has(section.key) ? 'warning' : sectionBadgeVariant(getValueKind(currentConfig[section.key]))}>
                        {section.key}
                      </Badge>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <Button onClick={() => validateMutation.mutate()} disabled={validateMutation.isPending || !sections.length}>
                {validateMutation.isPending ? '校验中' : '预览差异'}
              </Button>
              <Button
                variant="secondary"
                onClick={openSaveDialog}
                disabled={saveMutation.isPending || currentDraftKey === 'invalid-draft' || !canEditSettings}
              >
                {saveMutation.isPending ? '保存中' : '保存配置'}
              </Button>
              <Button variant="outline" onClick={handleResetDraft} disabled={!sections.length}>
                重置草稿
              </Button>
            </div>

            {validationMessage ? (
              <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
                {validationMessage}
              </div>
            ) : null}

            {statusMessage ? (
              <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-100">
                {statusMessage}
              </div>
            ) : null}
            {canEditSettings ? (
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-300">
                保存和恢复会先写入临时文件并原子替换配置，然后重新加载验证。若运行中的 API / Worker 仍缓存旧配置，请按提示重载。
              </div>
            ) : null}
          </CardContent>
        </Card>

        <div className="grid gap-6">
          <Card>
            <CardHeader>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <CardTitle>{activeSection?.title ?? 'Section editor'}</CardTitle>
                  <CardDescription>
                    {activeSection ? activeSection.summary : 'Select a configuration section to edit.'}
                  </CardDescription>
                </div>
                {activeSection ? (
                  <Badge variant={dirtySections.has(activeSection.key) ? 'warning' : 'success'}>
                    {dirtySections.has(activeSection.key) ? 'Pending changes' : 'Synced'}
                  </Badge>
                ) : null}
              </div>
            </CardHeader>
            <CardContent>
              {!activeSection ? (
                <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">
                  {configQuery.isLoading || schemaQuery.isLoading ? '正在加载配置…' : '没有可编辑的配置项。'}
                </div>
              ) : (
                <SectionEditor
                  dirty={dirtySections.has(activeSection.key)}
                  kind={draftKinds[activeSection.key] ?? getValueKind(currentConfig[activeSection.key])}
                  onChange={(nextValue) => {
                    setDraftValues((current) => ({ ...current, [activeSection.key]: nextValue }));
                    setDraftKinds((current) => ({ ...current, [activeSection.key]: current[activeSection.key] ?? getValueKind(currentConfig[activeSection.key]) }));
                    setDirtySections((current) => {
                      const next = new Set(current);
                      next.add(activeSection.key);
                      return next;
                    });
                  }}
                  section={activeSection}
                  value={draftValues[activeSection.key] ?? stringifyValue(currentConfig[activeSection.key])}
                />
              )}
            </CardContent>
          </Card>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Masked snapshot</CardTitle>
                <CardDescription>Current masked runtime configuration returned by the backend.</CardDescription>
              </CardHeader>
              <CardContent>
                {configQuery.isLoading ? (
                  <Skeleton className="h-72 w-full" />
                ) : configQuery.error ? (
                  <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
                    {getErrorMessage(configQuery.error)}
                  </div>
                ) : (
                  <pre className="max-h-72 overflow-auto rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-xs text-slate-200">
                    {prettyJson(currentConfig)}
                  </pre>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Validation diff</CardTitle>
                <CardDescription>Compare your pending draft with the current config before saving.</CardDescription>
              </CardHeader>
              <CardContent>
                {validateMutation.isPending ? (
                  <Skeleton className="h-72 w-full" />
                ) : validationDiff ? (
                  <pre className="max-h-72 overflow-auto rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-xs text-slate-200">
                    {prettyJson(validationDiff)}
                  </pre>
                ) : (
                  <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">
                    点击“预览差异”后，这里会显示脱敏后的变更结果。
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <CardTitle>Backup history</CardTitle>
                  <CardDescription>Save and restore operations write to the backup directory.</CardDescription>
                </div>
                <Button variant="outline" onClick={() => backupsQuery.refetch()} disabled={backupsQuery.isFetching}>
                  {backupsQuery.isFetching ? '刷新中' : '刷新'}
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {backupsQuery.isLoading ? (
                <Skeleton className="h-40 w-full" />
              ) : backupsQuery.error ? (
                <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
                  {getErrorMessage(backupsQuery.error)}
                </div>
              ) : !backupsQuery.data?.items.length ? (
                <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">
                  当前路径没有找到备份文件。
                </div>
              ) : (
                backupsQuery.data.items.map((item) => (
                  <BackupCard
                    item={item}
                    key={item.path}
                    disabled={!canEditSettings}
                    onRestore={() => {
                      if (!canEditSettings) {
                        setValidationMessage('当前身份需要 admin 权限才能恢复备份。');
                        return;
                      }
                      setRestoreTarget(item);
                    }}
                  />
                ))
              )}
            </CardContent>
          </Card>
        </div>
      </section>

      <Dialog open={saveConfirmOpen} onOpenChange={setSaveConfirmOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Confirm save</DialogTitle>
            <DialogDescription>Saving will write a new backup first and then replace the config file.</DialogDescription>
          </DialogHeader>

          <div className="grid gap-4">
            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Config path</p>
                <p className="mt-2 break-all font-medium text-slate-100">{configPath}</p>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Dirty sections</p>
                <p className="mt-2 font-medium text-slate-100">{dirtyCount}</p>
              </div>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Draft payload</p>
              <pre className="mt-3 max-h-60 overflow-auto text-xs text-slate-200">
                {prettyJson(buildDraftPayload(sections, draftValues, draftKinds, dirtySections))}
              </pre>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setSaveConfirmOpen(false);
              }}
            >
              Cancel
            </Button>
            <Button onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending || !canEditSettings}>
              {saveMutation.isPending ? 'Saving' : 'Confirm save'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={Boolean(restoreTarget)}
        onOpenChange={(open) => {
          if (!open) {
            setRestoreTarget(null);
          }
        }}
      >
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Confirm restore</DialogTitle>
            <DialogDescription>Restoring a backup will overwrite the current config file after confirmation.</DialogDescription>
          </DialogHeader>

          <div className="grid gap-4">
            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Backup path</p>
                <p className="mt-2 break-all font-medium text-slate-100">{restoreTarget?.path}</p>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Target config</p>
                <p className="mt-2 break-all font-medium text-slate-100">{configPath}</p>
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setRestoreTarget(null);
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={() => {
                if (restoreTarget) {
                  restoreMutation.mutate(restoreTarget.path);
                }
              }}
              disabled={restoreMutation.isPending || !restoreTarget || !canEditSettings}
            >
              {restoreMutation.isPending ? 'Restoring' : 'Confirm restore'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  );
}
