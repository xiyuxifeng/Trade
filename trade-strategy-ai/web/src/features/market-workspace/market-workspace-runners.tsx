import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export type MarketWorkspaceRunner = {
  jobType: string;
  title: string;
  description: string;
  badge: string;
};

type MarketWorkspaceRunnersProps = {
  runners: MarketWorkspaceRunner[];
  submittingJobType: string | null;
  onRun: (jobType: string) => void;
  kaipanSchedulerControlEnabled?: boolean;
  kaipanSchedulerStarted?: boolean;
  kaipanSchedulerToggling?: boolean;
  onKaipanSchedulerToggle?: () => void;
};

export function MarketWorkspaceRunners({
  runners,
  submittingJobType,
  onRun,
  kaipanSchedulerControlEnabled = false,
  kaipanSchedulerStarted = false,
  kaipanSchedulerToggling = false,
  onKaipanSchedulerToggle,
}: MarketWorkspaceRunnersProps) {
  return (
    <section className="space-y-4">
      <div className="flex items-end justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">运行指定任务</h2>
          <p className="text-sm text-slate-500">手动任务通过 Job Center 提交，不直接调用 provider；调度器由当前后台进程管理。</p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
        {runners.map((runner) => (
          <Card key={runner.jobType} className="border-slate-200 bg-white/90 shadow-sm text-slate-900">
            <CardHeader className="space-y-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <CardTitle className="text-base text-slate-900">{runner.title}</CardTitle>
                  <CardDescription className="mt-1 text-sm text-slate-500">{runner.description}</CardDescription>
                </div>
                <Badge variant="info">{runner.badge}</Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {runner.jobType === 'kaipan-run' ? (
                <p className="rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3 text-xs leading-6 text-slate-500">
                  当前仅保留一个开关按钮。调度时间由配置自动读取，运行中按当前 scheduler 状态切换为停止。
                </p>
              ) : null}
              <div className="flex items-center justify-between gap-3">
                <p className="text-xs text-slate-500">任务类型：{runner.jobType}</p>
                <Button
                  onClick={() => {
                    if (runner.jobType === 'kaipan-run' && kaipanSchedulerControlEnabled) {
                      onKaipanSchedulerToggle?.();
                      return;
                    }
                    onRun(runner.jobType);
                  }}
                  disabled={runner.jobType === 'kaipan-run' && kaipanSchedulerControlEnabled ? kaipanSchedulerToggling : submittingJobType === runner.jobType}
                >
                  {runner.jobType === 'kaipan-run'
                    ? kaipanSchedulerControlEnabled
                      ? kaipanSchedulerToggling
                        ? '处理中'
                        : kaipanSchedulerStarted
                          ? '停止调度器'
                          : '启动调度器'
                      : submittingJobType === runner.jobType
                        ? '提交中'
                        : `运行${runner.title}`
                    : submittingJobType === runner.jobType
                      ? '提交中'
                      : `运行${runner.title}`}
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}
