import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ApiError } from '@/lib/api/http';
import { listWorkflows } from '@/lib/api/workflows';
import type { WorkflowDefinition, WorkflowStep } from '@/types/workflows';
import { getWorkflowPrimaryStep } from './workflow-presets';
import { WorkflowParameterForm } from './workflow-parameter-form';

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return '工作流数据加载失败';
}

function workflowRiskVariant(risk: string) {
  if (risk === 'critical' || risk === 'high') return 'destructive';
  if (risk === 'medium') return 'warning';
  return 'success';
}

function getRiskLabel(risk: string) {
  const mapping: Record<string, string> = {
    critical: '严重',
    high: '高风险',
    medium: '中风险',
    low: '低风险',
    info: '信息',
    success: '成功',
    warning: '警示',
    default: '默认',
    destructive: '危险',
  };
  return mapping[risk] || risk;
}

function jobRiskVariant(risk: string) {
  if (risk === 'critical') return 'destructive';
  if (risk === 'high') return 'warning';
  if (risk === 'medium') return 'info';
  return 'success';
}

function WorkflowCatalogCard({
  workflow,
  active,
  onSelect,
}: {
  workflow: WorkflowDefinition;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <button className="text-left" onClick={onSelect} type="button">
      <Card
        className={[
          'h-full cursor-pointer border-slate-200 bg-white transition-all duration-200 hover:-translate-y-0.5 hover:border-sky-300 hover:bg-sky-50/70',
          active ? 'border-sky-300 ring-1 ring-sky-200' : '',
        ].join(' ')}
      >
        <CardHeader>
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <CardTitle className="truncate">{workflow.title}</CardTitle>
              <CardDescription className="mt-1 line-clamp-2">{workflow.description}</CardDescription>
            </div>
            <Badge variant={workflowRiskVariant(workflow.job_definition?.risk ?? 'medium')}>
              {getRiskLabel(workflow.job_type)}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-slate-700">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">权限: {workflow.permissions}</p>
          <p className="text-sm text-slate-600">步骤数 {workflow.steps.length}</p>
          <div className="flex flex-wrap gap-2">
            {workflow.steps.slice(0, 3).map((step) => (
              <Badge key={step.step_id} variant="info">
                {step.title}
              </Badge>
            ))}
            {workflow.steps.length > 3 ? <Badge variant="default">+{workflow.steps.length - 3}</Badge> : null}
          </div>
        </CardContent>
      </Card>
    </button>
  );
}

function WorkflowStepCard({
  step,
  active,
  onSelect,
}: {
  step: WorkflowStep;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <button className="text-left" onClick={onSelect} type="button">
      <Card
        className={[
          'h-full cursor-pointer border-slate-200 bg-white transition-all duration-200 hover:border-sky-300 hover:bg-sky-50/70',
          active ? 'border-sky-300 bg-sky-50/80 ring-1 ring-sky-200' : '',
        ].join(' ')}
      >
        <CardHeader>
          <div className="flex items-start justify-between gap-3">
            <div>
              <CardTitle className="text-base">{step.title}</CardTitle>
              <CardDescription>{step.description}</CardDescription>
            </div>
            <Badge variant={jobRiskVariant(step.risk)}>{getRiskLabel(step.risk)}</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-slate-700">
          <div className="flex flex-wrap gap-2">
            <Badge variant="info">{step.required_job_type}</Badge>
            {step.requires_confirmation ? <Badge variant="warning">需确认</Badge> : <Badge variant="success">可直接运行</Badge>}
          </div>
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">
            参数 {step.parameters.length} 项
          </p>
        </CardContent>
      </Card>
    </button>
  );
}

function ParamFieldList({ step }: { step: WorkflowStep }) {
  const fields = Object.entries(step.param_schema.fields);
  return (
    <div className="grid gap-3">
      {fields.map(([name, field]) => (
        <div className="rounded-2xl border border-slate-200 bg-white p-4" key={name}>
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
          <div className="mt-3 grid gap-2 text-xs text-slate-500">
            {field.default !== undefined ? (
              <p>默认值: {typeof field.default === 'object' ? JSON.stringify(field.default, null, 2) : String(field.default)}</p>
            ) : null}
            {field.enum?.length ? <p>可选值: {field.enum.join(', ')}</p> : null}
          </div>
        </div>
      ))}
    </div>
  );
}

