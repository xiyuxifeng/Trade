import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { useAuth } from '@/features/auth/auth-context';
import { ApiError } from '@/lib/api/http';
import { listProfiles } from '@/lib/api/profiles';
import { runWorkflow } from '@/lib/api/workflows';
import type { WorkflowDefinition, WorkflowParamField, WorkflowRunResponse } from '@/types/workflows';
import type { ProfileRecord } from '@/types/profile';
import {
  buildWorkflowDefaultValues,
  getWorkflowRunSchema,
  summarizeWorkflowRisk,
  validateWorkflowValues,
  type WorkflowFieldValues,
} from './workflow-form-utils';

function prettyJson(value: unknown) {
  return JSON.stringify(value, null, 2);
}

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return '工作流运行失败';
}

function getApiFieldErrors(error: unknown): Record<string, string> {
  if (!(error instanceof ApiError)) return {};

  const detail = error.payload?.detail;
  if (!detail || typeof detail !== 'object' || Array.isArray(detail)) return {};

  const fields = (detail as { fields?: unknown }).fields;
  if (!fields || typeof fields !== 'object' || Array.isArray(fields)) return {};

  return Object.fromEntries(
    Object.entries(fields).map(([name, value]) => [name, typeof value === 'string' ? value : JSON.stringify(value)]),
  );
}

function FieldEditor({
  name,
  field,
  value,
  error,
  onChange,
}: {
  name: string;
  field: WorkflowParamField;
  value: string | boolean | undefined;
  error?: string;
  onChange: (nextValue: string | boolean) => void;
}) {
  const errorId = `workflow-field-${name}-error`;
  const label = (
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-medium text-slate-900">{name}</p>
          <p className="mt-1 text-sm text-slate-600">{field.description}</p>
        </div>
      <div className="flex flex-wrap gap-2">
        <Badge variant={field.required ? 'warning' : 'default'}>{field.required ? '必填' : '可选'}</Badge>
        <Badge variant="info">{field.type}</Badge>
      </div>
    </div>
  );

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      {label}
      <div className="mt-4">
        {field.type === 'boolean' ? (
          <label className="flex items-center gap-3 text-sm text-slate-700">
            <input
              aria-describedby={error ? errorId : undefined}
              aria-invalid={error ? 'true' : undefined}
              checked={Boolean(value)}
              className="h-4 w-4 rounded border-slate-300 bg-white"
              onChange={(event) => onChange(event.target.checked)}
              type="checkbox"
            />
            <span>{field.default ? '默认开启' : '默认关闭'}</span>
          </label>
        ) : field.enum.length ? (
          <Select
            aria-describedby={error ? errorId : undefined}
            aria-invalid={error ? 'true' : undefined}
            value={String(value ?? '')}
            onChange={(event) => onChange(event.target.value)}
          >
            <option value="">{field.required ? '请选择' : '保持默认'}</option>
            {field.enum.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </Select>
        ) : field.type === 'array' || field.type === 'object' ? (
          <Textarea
            aria-describedby={error ? errorId : undefined}
            aria-invalid={error ? 'true' : undefined}
            className="min-h-28 font-mono text-xs"
            onChange={(event) => onChange(event.target.value)}
            placeholder={field.type === 'array' ? '[]' : '{}'}
            value={String(value ?? '')}
          />
        ) : (
          <Input
            aria-describedby={error ? errorId : undefined}
            aria-invalid={error ? 'true' : undefined}
            onChange={(event) => onChange(event.target.value)}
            placeholder={field.type === 'date' ? 'YYYY-MM-DD (例如: 2024-01-01)' : ''}
            type={field.type === 'integer' || field.type === 'number' ? 'number' : field.type === 'date' ? 'date' : 'text'}
            value={String(value ?? '')}
          />
        )}
      </div>
      {error ? (
        <p className="mt-2 text-sm text-rose-700" id={errorId}>
          {error}
        </p>
      ) : null}
    </div>
  );
}

