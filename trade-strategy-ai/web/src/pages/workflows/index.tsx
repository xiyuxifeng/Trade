import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Skeleton } from '@/components/ui/skeleton';
import { ApiError } from '@/lib/api/http';
import { listWorkflows, runWorkflow } from '@/lib/api/workflows';
import type { WorkflowDefinition } from '@/types/workflows';
import { PageHeader } from '@/components/layout/page-header';

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return '工作流数据加载失败';
}

function prettyJson(value: unknown) {
  return JSON.stringify(value, null, 2);
}

const DEFAULT_PARAMS: Record<string, Record<string, unknown>> = {
  'run-pre-market': {
    config_path: 'config/app.yaml',
    as_of_date: new Date().toISOString().slice(0, 10),
    force: false,
    export_html: true,
  },
  'run-after-close': {
    config_path: 'config/app.yaml',
    as_of_date: new Date().toISOString().slice(0, 10),
    force: false,
    export_html: true,
  },
  'pipeline-run': {
    config_path: 'config/app.yaml',
    max_articles: 100,
    force: false,
    skip_crawl: false,
    from_step: 'crawl',
    use_db: true,
    new_version: false,
  },
  'pipeline-step': {
    step: 'crawl',
    config_path: 'config/app.yaml',
    max_articles: 100,
    force: false,
    use_db: true,
    new_version: false,
  },
};

function WorkflowCard({
  workflow,
  active,
  onSelect,
}: {
  workflow: WorkflowDefinition;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      className={`text-left ${active ? 'ring-1 ring-sky-400/50' : ''}`}
      onClick={onSelect}
      type="button"
    >
      <Card className="h-full transition-colors hover:border-sky-500/25 hover:bg-slate-900/70">
        <CardHeader>
          <div className="flex items-start justify-between gap-3">
            <div>
              <CardTitle>{workflow.title}</CardTitle>
              <CardDescription>{workflow.description}</CardDescription>
            </div>
            <Badge variant="info">{workflow.job_type}</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-slate-300">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">
            Permissions: {workflow.permissions}
          </p>
          <div className="space-y-2">
            {workflow.steps.map((step) => (
              <div
                className="rounded-xl border border-slate-800 bg-slate-950/60 p-3"
                key={step.step_id}
              >
                <p className="font-medium text-slate-100">{step.title}</p>
                <p className="text-xs text-slate-400">{step.description}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </button>
  );
}

export function WorkflowsPage() {
  const queryClient = useQueryClient();
  const [selectedWorkflowId, setSelectedWorkflowId] = useState('pre-market');
  const [createdBy, setCreatedBy] = useState('web');
  const [paramsText, setParamsText] = useState(prettyJson(DEFAULT_PARAMS['run-pre-market']));
  const [lastResult, setLastResult] = useState<unknown>(null);
  const [inputError, setInputError] = useState<string | null>(null);

  const workflowsQuery = useQuery({
    queryKey: ['workflows'],
    queryFn: listWorkflows,
    staleTime: 15_000,
  });

  const selectedWorkflow = useMemo(
    () => workflowsQuery.data?.items.find((workflow) => workflow.workflow_id === selectedWorkflowId) ?? workflowsQuery.data?.items[0] ?? null,
    [selectedWorkflowId, workflowsQuery.data],
  );

  const runMutation = useMutation({
    mutationFn: async () => {
      const parsed = JSON.parse(paramsText) as Record<string, unknown>;
      return runWorkflow(selectedWorkflowId, {
        params: parsed,
        created_by: createdBy || undefined,
      });
    },
    onSuccess: async (data) => {
      setInputError(null);
      setLastResult(data);
      await queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
    onError: (error: unknown) => {
      setLastResult(null);
      setInputError(getErrorMessage(error));
    },
  });

  return (
    <main className="page-stack">
      <PageHeader
        kicker="Workflows"
        title="Guided operations"
        description="Launch supported workflows without hand-writing CLI arguments."
      />

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(360px,0.8fr)]">
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle>Workflow definitions</CardTitle>
                <CardDescription>Predefined operational flows from the UI BFF.</CardDescription>
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
              </div>
            ) : workflowsQuery.error ? (
              <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
                {getErrorMessage(workflowsQuery.error)}
              </div>
            ) : !workflowsQuery.data?.items.length ? (
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">
                暂无工作流定义。
              </div>
            ) : (
              <div className="grid gap-4">
                {workflowsQuery.data.items.map((workflow) => (
                  <WorkflowCard
                    active={workflow.workflow_id === selectedWorkflowId}
                    key={workflow.workflow_id}
                    onSelect={() => {
                      setSelectedWorkflowId(workflow.workflow_id);
                      setParamsText(prettyJson(DEFAULT_PARAMS[workflow.job_type] ?? {}));
                    }}
                    workflow={workflow}
                  />
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <div className="grid gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Run workflow</CardTitle>
              <CardDescription>Fill in JSON params and dispatch a Job.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4">
              <Input
                placeholder="created_by"
                value={createdBy}
                onChange={(event) => setCreatedBy(event.target.value)}
              />
              <Select
                value={selectedWorkflowId}
                onChange={(event) => {
                  const workflowId = event.target.value;
                  const workflow = workflowsQuery.data?.items.find((item) => item.workflow_id === workflowId);
                  setSelectedWorkflowId(workflowId);
                  setParamsText(prettyJson(DEFAULT_PARAMS[workflow?.job_type ?? ''] ?? {}));
                }}
              >
                {workflowsQuery.data?.items.map((workflow) => (
                  <option key={workflow.workflow_id} value={workflow.workflow_id}>
                    {workflow.title}
                  </option>
                ))}
              </Select>
              <Textarea
                className="min-h-[220px] font-mono text-xs"
                value={paramsText}
                onChange={(event) => setParamsText(event.target.value)}
              />
              {inputError ? (
                <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
                  {inputError}
                </div>
              ) : null}
              <Button onClick={() => runMutation.mutate()} disabled={runMutation.isPending || !selectedWorkflow}>
                {runMutation.isPending ? 'Running' : 'Run workflow'}
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Run summary</CardTitle>
              <CardDescription>Latest workflow execution result.</CardDescription>
            </CardHeader>
            <CardContent>
              {!lastResult ? (
                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">
                  No workflow has been run yet.
                </div>
              ) : (
                <pre className="max-h-[360px] overflow-auto rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-xs text-slate-200">
                  {JSON.stringify(lastResult, null, 2)}
                </pre>
              )}
            </CardContent>
          </Card>
        </div>
      </section>
    </main>
  );
}
