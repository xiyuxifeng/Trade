import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

type StatusStripProps = {
  title: string;
  description: string;
  path: string;
  className?: string;
};

export function StatusStrip({ title, description, path, className }: StatusStripProps) {
  return (
    <div className={cn('status-strip', className)}>
      <div className="status-strip-left">
        <div>
          <p className="status-strip-title">{title}</p>
          <p className="status-strip-description">{description}</p>
        </div>
      </div>
      <div className="status-strip-right">
        <span>Route</span>
        <code>{path}</code>
      </div>
    </div>
  );
}
