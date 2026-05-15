import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import type { JobRecord } from '@/types/jobs';

function statusVariant(status: string) {
  if (status === 'success') return 'success';
  if (status === 'failed' || status === 'cancelled') return 'destructive';
  if (status === 'running') return 'info';
  return 'warning';
}

function getStatusLabel(status: string) {
  const mapping: Record<string, string> = {
    pending: '等待中',
    running: '运行中',
    success: '成功',
    failed: '失败',
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
}: {
  jobs: JobRecord[];
  onViewDetail: (jobId: string) => void;
}) {
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-800">
      <Table>
        <TableHeader className="bg-slate-950/80">
          <TableRow>
            <TableHead>Job ID</TableHead>
            <TableHead>任务类型</TableHead>
            <TableHead>状态</TableHead>
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
                <p className="break-all font-medium text-slate-100">{job.id}</p>
              </TableCell>
              <TableCell>{job.job_type}</TableCell>
              <TableCell>
                <Badge variant={statusVariant(job.status)}>{getStatusLabel(job.status)}</Badge>
              </TableCell>
              <TableCell>{job.created_by}</TableCell>
              <TableCell>{formatTimestamp(job.created_at)}</TableCell>
              <TableCell>{formatTimestamp(job.started_at)}</TableCell>
              <TableCell>{formatTimestamp(job.finished_at)}</TableCell>
              <TableCell>{job.retry_count}</TableCell>
              <TableCell>
                <Button variant="outline" size="sm" onClick={() => onViewDetail(job.id)}>
                  查看详情
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
