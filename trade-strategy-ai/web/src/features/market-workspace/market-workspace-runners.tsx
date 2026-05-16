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
};

export function MarketWorkspaceRunners({ runners, submittingJobType, onRun }: MarketWorkspaceRunnersProps) {
  return (
    <section className="space-y-4">
      <div className="flex items-end justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">运行指定任务</h2>
          <p className="text-sm text-slate-500">所有操作都通过 Job Center 提交，不直接调用 provider。</p>
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
            <CardContent className="flex items-center justify-between gap-3">
              <p className="text-xs text-slate-500">任务类型：{runner.jobType}</p>
              <Button onClick={() => onRun(runner.jobType)} disabled={submittingJobType === runner.jobType}>
                {submittingJobType === runner.jobType ? '提交中' : `运行${runner.title}`}
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}
