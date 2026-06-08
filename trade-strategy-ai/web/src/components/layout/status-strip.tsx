import { cn } from '@/lib/utils';

type StatusStripProps = {
  title: string;
  description: string;
  path: string;
  kind?: 'canonical' | 'compat';
  className?: string;
};

export function StatusStrip({ title, description, path, kind = 'canonical', className }: StatusStripProps) {
  return (
    <div className={cn('status-strip', className)}>
      <div className="status-strip-left">
        <div>
          <p className="status-strip-title">{title}</p>
          <p className="status-strip-description">{description}</p>
        </div>
      </div>
      <div className="status-strip-right">
        {kind === 'compat' ? <span>兼容访问</span> : <span>Route</span>}
        {kind === 'compat' ? <code>历史链接</code> : <code>{path}</code>}
      </div>
    </div>
  );
}
