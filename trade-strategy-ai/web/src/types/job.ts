export type StepTimelineStatus = 'pending' | 'running' | 'success' | 'failed' | 'cancelled' | 'skipped';

export type StepTimelineItem = {
  id: string;
  stepName: string;
  title?: string | null;
  status: StepTimelineStatus;
  startedAt?: string | null;
  finishedAt?: string | null;
  durationMs?: number | null;
  errorSummary?: string | null;
  details?: Record<string, unknown> | string | null;
  metadata?: Record<string, unknown>;
  order?: number | null;
};
