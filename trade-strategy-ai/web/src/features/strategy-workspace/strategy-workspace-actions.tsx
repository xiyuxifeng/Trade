import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { ConfirmDialog, SectionCard } from '@/components/kit';
import { ErrorState } from '@/components/state/ErrorState';
import { createJob } from '@/lib/api/jobs';
import { getWorkspaceErrorMessage } from './strategy-workspace-utils';

type StrategyActionType = 'strategy-build' | 'run-pre-market' | 'run-after-close';

type StrategyActionConfig = {
  jobType: StrategyActionType;
  label: string;
  confirmTitle: string;
  description: string;
  highlight: string;
};

const STRATEGY_ACTIONS: StrategyActionConfig[] = [
  {
    jobType: 'strategy-build',
    label: '构建策略版本',
    confirmTitle: '确认构建策略版本',
    description: '生成正式策略版本并保留版本链。',
    highlight: '版本',
  },
  {
    jobType: 'run-pre-market',
    label: '盘前运行',
    confirmTitle: '确认盘前运行',
    description: '基于最新 profile snapshot 执行盘前流程。',
    highlight: '盘前',
  },
  {
    jobType: 'run-after-close',
    label: '盘后运行',
    confirmTitle: '确认盘后运行',
    description: '基于最新 profile snapshot 执行盘后流程。',
    highlight: '盘后',
  },
];

function buildStrategyJobParams(
  action: StrategyActionType,
  strategyDate: string,
  traderId: string,
  profileId: string,
  snapshotId: string | null,
) {
  if (action === 'strategy-build') {
    return {
      profile_id: profileId,
      trader_id: traderId,
      strategy_date: strategyDate,
      force: false,
      snapshot_id: snapshotId ?? undefined,
      market_regime_version: 'market-regime-v3',
      selected_by: 'web',
    };
  }

  return {
    profile_id: profileId,
    as_of_date: strategyDate,
    force: false,
  };
}

type StrategyWorkspaceActionsProps = {
  traderId: string;
  strategyDate: string;
  profileId: string;
  snapshotId: string | null;
  disabled?: boolean;
  onSubmitted?: (payload: { jobType: StrategyActionType; jobId: string }) => void;
};

export function StrategyWorkspaceActions({
  traderId,
  strategyDate,
  profileId,
  snapshotId,
  disabled = false,
  onSubmitted,
}: StrategyWorkspaceActionsProps) {
  const queryClient = useQueryClient();
  const [selectedAction, setSelectedAction] = useState<StrategyActionConfig | null>(null);
  const [submissionError, setSubmissionError] = useState<string | null>(null);

  const selectedActionLabel = selectedAction?.label ?? '';
  const canSubmit = Boolean(traderId.trim() && strategyDate && profileId && !disabled);

  const mutation = useMutation({
    mutationFn: async (action: StrategyActionConfig) => {
      return createJob({
        job_type: action.jobType,
        created_by: 'web',
        params: buildStrategyJobParams(action.jobType, strategyDate, traderId.trim(), profileId, snapshotId),
      });
    },
    onSuccess: async (result, action) => {
      setSubmissionError(null);
      setSelectedAction(null);
      onSubmitted?.({ jobType: action.jobType, jobId: result.job.id });
      await queryClient.invalidateQueries({ queryKey: ['strategy-workspace'] });
    },
    onError: (error) => {
      setSubmissionError(getWorkspaceErrorMessage(error, '策略任务提交失败'));
    },
  });

  return (
    <SectionCard
      title="策略提交入口"
      description="所有动作都通过 Job Center 提交，不扩张 CLI 入口。候选版本在下方候选区生成与审核。"
      action={<Badge variant="info" className="w-fit">正式动作</Badge>}
    >
      <div className="space-y-4">
        <div className="grid gap-3">
          {STRATEGY_ACTIONS.map((action) => (
            <button
              key={action.jobType}
              className="rounded-2xl border border-slate-200 bg-white p-4 text-left transition-colors hover:border-sky-200 hover:bg-sky-50/70 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={!canSubmit || mutation.isPending}
              onClick={() => {
                setSubmissionError(null);
                setSelectedAction(action);
              }}
              type="button"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-base font-medium text-slate-950">{action.label}</p>
                  <p className="mt-1 text-sm text-slate-600">{action.description}</p>
                </div>
                <Badge variant="info">{action.highlight}</Badge>
              </div>
            </button>
          ))}
        </div>

        {submissionError ? (
          <ErrorState
            category="job failed"
            title="策略任务提交失败"
            description="提交到 Job Center 时返回了错误。"
            suggestion="请先查看错误详情，再确认是否重新提交。"
            detail={submissionError}
            actions={[
              { label: '查看任务列表', to: '/jobs' },
              { label: '前往配置管理', to: '/profiles' },
            ]}
          />
        ) : null}
      </div>

        <ConfirmDialog
          open={Boolean(selectedAction)}
          onOpenChange={(open) => !open && setSelectedAction(null)}
          title={selectedAction?.confirmTitle ?? '确认策略任务'}
          description="本操作会通过正式 Job 提交到后端，执行后可在 Job Center、Artifact Center 和 Report Center 查看结果。"
          confirmLabel={mutation.isPending ? '提交中' : '确认提交'}
          confirmDisabled={mutation.isPending || !selectedAction || !canSubmit}
          cancelLabel="取消"
          onConfirm={() => {
            if (!selectedAction || !canSubmit) {
              return Promise.resolve();
            }
            return mutation.mutateAsync(selectedAction).then(() => undefined);
          }}
        >
          <p className="text-sm leading-6 text-slate-600">
            确认后会提交 {selectedActionLabel}，不会调用 CLI，也不会在前端计算策略结果。
          </p>
        </ConfirmDialog>
      </SectionCard>
  );
}
