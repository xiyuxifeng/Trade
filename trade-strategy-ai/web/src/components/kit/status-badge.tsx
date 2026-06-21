import { Badge } from '@/components/ui/badge';

const STATUS_META: Record<string, { label: string; variant: 'default' | 'success' | 'warning' | 'destructive' | 'info' }> = {
  validated: { label: '已校验', variant: 'success' },
  success: { label: '成功', variant: 'success' },
  validated_success: { label: '成功', variant: 'success' },
  released: { label: '已发布', variant: 'success' },
  ready: { label: '已就绪', variant: 'success' },
  degraded: { label: '可降级继续', variant: 'warning' },
  blocked: { label: '已阻塞', variant: 'destructive' },
  partial: { label: '部分完成', variant: 'warning' },
  unavailable: { label: '当前不可用', variant: 'default' },
  draft: { label: '草稿', variant: 'warning' },
  pending: { label: '等待中', variant: 'warning' },
  running: { label: '运行中', variant: 'info' },
  paused: { label: '已暂停', variant: 'default' },
  failed: { label: '失败', variant: 'destructive' },
  cancelled: { label: '已取消', variant: 'default' },
  archived: { label: '已归档', variant: 'default' },
  invalid_config: { label: '校验失败', variant: 'destructive' },
};

type StatusBadgeProps = {
  value: string;
  label?: string;
};

export function StatusBadge({ value, label }: StatusBadgeProps) {
  const meta = STATUS_META[value] ?? { label: value || '未知', variant: 'default' };
  return <Badge variant={meta.variant}>{label ?? meta.label}</Badge>;
}
