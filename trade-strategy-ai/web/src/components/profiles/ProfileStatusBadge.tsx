import { Badge } from '@/components/ui/badge';
import type { ProfileValidationStatus } from '@/types/profile';

const STATUS_META: Record<string, { label: string; variant: 'default' | 'success' | 'warning' | 'destructive' | 'info' }> = {
  draft: { label: '草稿', variant: 'warning' },
  validated: { label: '已校验', variant: 'success' },
  invalid_config: { label: '校验失败', variant: 'destructive' },
  archived: { label: '已归档', variant: 'default' },
};

export function ProfileStatusBadge({ status }: { status: ProfileValidationStatus }) {
  const meta = STATUS_META[status] ?? { label: status || '未知', variant: 'default' };
  return <Badge variant={meta.variant}>{meta.label}</Badge>;
}
