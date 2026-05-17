import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

type PageHeaderProps = {
  kicker?: string;
  title?: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
};

export function PageHeader({
  kicker,
  title,
  description,
  actionLabel,
  onAction,
  className,
}: PageHeaderProps) {
  return (
    <header className={cn('page-header', className)}>
      <div className="page-header-copy">
        {kicker ? <Badge variant="info">{kicker}</Badge> : null}
        {title ? <h1>{title}</h1> : null}
        {description ? <p>{description}</p> : null}
      </div>
      {actionLabel && onAction ? (
        <Button variant="outline" onClick={onAction}>
          {actionLabel}
        </Button>
      ) : null}
    </header>
  );
}
