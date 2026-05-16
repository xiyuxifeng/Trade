type LogViewerProps = {
  lines: string[];
  emptyLabel?: string;
};

export function LogViewer({ lines, emptyLabel = '暂无日志。' }: LogViewerProps) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">日志</p>
      <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap break-words rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs leading-6 text-slate-700">
        {lines.length ? lines.join('\n') : emptyLabel}
      </pre>
    </div>
  );
}
