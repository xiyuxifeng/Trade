import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

type SectionCardProps = {
  title: string;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
};

export function SectionCard({ title, description, action, children, className }: SectionCardProps) {
  return (
    <section className={cn('rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm', className)}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-3xl">
          <h2 className="text-xl font-semibold tracking-tight text-slate-950">{title}</h2>
          {description ? <p className="mt-1 text-sm leading-6 text-slate-600">{description}</p> : null}
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </div>
      <div className="mt-6 flex min-h-0 flex-1 flex-col">{children}</div>
    </section>
  );
}
