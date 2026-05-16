import { Badge } from '@/components/ui/badge';

const STATUS_META: Record<string, { label: string; variant: 'default' | 'success' | 'warning' | 'destructive' | 'info' }> = {
  validated: { label: '已校验', variant: 'success' },
  success: { label: '成功', variant: 'success' },
  validated_success: { label: '成功', variant: 'success' },
  released: { label: '已发布', variant: 'success' },
  draft: { label: '草稿', variant: 'warning' },
  pending: { label: '等待中', variant: 'warning' },
  running: { label: '运行中', variant: 'info' },
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
