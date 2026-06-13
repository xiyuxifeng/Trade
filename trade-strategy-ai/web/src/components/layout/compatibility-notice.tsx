import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';

import type { LegacyRouteMetadata } from '@/app/route-config';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import type { PageAction } from './business-page-shell';

type CompatibilityNoticeProps = {
  legacy: LegacyRouteMetadata;
  legacyLabel: string;
  continueAction?: PageAction;
  className?: string;
};

const actionClassName =
  'inline-flex items-center justify-center gap-2 rounded-lg border border-slate-200 bg-slate-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400/50';

function renderAction(action: PageAction) {
  if (action.to !== undefined) {
    return (
      <Link className={actionClassName} to={action.to}>
        {action.label}
      </Link>
    );
  }

  return (
    <Button onClick={action.onClick} variant="default">
      {action.label}
    </Button>
  );
}

function LabelValue({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
      <p className="m-0 text-sm font-medium text-slate-900">{label}</p>
      <p className="mt-1 text-sm text-slate-600">{value}</p>
    </div>
  );
}

export function CompatibilityNotice({ legacy, legacyLabel, continueAction, className }: CompatibilityNoticeProps) {
  const retentionExplanation = legacy.retirementRequired
    ? '当前入口继续保留，直到退役条件满足。'
    : '当前入口继续保留，方便已有链接继续可用。';

  return (
    <Card className={cn('border-slate-200/90 bg-white/95', className)}>
      <CardHeader>
        <p className="page-kicker">历史入口</p>
        <CardTitle>{legacyLabel}</CardTitle>
        <CardDescription>{retentionExplanation}</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3">
        <LabelValue
          label="正式入口"
          value={
            <Link className="font-medium text-sky-700 underline decoration-sky-300 underline-offset-4" to={legacy.targetPath}>
              前往正式入口
            </Link>
          }
        />
        <LabelValue label="当前保留说明" value={retentionExplanation} />
        <LabelValue label="保留阶段" value={legacy.retireStage} />
        <LabelValue label="退役条件" value={legacy.retireCondition} />
        {continueAction ? <div className="pt-1">{renderAction(continueAction)}</div> : null}
      </CardContent>
    </Card>
  );
}
