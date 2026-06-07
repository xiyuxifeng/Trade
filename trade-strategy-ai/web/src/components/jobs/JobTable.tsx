import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import type { JobDefinitionSummary, JobRecord } from '@/types/jobs';
import { JobProgress } from './JobProgress';
import { JobControls } from './JobControls';

function statusVariant(status: string) {
  if (status === 'success') return 'success';
  if (status === 'failed' || status === 'cancelled') return 'destructive';
  if (status === 'running') return 'info';
  if (status === 'paused') return 'default';
  return 'warning';
}

function getStatusLabel(status: string) {
  const mapping: Record<string, string> = {
    pending: '等待中',
    running: '运行中',
    success: '成功',
    failed: '失败',
    paused: '已暂停',
    cancelled: '已取消',
  };
  return mapping[status] || status;
}

function formatTimestamp(value: string | null) {
  if (!value) return '未记录';
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

export function JobTable({
  jobs,
  onViewDetail,
  canOperate,
  onPause,
  onResume,
  onCancel,
  onRetry,
  jobDefinitionsByType,
}: {
  jobs: JobRecord[];
  onViewDetail: (jobId: string) => void;
  canOperate: boolean;
  jobDefinitionsByType?: Record<string, JobDefinitionSummary>;
  onPause?: (jobId: string) => void;
  onResume?: (jobId: string) => void;
  onCancel?: (jobId: string) => void;
  onRetry?: (jobId: string) => void;
}) {
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <Table>
        <TableHeader className="bg-slate-50">
          <TableRow>
            <TableHead>Job ID</TableHead>
            <TableHead>任务类型</TableHead>
            <TableHead>状态</TableHead>
            <TableHead>步骤进度</TableHead>
            <TableHead>创建者</TableHead>
            <TableHead>创建时间</TableHead>
            <TableHead>开始时间</TableHead>
            <TableHead>结束时间</TableHead>
            <TableHead>重试次数</TableHead>
            <TableHead>操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {jobs.map((job) => (
            <TableRow key={job.id}>
              <TableCell>
                <p className="break-all font-medium text-slate-900">{job.id}</p>
              </TableCell>
              <TableCell>{job.job_type}</TableCell>
              <TableCell>
                <Badge variant={statusVariant(job.status)}>{getStatusLabel(job.status)}</Badge>
              </TableCell>
              <TableCell className="min-w-[220px] align-top">
                {job.progress ? <JobProgress progress={job.progress} compact /> : <span className="text-sm text-slate-400">未记录</span>}
              </TableCell>
              <TableCell>{job.created_by}</TableCell>
              <TableCell>{formatTimestamp(job.created_at)}</TableCell>
              <TableCell>{formatTimestamp(job.started_at)}</TableCell>
              <TableCell>{formatTimestamp(job.finished_at)}</TableCell>
              <TableCell>{job.retry_count}</TableCell>
              <TableCell>
                <div className="flex flex-wrap gap-2">
                  <Button variant="outline" size="sm" onClick={() => onViewDetail(job.id)}>
                    查看详情
                  </Button>
                  <JobControls
                    status={job.status}
                    canOperate={canOperate}
                    canPause={jobDefinitionsByType?.[job.job_type]?.can_pause ?? false}
                    canResume={jobDefinitionsByType?.[job.job_type]?.can_resume ?? false}
                    canCancel={jobDefinitionsByType?.[job.job_type]?.can_cancel ?? false}
                    canRetry={jobDefinitionsByType?.[job.job_type]?.can_retry ?? false}
                    onPause={onPause ? () => onPause(job.id) : undefined}
                    onResume={onResume ? () => onResume(job.id) : undefined}
                    onCancel={onCancel ? () => onCancel(job.id) : undefined}
                    onRetry={onRetry ? () => onRetry(job.id) : undefined}
                    className="flex flex-wrap gap-2"
                  />
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
