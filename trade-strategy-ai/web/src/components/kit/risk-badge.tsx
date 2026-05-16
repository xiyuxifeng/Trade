import { Badge } from '@/components/ui/badge';

const RISK_META: Record<string, { label: string; variant: 'default' | 'success' | 'warning' | 'destructive' | 'info' }> = {
  low: { label: '低风险', variant: 'success' },
  medium: { label: '中风险', variant: 'warning' },
  high: { label: '高风险', variant: 'destructive' },
  critical: { label: '高风险', variant: 'destructive' },
};

type RiskBadgeProps = {
  value: string;
  label?: string;
};

export function RiskBadge({ value, label }: RiskBadgeProps) {
  const meta = RISK_META[value] ?? { label: value || '未知', variant: 'default' };
  return <Badge variant={meta.variant}>{label ?? meta.label}</Badge>;
}
