import { useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { ArrowLeft, Plus } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { PageHeader } from '@/components/layout/page-header';
import { ErrorState } from '@/components/state/ErrorState';
import { LoadingState, SectionCard } from '@/components/kit';
import { useAuth } from '@/features/auth/auth-context';
import { buildErrorRecoveryState } from '@/lib/error-recovery';
import { createJob, listJobDefinitions, validateJobSubmission } from '@/lib/api/jobs';
import type { JobDefinitionSummary } from '@/types/jobs';

type ParamField = {
  type?: string;
  description?: string;
  required?: boolean;
  default?: unknown;
  enum?: string[];
};

function fieldsFor(definition: JobDefinitionSummary | null): Record<string, ParamField> {
  const schema = definition?.param_schema as { fields?: Record<string, ParamField> } | undefined;
  return schema?.fields ?? {};
}

function parseFieldValue(field: ParamField, raw: string): unknown {
  if (raw.trim() === '') return undefined;
  if (field.type === 'integer') return Number.parseInt(raw, 10);
  if (field.type === 'number') return Number.parseFloat(raw);
  if (field.type === 'boolean') return raw === 'true';
  if (field.type === 'object' || field.type === 'array') return JSON.parse(raw);
  return raw;
}

function defaultValueFor(field: ParamField): string {
  if (field.default === undefined || field.default === null) return '';
  if (typeof field.default === 'object') return JSON.stringify(field.default);
  return String(field.default);
}

function riskLabel(risk: string) {
  if (risk === 'critical') return '极高风险';
  if (risk === 'high') return '高风险';
  if (risk === 'medium') return '中风险';
  return '低风险';
}

export function JobNewPage() {
  const navigate = useNavigate();
  const { canAccess, principal } = useAuth();
  const canCreate = canAccess('operator');
  const [selectedType, setSelectedType] = useState('');
  const [values, setValues] = useState<Record<string, string>>({});
  const [confirmed, setConfirmed] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const definitionsQuery = useQuery({
    queryKey: ['job-definitions'],
    queryFn: listJobDefinitions,
    enabled: canCreate,
    staleTime: 60_000,
  });

  const creatableDefinitions = useMemo(
    () => (definitionsQuery.data ?? []).filter((definition) => definition.runnable),
    [definitionsQuery.data],
  );
  const selectedDefinition = creatableDefinitions.find((definition) => definition.job_type === selectedType) ?? null;
  const fields = fieldsFor(selectedDefinition);

  const validateMutation = useMutation({
    mutationFn: validateJobSubmission,
  });

  const createMutation = useMutation({
    mutationFn: createJob,
    onSuccess: (payload) => {
      if (payload.job?.id) {
        navigate(`/system/jobs/${encodeURIComponent(payload.job.id)}`);
      }
    },
    onError: (error) => {
      setFormError(error instanceof Error ? error.message : '创建任务失败。');
    },
  });

  function buildParams() {
    const params: Record<string, unknown> = {};
    for (const [name, field] of Object.entries(fields)) {
      const value = parseFieldValue(field, values[name] ?? defaultValueFor(field));
      if (value !== undefined) {
        params[name] = value;
      }
    }
    return params;
  }

  async function submit() {
    setFormError(null);
    if (!selectedDefinition) {
      setFormError('请选择任务类型。');
      return;
    }
    if (selectedDefinition.requires_confirmation && !confirmed) {
      setFormError('该任务风险较高，需要先确认影响范围。');
      return;
    }
    let params: Record<string, unknown>;
    try {
      params = buildParams();
    } catch (error) {
      setFormError(error instanceof Error ? `参数格式不正确：${error.message}` : '参数格式不正确。');
      return;
    }
    const request = {
      job_type: selectedDefinition.job_type,
      params,
      created_by: principal.api_key_label ?? principal.role,
      confirmed,
    };
    try {
      const validated = await validateMutation.mutateAsync(request);
      createMutation.mutate({ ...request, params: validated.params });
    } catch (error) {
      setFormError(error instanceof Error ? error.message : '参数校验失败。');
    }
  }

  if (!canCreate) {
    return (
      <main className="page-stack">
        <PageHeader kicker="系统任务" title="新建任务" description="集中创建需要后台执行的系统任务。" />
        <section className="page-card">
          <p className="text-lg font-semibold text-slate-900">没有权限创建任务</p>
          <p className="mt-2 text-sm text-slate-600">当前身份为 {principal.role}，新建任务至少需要 operator 权限。</p>
        </section>
      </main>
    );
  }

  return (
    <main className="page-stack">
      <PageHeader kicker="系统任务" title="新建任务" description="面向操作员和管理员的高级任务创建入口。" />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <Button variant="outline" onClick={() => navigate('/system/jobs')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          返回任务管理
        </Button>
      </div>

      {definitionsQuery.isLoading ? (
        <LoadingState label="正在加载任务类型" description="正在读取已注册任务定义和参数要求。" />
      ) : definitionsQuery.error ? (
        <ErrorState
          {...buildErrorRecoveryState(definitionsQuery.error, 'jobs')}
          onRetry={() => {
            void definitionsQuery.refetch();
          }}
        />
      ) : (
        <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
          <SectionCard title="选择任务类型" description="普通业务入口会自动创建任务；这里只用于高级运维创建。">
            <div className="space-y-4">
              <Select
                aria-label="选择任务类型"
                value={selectedType}
                onChange={(event) => {
                  const next = event.target.value;
                  setSelectedType(next);
                  const definition = creatableDefinitions.find((item) => item.job_type === next);
                  setValues(
                    Object.fromEntries(
                      Object.entries(fieldsFor(definition ?? null)).map(([name, field]) => [name, defaultValueFor(field)]),
                    ),
                  );
                  setConfirmed(false);
                  setFormError(null);
                }}
              >
                <option value="">请选择</option>
                {creatableDefinitions.map((definition) => (
                  <option key={definition.job_type} value={definition.job_type}>
                    {definition.title}
                  </option>
                ))}
              </Select>

              {selectedDefinition ? (
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-600">
                  <p className="font-medium text-slate-950">{selectedDefinition.title}</p>
                  <p className="mt-1">{selectedDefinition.description}</p>
                  <p className="mt-2">风险级别：{riskLabel(selectedDefinition.risk)}</p>
                </div>
              ) : null}
            </div>
          </SectionCard>

          <SectionCard title="参数" description="按任务定义填写必要参数；对象和数组使用 JSON。">
            {!selectedDefinition ? (
              <p className="text-sm text-slate-600">请先选择任务类型。</p>
            ) : (
              <div className="space-y-4">
                {Object.entries(fields).map(([name, field]) => (
                  <label key={name} className="block space-y-1">
                    <span className="text-sm font-medium text-slate-900">
                      {field.description || name}
                      {field.required ? <span className="text-rose-600"> *</span> : null}
                    </span>
                    {field.type === 'boolean' ? (
                      <Select
                        value={values[name] ?? defaultValueFor(field)}
                        onChange={(event) => setValues((current) => ({ ...current, [name]: event.target.value }))}
                      >
                        <option value="">未设置</option>
                        <option value="true">是</option>
                        <option value="false">否</option>
                      </Select>
                    ) : field.enum?.length ? (
                      <Select
                        value={values[name] ?? defaultValueFor(field)}
                        onChange={(event) => setValues((current) => ({ ...current, [name]: event.target.value }))}
                      >
                        <option value="">未设置</option>
                        {field.enum.map((item) => (
                          <option key={item} value={item}>
                            {item}
                          </option>
                        ))}
                      </Select>
                    ) : (
                      <Input
                        value={values[name] ?? defaultValueFor(field)}
                        placeholder={name}
                        onChange={(event) => setValues((current) => ({ ...current, [name]: event.target.value }))}
                      />
                    )}
                  </label>
                ))}
                {selectedDefinition.requires_confirmation ? (
                  <label className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                    <input
                      className="mt-1"
                      type="checkbox"
                      checked={confirmed}
                      onChange={(event) => setConfirmed(event.target.checked)}
                    />
                    <span>我已确认该任务的影响范围，允许系统创建此高风险任务。</span>
                  </label>
                ) : null}
                {formError ? <p className="text-sm text-rose-700">{formError}</p> : null}
                <Button onClick={() => void submit()} disabled={createMutation.isPending || validateMutation.isPending}>
                  <Plus className="mr-2 h-4 w-4" />
                  {createMutation.isPending || validateMutation.isPending ? '创建中' : '创建任务'}
                </Button>
              </div>
            )}
          </SectionCard>
        </section>
      )}
    </main>
  );
}
