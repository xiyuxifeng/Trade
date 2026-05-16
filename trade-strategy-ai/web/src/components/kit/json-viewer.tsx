import { useMemo } from 'react';

type JsonViewerProps = {
  value: unknown;
  title?: string;
};

function stringify(value: unknown) {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export function JsonViewer({ value, title = 'JSON 预览' }: JsonViewerProps) {
  const text = useMemo(() => stringify(value), [value]);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{title}</p>
      <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap break-words rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs leading-6 text-slate-700">
        {text}
      </pre>
    </div>
  );
}
