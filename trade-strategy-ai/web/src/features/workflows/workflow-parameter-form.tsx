import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
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
import { runWorkflow } from '@/lib/api/workflows';
import type { WorkflowDefinition, WorkflowParamField, WorkflowRunResponse } from '@/types/workflows';
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

function FieldEditor({
  name,
  field,
  value,
  onChange,
}: {
  name: string;
  field: WorkflowParamField;
  value: string | boolean | undefined;
  onChange: (nextValue: string | boolean) => void;
}) {
  const label = (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <p className="font-medium text-slate-100">{name}</p>
        <p className="mt-1 text-sm text-slate-400">{field.description}</p>
      </div>
      <div className="flex flex-wrap gap-2">
        <Badge variant={field.required ? 'warning' : 'default'}>{field.required ? '必填' : '可选'}</Badge>
        <Badge variant="info">{field.type}</Badge>
      </div>
    </div>
  );

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
      {label}
      <div className="mt-4">
        {field.type === 'boolean' ? (
          <label className="flex items-center gap-3 text-sm text-slate-200">
            <input
              checked={Boolean(value)}
              className="h-4 w-4 rounded border-slate-700 bg-slate-950"
              onChange={(event) => onChange(event.target.checked)}
              type="checkbox"
            />
            <span>{field.default ? '默认开启' : '默认关闭'}</span>
          </label>
        ) : field.enum.length ? (
          <Select value={String(value ?? '')} onChange={(event) => onChange(event.target.value)}>
            <option value="">{field.required ? '请选择' : '保持默认'}</option>
            {field.enum.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </Select>
        ) : field.type === 'array' || field.type === 'object' ? (
          <Textarea
            className="min-h-28 font-mono text-xs"
            onChange={(event) => onChange(event.target.value)}
            placeholder={field.type === 'array' ? '[]' : '{}'}
            value={String(value ?? '')}
          />
        ) : (
          <Input
            onChange={(event) => onChange(event.target.value)}
            placeholder={field.type === 'date' ? 'YYYY-MM-DD (例如: 2024-01-01)' : ''}
            type={field.type === 'integer' || field.type === 'number' ? 'number' : field.type === 'date' ? 'date' : 'text'}
            value={String(value ?? '')}
          />
        )}
      </div>
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
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [previewParams, setPreviewParams] = useState<Record<string, unknown>>({});
  const [submittedSummary, setSubmittedSummary] = useState<WorkflowRunResponse | null>(null);

  const riskSummary = useMemo(() => summarizeWorkflowRisk(workflow), [workflow]);
  const canRunWorkflow = canAccess('operator');

  useEffect(() => {
    setValues(buildWorkflowDefaultValues(schema));
    setErrorMessage(null);
    setConfirmOpen(false);
    setPreviewParams({});
    setSubmittedSummary(null);
  }, [schema, workflow.workflow_id]);

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
      setSubmittedSummary(data);
      setConfirmOpen(false);
      await queryClient.invalidateQueries({ queryKey: ['jobs'] });
      if (data.job?.id) {
        onSubmitted?.(data.job.id);
      }
    },
    onError: (error: unknown) => {
      setSubmittedSummary(null);
      setErrorMessage(getErrorMessage(error));
    },
  });

  const fields = Object.entries(schema?.fields ?? {});

  const submit = () => {
    if (!canRunWorkflow) {
      setErrorMessage('当前身份需要 operator 权限才能提交工作流。');
      return;
    }

    const validation = validateWorkflowValues(schema, values);
    if (validation.errors.length) {
      setErrorMessage(validation.errors.join('；'));
      return;
    }

    setPreviewParams(validation.params);
    setErrorMessage(null);

    if (riskSummary.requiresConfirmation) {
      setConfirmOpen(true);
      return;
    }

    runMutation.mutate({ params: validation.params, confirmed: false });
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
          <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">
            当前工作流没有可编辑参数。
          </div>
        ) : (
          <>
            <div className="grid gap-3">
              {fields.map(([name, field]) => (
                <FieldEditor
                  key={name}
                  name={name}
                  field={field}
                  value={values[name]}
                  onChange={(nextValue) => setValues((current) => ({ ...current, [name]: nextValue }))}
                />
              ))}
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">参数预览</p>
              <pre className="mt-3 max-h-64 overflow-auto text-xs text-slate-200">
                {prettyJson(values)}
              </pre>
            </div>
          </>
        )}

        {errorMessage ? (
          <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
            {errorMessage}
          </div>
        ) : null}

        {submittedSummary ? (
          <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-100">
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
            }}
          >
            重置默认值
          </Button>
        </div>
        {!canRunWorkflow ? (
          <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-100">
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
              <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">工作流</p>
                <p className="mt-2 font-medium text-slate-100">{workflow.title}</p>
                <p className="mt-1 text-sm text-slate-400">{workflow.description}</p>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">风险说明</p>
                <p className="mt-2 font-medium text-slate-100">{workflow.job_definition?.risk ?? 'medium'}</p>
                <p className="mt-1 text-sm text-slate-400">提交后会创建 Job 并进入任务中心。</p>
              </div>
            </div>
            <div>
              <p className="mb-2 text-sm font-medium text-slate-200">参数摘要</p>
              <pre className="max-h-72 overflow-auto rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-xs text-slate-200">
                {prettyJson(previewParams)}
              </pre>
            </div>
          </div>

          <DialogFooter>
            <DialogClose className="rounded-xl border border-slate-700 px-4 py-2 text-sm text-slate-200 transition-colors hover:bg-slate-800">
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