export function WorkflowParameterForm({
  workflow,
  onSubmitted,
}: {
  workflow: WorkflowDefinition;
  onSubmitted?: (jobId: string) => void;
}) {
  const queryClient = useQueryClient();
  const { canAccess } = useAuth();
  const schema = getWorkflowRunSchema(workflow);
  const [values, setValues] = useState<WorkflowFieldValues>(() => buildWorkflowDefaultValues(schema));
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [previewParams, setPreviewParams] = useState<Record<string, unknown>>({});
  const [submittedSummary, setSubmittedSummary] = useState<WorkflowRunResponse | null>(null);
  const profilesQuery = useQuery({
    queryKey: ['workflow-parameter-form', 'profiles'],
    queryFn: () => listProfiles({ skip: 0, limit: 50 }),
    staleTime: 60_000,
  });
  const profileItems = profilesQuery.data?.items ?? [];

  const riskSummary = useMemo(() => summarizeWorkflowRisk(workflow), [workflow]);
  const canRunWorkflow = canAccess('operator');
  const hasProfileField = Boolean(schema?.fields.profile_id);
  const fields = useMemo(
    () => Object.entries(schema?.fields ?? {}).filter(([name]) => !(hasProfileField && name === 'config_path')),
    [hasProfileField, schema?.fields],
  );
  const previewValues = useMemo(() => {
    if (!hasProfileField) return values;
    const next = { ...values };
    delete next.config_path;
    return next;
  }, [hasProfileField, values]);

  useEffect(() => {
    setValues(buildWorkflowDefaultValues(schema));
    setErrorMessage(null);
    setFieldErrors({});
    setConfirmOpen(false);
    setPreviewParams({});
    setSubmittedSummary(null);
  }, [schema, workflow.workflow_id]);

  useEffect(() => {
    if (!hasProfileField || !profileItems.length) {
      return;
    }
    if (!String(values.profile_id ?? '').trim()) {
      setValues((current) => ({ ...current, profile_id: profileItems[0].profile_id }));
    }
  }, [hasProfileField, profileItems, values.profile_id]);

  const runMutation = useMutation({
    mutationFn: async (request: { params: Record<string, unknown>; confirmed: boolean }) => {
      return runWorkflow(workflow.workflow_id, {
        params: request.params,
        created_by: 'web',
        confirmed: request.confirmed,
      });
    },
    onSuccess: async (data) => {
      setErrorMessage(null);
      setFieldErrors({});
      setSubmittedSummary(data);
      setConfirmOpen(false);
      await queryClient.invalidateQueries({ queryKey: ['jobs'] });
      if (data.job?.id) {
        onSubmitted?.(data.job.id);
      }
    },
    onError: (error: unknown) => {
      setSubmittedSummary(null);
      setFieldErrors(getApiFieldErrors(error));
      setErrorMessage(getErrorMessage(error));
    },
  });

  const submit = () => {
    if (!canRunWorkflow) {
      setErrorMessage('当前身份需要 operator 权限才能提交工作流。');
      return;
    }

    const validation = validateWorkflowValues(schema, values);
    if (validation.errors.length) {
      setErrorMessage(validation.errors.join('；'));
      setFieldErrors(validation.fieldErrors);
      return;
    }

    const submittedParams = hasProfileField
      ? Object.fromEntries(Object.entries(validation.params).filter(([name]) => name !== 'config_path'))
      : validation.params;
    setPreviewParams(submittedParams);
    setErrorMessage(null);
    setFieldErrors({});

    if (riskSummary.requiresConfirmation) {
      setConfirmOpen(true);
      return;
    }

    runMutation.mutate({ params: submittedParams, confirmed: false });
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle>参数表单</CardTitle>
            <CardDescription>根据工作流 schema 自动生成填写项，并在高风险操作上二次确认。</CardDescription>
          </div>
          <Badge variant={riskSummary.requiresConfirmation ? 'warning' : 'success'}>{riskSummary.label}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {!schema ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
          当前工作流没有可编辑参数。
        </div>
        ) : (
          <>
            {hasProfileField ? (
              <div className="rounded-2xl border border-slate-200 bg-white p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-medium text-slate-900">Profile</p>
                    <p className="mt-1 text-sm text-slate-600">Web 主流程只认 Profile，`config_path` 仅保留兼容/调试入口。</p>
                  </div>
                  <Badge variant={profileItems.length === 0 ? 'warning' : 'info'}>{profileItems.length === 0 ? '无可用 Profile' : 'Profile'}</Badge>
                </div>
                <label className="mt-4 block space-y-2">
                  <span className="text-sm font-medium text-slate-700">Profile</span>
                  <Select
                    aria-invalid={fieldErrors.profile_id ? 'true' : undefined}
                    aria-label="Profile"
                    value={String(values.profile_id ?? '')}
                    onChange={(event) => {
                      setValues((current) => ({ ...current, profile_id: event.target.value }));
                      setFieldErrors((current) => {
                        const next = { ...current };
                        delete next.profile_id;
                        return next;
                      });
                    }}
                    disabled={profilesQuery.isLoading || profileItems.length === 0}
                  >
                    {profileItems.length === 0 ? <option value="">暂无可用 Profile</option> : null}
                    {profileItems.map((profile: ProfileRecord) => (
                      <option key={profile.profile_id} value={profile.profile_id}>
                        {profile.name} ({profile.profile_id})
                      </option>
                    ))}
                  </Select>
                  {profilesQuery.isError ? <p className="mt-2 text-sm text-rose-700">Profile 列表加载失败，请稍后重试。</p> : null}
                  {fieldErrors.profile_id ? <p className="mt-2 text-sm text-rose-700">{fieldErrors.profile_id}</p> : null}
                </label>
              </div>
            ) : null}
            <div className="grid gap-3">
              {fields.map(([name, field]) =>
                name === 'profile_id' ? null : (
                  <FieldEditor
                    key={name}
                    name={name}
                    field={field}
                    error={fieldErrors[name]}
                    value={values[name]}
                    onChange={(nextValue) => {
                      setValues((current) => ({ ...current, [name]: nextValue }));
                      setFieldErrors((current) => {
                        const next = { ...current };
                        delete next[name];
                        return next;
                      });
                    }}
                  />
                ),
              )}
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">参数预览</p>
              <pre className="mt-3 max-h-64 overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-4 text-xs text-slate-800">
                {prettyJson(previewValues)}
              </pre>
            </div>
          </>
        )}

        {errorMessage ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          {errorMessage}
        </div>
      ) : null}

      {submittedSummary ? (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">
          工作流已提交到 Job Center。
        </div>
      ) : null}

        <div className="flex flex-wrap gap-3">
          <Button onClick={submit} disabled={runMutation.isPending || !schema || !canRunWorkflow}>
            {runMutation.isPending ? '提交中' : riskSummary.requiresConfirmation ? '继续并确认' : '提交运行'}
          </Button>
          <Button
            variant="outline"
            onClick={() => {
              setValues(buildWorkflowDefaultValues(schema));
              setErrorMessage(null);
              setFieldErrors({});
            }}
          >
            重置默认值
          </Button>
        </div>
        {!canRunWorkflow ? (
          <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-700">
            当前身份仅可查看参数，提交运行需要 operator 权限。
          </div>
        ) : null}
      </CardContent>

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>确认高风险操作</DialogTitle>
            <DialogDescription>
              该工作流包含高风险或需要确认的步骤，请先核对参数摘要和影响范围。
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4">
            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-2xl border border-slate-200 bg-white p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">工作流</p>
                <p className="mt-2 font-medium text-slate-900">{workflow.title}</p>
                <p className="mt-1 text-sm text-slate-600">{workflow.description}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">风险说明</p>
                <p className="mt-2 font-medium text-slate-900">{workflow.job_definition?.risk ?? 'medium'}</p>
                <p className="mt-1 text-sm text-slate-600">提交后会创建 Job 并进入任务中心。</p>
              </div>
            </div>
            <div>
              <p className="mb-2 text-sm font-medium text-slate-800">参数摘要</p>
              <pre className="max-h-72 overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-4 text-xs text-slate-800">
                {prettyJson(previewParams)}
              </pre>
            </div>
          </div>

          <DialogFooter>
            <DialogClose className="rounded-xl border border-slate-200 px-4 py-2 text-sm text-slate-700 transition-colors hover:bg-slate-50">
              取消
            </DialogClose>
            <Button
              onClick={() => runMutation.mutate({ params: previewParams, confirmed: true })}
              disabled={runMutation.isPending || !canRunWorkflow}
            >
              {runMutation.isPending ? '提交中' : '确认提交'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