export function WorkflowCenter() {
  const navigate = useNavigate();
  const params = useParams<{ workflowId?: string }>();
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null);

  const workflowsQuery = useQuery({
    queryKey: ['workflows'],
    queryFn: listWorkflows,
    staleTime: 15_000,
  });

  // Legacy workflow entries are hidden here because strategy now uses the sidebar canonical pages.
  const removedWorkflowIds = new Set(['pipeline', 'pre-market', 'after-close', 'strategy']);
  const workflows = (workflowsQuery.data?.items ?? []).filter((workflow) => !removedWorkflowIds.has(workflow.workflow_id));

  const selectedWorkflow = useMemo(() => {
    if (!workflows.length) return null;
    if (params.workflowId) {
      return workflows.find((workflow) => workflow.workflow_id === params.workflowId) ?? null;
    }
    return workflows[0] ?? null;
  }, [params.workflowId, workflows]);

  const workflowNotFound = Boolean(params.workflowId) && !workflowsQuery.isLoading && !workflowsQuery.error && !selectedWorkflow;

  useEffect(() => {
    if (!selectedWorkflow) return;
    const activeStep = selectedWorkflow.steps.find((step) => step.step_id === selectedStepId);
    if (!activeStep) {
      setSelectedStepId(selectedWorkflow.steps[0]?.step_id ?? null);
    }
  }, [selectedStepId, selectedWorkflow]);

  const selectedStep = useMemo(() => {
    if (!selectedWorkflow) return null;
    return selectedWorkflow.steps.find((step) => step.step_id === selectedStepId) ?? selectedWorkflow.steps[0] ?? null;
  }, [selectedStepId, selectedWorkflow]);

  return (
    <main className="page-stack">
      {/* <PageHeader
        kicker="工作流"
        title="引导式操作"
        description="将操作手册流程映射为引导式控制台，提供深度链接、步骤检查和预填运行表单。"
      /> */}

      <section className="grid gap-6 xl:grid-cols-[minmax(320px,0.95fr)_minmax(0,1.4fr)]">
        <Card className="border-slate-200 bg-white">
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle>工作流目录</CardTitle>
                <CardDescription>选择一个引导式流程以查看其步骤及运行入口。</CardDescription>
              </div>
              <Button variant="outline" onClick={() => workflowsQuery.refetch()} disabled={workflowsQuery.isFetching}>
                {workflowsQuery.isFetching ? '刷新中' : '刷新'}
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {workflowsQuery.isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-28 w-full" />
                <Skeleton className="h-28 w-full" />
                <Skeleton className="h-28 w-full" />
              </div>
            ) : workflowsQuery.error ? (
              <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
                {getErrorMessage(workflowsQuery.error)}
              </div>
            ) : !workflows.length ? (
              <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
                暂无工作流定义。
              </div>
            ) : (
              <div className="grid gap-4">
                {workflows.map((workflow) => (
                  <WorkflowCatalogCard
                    active={workflow.workflow_id === selectedWorkflow?.workflow_id}
                    key={workflow.workflow_id}
                    onSelect={() => {
                      setSelectedStepId(workflow.steps[0]?.step_id ?? null);
                      navigate(`/workflows/${workflow.workflow_id}/run`);
                    }}
                    workflow={workflow}
                  />
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <div className="grid gap-6">
          <Card className="border-slate-200 bg-white">
            <CardHeader>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <CardTitle>{selectedWorkflow?.title ?? '工作流详情'}</CardTitle>
                  <CardDescription>
                    {selectedWorkflow?.description ?? '请选择一个工作流以查看其引导内容。'}
                  </CardDescription>
                </div>
                {selectedWorkflow ? <Badge variant="info">{selectedWorkflow.job_type}</Badge> : null}
              </div>
            </CardHeader>
            <CardContent className="space-y-5">
              {workflowNotFound ? (
                <div className="space-y-4">
                  <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                    该工作流已移除或不可用，请返回工作流目录选择其他流程。
                  </div>
                  <Button onClick={() => navigate('/workflows')}>返回工作流目录</Button>
                </div>
              ) : !selectedWorkflow ? (
                <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
                  正在加载工作流定义。
                </div>
              ) : (
                <>
                  <div className="grid gap-3 md:grid-cols-3">
                    <div className="rounded-2xl border border-slate-200 bg-white p-4">
                      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">权限</p>
                      <p className="mt-2 text-sm font-medium text-slate-900">{selectedWorkflow.permissions}</p>
                    </div>
                    <div className="rounded-2xl border border-slate-200 bg-white p-4">
                      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">步骤</p>
                      <p className="mt-2 text-sm font-medium text-slate-900">{selectedWorkflow.steps.length}</p>
                    </div>
                    <div className="rounded-2xl border border-slate-200 bg-white p-4">
                      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">主动作</p>
                      <p className="mt-2 text-sm font-medium text-slate-900">
                        {selectedWorkflow.job_definition?.title ?? selectedWorkflow.job_type}
                      </p>
                    </div>
                  </div>

                  <Tabs defaultValue="overview">
                    <TabsList>
                      <TabsTrigger value="overview">流程总览</TabsTrigger>
                      <TabsTrigger value="steps">步骤详情</TabsTrigger>
                      <TabsTrigger value="run">运行入口</TabsTrigger>
                    </TabsList>

                    <TabsContent value="overview">
                      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.1fr)_minmax(280px,0.9fr)]">
                        <Card className="border-slate-200 bg-white">
                          <CardHeader>
                            <CardTitle>工作流摘要</CardTitle>
                            <CardDescription>在执行前通过此页面检查主要路径。</CardDescription>
                          </CardHeader>
                          <CardContent className="space-y-4 text-sm text-slate-700">
                            <div className="grid gap-3 md:grid-cols-2">
                              <div className="rounded-2xl border border-slate-200 bg-white p-4">
                                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">任务定义</p>
                                <p className="mt-2 font-medium text-slate-900">{selectedWorkflow.job_definition?.title}</p>
                                <p className="mt-1 text-sm text-slate-600">{selectedWorkflow.job_definition?.description}</p>
                              </div>
                              <div className="rounded-2xl border border-slate-200 bg-white p-4">
                                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">风险等级</p>
                                <Badge variant={jobRiskVariant(selectedWorkflow.job_definition?.risk ?? 'medium')} className="mt-2">
                                  {getRiskLabel(selectedWorkflow.job_definition?.risk ?? 'medium')}
                                </Badge>
                                <p className="mt-2 text-sm text-slate-600">
                                  {selectedWorkflow.job_definition?.requires_confirmation
                                    ? '高风险动作会在下一阶段加入更严格的确认流程。'
                                    : '当前工作流可以直接进入预设运行。'}
                                </p>
                              </div>
                            </div>

                            <div className="grid gap-3">
                              <p className="text-sm font-medium text-slate-800">当前主步骤</p>
                              {selectedWorkflow.steps.map((step, index) => (
                                <div
                                  className={[
                                    'rounded-2xl border p-4',
                                    selectedStep?.step_id === step.step_id
                                      ? 'border-sky-300 bg-sky-50'
                                      : 'border-slate-200 bg-white',
                                  ].join(' ')}
                                  key={step.step_id}
                                >
                                  <div className="flex flex-wrap items-center justify-between gap-3">
                                    <div>
                                      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">步骤 {index + 1}</p>
                                      <p className="mt-1 font-medium text-slate-900">{step.title}</p>
                                    </div>
                                    <div className="flex flex-wrap gap-2">
                                      <Badge variant={jobRiskVariant(step.risk)}>{getRiskLabel(step.risk)}</Badge>
                                      {step.requires_confirmation ? (
                                        <Badge variant="warning">需确认</Badge>
                                      ) : (
                                        <Badge variant="success">直接运行</Badge>
                                      )}
                                    </div>
                                  </div>
                                  <p className="mt-2 text-sm text-slate-600">{step.description}</p>
                                </div>
                              ))}
                            </div>
                          </CardContent>
                        </Card>

                        <Card className="border-slate-200 bg-white">
                          <CardHeader>
                            <CardTitle>就绪检查</CardTitle>
                            <CardDescription>为所选工作流准备的负载预览。</CardDescription>
                          </CardHeader>
                          <CardContent className="space-y-4">
                            <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
                              <p className="font-medium text-slate-900">运行前检查</p>
                              <ul className="mt-2 list-disc space-y-1 pl-5 text-slate-600">
                                <li>确认已连接正确的配置路径与项目根目录。</li>
                                <li>确认该工作流的主步骤与当前任务目标一致。</li>
                                <li>预设参数用于快速进入执行入口，详细表单在本页提供。</li>
                              </ul>
                            </div>
                          </CardContent>
                        </Card>
                      </div>
                    </TabsContent>

                    <TabsContent value="steps">
                      <div className="grid gap-4 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
                        <div className="grid gap-3">
                          {selectedWorkflow.steps.map((step) => (
                            <WorkflowStepCard
                              active={selectedStep?.step_id === step.step_id}
                              key={step.step_id}
                              onSelect={() => setSelectedStepId(step.step_id)}
                              step={step}
                            />
                          ))}
                        </div>

                        {selectedStep ? (
                          <Card className="border-slate-200 bg-white">
                            <CardHeader>
                              <div className="flex flex-wrap items-start justify-between gap-3">
                                <div>
                                  <CardTitle>{selectedStep.title}</CardTitle>
                                  <CardDescription>{selectedStep.description}</CardDescription>
                                </div>
                                <Badge variant={jobRiskVariant(selectedStep.risk)}>{getRiskLabel(selectedStep.risk)}</Badge>
                              </div>
                            </CardHeader>
                            <CardContent className="space-y-4">
                              <div className="grid gap-3 md:grid-cols-2">
                                <div className="rounded-2xl border border-slate-200 bg-white p-4">
                                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">任务类型</p>
                                  <p className="mt-2 text-sm font-medium text-slate-900">{selectedStep.required_job_type}</p>
                                </div>
                                <div className="rounded-2xl border border-slate-200 bg-white p-4">
                                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">确认机制</p>
                                  <p className="mt-2 text-sm font-medium text-slate-900">
                                    {selectedStep.requires_confirmation ? '需要二次确认' : '无需额外确认'}
                                  </p>
                                </div>
                              </div>

                              <div>
                                <p className="mb-3 text-sm font-medium text-slate-800">参数结构 (Schema)</p>
                                <ParamFieldList step={selectedStep} />
                              </div>
                            </CardContent>
                          </Card>
                        ) : null}
                      </div>
                    </TabsContent>

                    <TabsContent value="run">
                      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.1fr)_minmax(280px,0.9fr)]">
                        <WorkflowParameterForm
                          onSubmitted={(jobId) => navigate(`/jobs/${encodeURIComponent(jobId)}`)}
                          workflow={selectedWorkflow}
                        />

                        <Card className="border-slate-200 bg-white">
                          <CardHeader>
                            <CardTitle>执行注意事项</CardTitle>
                            <CardDescription>引导式运行清单。</CardDescription>
                          </CardHeader>
                          <CardContent className="space-y-3 text-sm text-slate-700">
                            <div className="rounded-2xl border border-slate-200 bg-white p-4">
                              <p className="font-medium text-slate-900">当前工作流</p>
                              <p className="mt-1 text-slate-600">{selectedWorkflow.title}</p>
                            </div>
                            <div className="rounded-2xl border border-slate-200 bg-white p-4">
                              <p className="font-medium text-slate-900">主步骤</p>
                              <p className="mt-1 text-slate-600">{getWorkflowPrimaryStep(selectedWorkflow)?.title ?? '未定义'}</p>
                            </div>
                            <div className="rounded-2xl border border-slate-200 bg-white p-4">
                              <p className="font-medium text-slate-900">后续阶段</p>
                              <p className="mt-1 text-slate-600">`WEB-S5-004` 会将此处与任务中心 (Job Center) 的详情跳转进行关联。</p>
                            </div>
                          </CardContent>
                        </Card>
                      </div>
                    </TabsContent>
                  </Tabs>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </section>
    </main>
  );
}
