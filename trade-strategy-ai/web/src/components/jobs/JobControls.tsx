import { Button } from '@/components/ui/button';

type JobControlsProps = {
  status: string;
  canOperate: boolean;
  canPause?: boolean;
  canResume?: boolean;
  canCancel?: boolean;
  canRetry?: boolean;
  isPending?: boolean;
  onPause?: () => void;
  onResume?: () => void;
  onCancel?: () => void;
  onRetry?: () => void;
  className?: string;
};

function shouldShowPause(status: string) {
  return status === 'pending' || status === 'running';
}

function shouldShowResume(status: string) {
  return status === 'paused';
}

function shouldShowRetry(status: string) {
  return status === 'failed';
}

function shouldShowCancel(status: string) {
  return status === 'pending' || status === 'running' || status === 'paused';
}

export function JobControls({
  status,
  canOperate,
  canPause = true,
  canResume = true,
  canCancel = true,
  canRetry = true,
  isPending = false,
  onPause,
  onResume,
  onCancel,
  onRetry,
  className,
}: JobControlsProps) {
  const hasActions =
    (shouldShowPause(status) && canPause) ||
    (shouldShowResume(status) && canResume) ||
    (shouldShowRetry(status) && canRetry) ||
    (shouldShowCancel(status) && canCancel);
  if (!hasActions) {
    return null;
  }
  return (
    <div className={className ? className : 'flex flex-wrap gap-2'}>
      {shouldShowPause(status) && canPause ? (
        <Button variant="secondary" size="sm" onClick={onPause} disabled={!canOperate || isPending || !onPause}>
          暂停
        </Button>
      ) : null}
      {shouldShowResume(status) && canResume ? (
        <Button variant="secondary" size="sm" onClick={onResume} disabled={!canOperate || isPending || !onResume}>
          恢复
        </Button>
      ) : null}
      {shouldShowRetry(status) && canRetry ? (
        <Button variant="secondary" size="sm" onClick={onRetry} disabled={!canOperate || isPending || !onRetry}>
          重试
        </Button>
      ) : null}
      {shouldShowCancel(status) && canCancel ? (
        <Button variant="destructive" size="sm" onClick={onCancel} disabled={!canOperate || isPending || !onCancel}>
          取消
        </Button>
      ) : null}
    </div>
  );
}
