import { cn } from '@/lib/utils';

type StatusStripProps = {
  title: string;
  description: string;
  path: string;
  kind?: 'canonical' | 'compat';
  className?: string;
};

export function StatusStrip({ title, description, kind = 'canonical', className }: StatusStripProps) {
  return (
    <div className={cn('status-strip', className)}>
      <div className="status-strip-left">
        <div>
          <p className="status-strip-title">{title}</p>
          <p className="status-strip-description">{description}</p>
        </div>
      </div>
      <div className="status-strip-right">
        <span>{kind === 'compat' ? '历史入口' : '正式入口'}</span>
        <span>{kind === 'compat' ? '该入口仅用于兼容已有链接' : '当前功能'}</span>
      </div>
    </div>
  );
}
