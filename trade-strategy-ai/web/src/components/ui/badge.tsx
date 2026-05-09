import type { HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

const badgeVariants = {
  default: 'bg-slate-800 text-slate-100',
  success: 'bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/30',
  warning: 'bg-amber-500/15 text-amber-300 ring-1 ring-amber-500/30',
  destructive: 'bg-rose-500/15 text-rose-300 ring-1 ring-rose-500/30',
  info: 'bg-sky-500/15 text-sky-300 ring-1 ring-sky-500/30',
};

type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  variant?: keyof typeof badgeVariants;
};

export function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium',
        badgeVariants[variant],
        className,
      )}
      {...props}
    />
  );
}
