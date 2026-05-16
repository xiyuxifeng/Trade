type LoadingStateProps = {
  label: string;
  description?: string;
};

export function LoadingState({ label, description }: LoadingStateProps) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
      <p className="font-medium text-slate-700">{label}</p>
      {description ? <p className="mt-1 leading-6">{description}</p> : null}
    </div>
  );
}
