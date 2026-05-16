import type { ReactNode } from 'react';

type SchemaFormProps = {
  title: string;
  description?: string;
  children?: ReactNode;
};

export function SchemaForm({ title, description, children }: SchemaFormProps) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4">
      <div>
        <h3 className="text-base font-semibold text-slate-950">{title}</h3>
        {description ? <p className="mt-1 text-sm leading-6 text-slate-600">{description}</p> : null}
      </div>
      {children ? <div className="mt-4">{children}</div> : null}
    </section>
  );
}
