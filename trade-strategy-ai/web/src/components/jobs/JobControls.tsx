import { Button } from '@/components/ui/button';

type JobControlsProps = {
  status: string;
  canOperate: boolean;
  canPause?: boolean;
  canResume?: boolean;
  canCancel?: boolean;
  canRetry?: boolean;
  isPending?: boolean;
  pendingAction?: 'pause' | 'resume' | 'cancel' | 'retry';
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

function renderActionLabel(label: string, isActionPending: boolean) {
  if (!isActionPending) {
    return label;
  }
  return (
    <>
      <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-r-transparent" aria-hidden="true" />
      {label}中
    </>
  );
}

export function JobControls({
  status,
  canOperate,
  canPause = true,
  canResume = true,
  canCancel = true,
  canRetry = true,
  isPending = false,
  pendingAction,
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
          {renderActionLabel('暂停', isPending && pendingAction === 'pause')}
        </Button>
      ) : null}
      {shouldShowResume(status) && canResume ? (
        <Button variant="secondary" size="sm" onClick={onResume} disabled={!canOperate || isPending || !onResume}>
          {renderActionLabel('恢复', isPending && pendingAction === 'resume')}
        </Button>
      ) : null}
      {shouldShowRetry(status) && canRetry ? (
        <Button variant="secondary" size="sm" onClick={onRetry} disabled={!canOperate || isPending || !onRetry}>
          {renderActionLabel('重试', isPending && pendingAction === 'retry')}
        </Button>
      ) : null}
      {shouldShowCancel(status) && canCancel ? (
        <Button variant="destructive" size="sm" onClick={onCancel} disabled={!canOperate || isPending || !onCancel}>
          {renderActionLabel('取消', isPending && pendingAction === 'cancel')}
        </Button>
      ) : null}
    </div>
  );
}
