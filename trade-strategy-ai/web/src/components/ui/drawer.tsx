import type { HTMLAttributes, ReactNode } from 'react';
import { createContext, useContext } from 'react';
import { cn } from '@/lib/utils';

type DrawerContextValue = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

const DrawerContext = createContext<DrawerContextValue | null>(null);

export function Drawer({
  open,
  onOpenChange,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: ReactNode;
}) {
  return <DrawerContext.Provider value={{ open, onOpenChange }}>{children}</DrawerContext.Provider>;
}

export function DrawerTrigger({
  children,
  className,
  ...props
}: HTMLAttributes<HTMLButtonElement>) {
  const context = useContext(DrawerContext);
  return (
    <button
      type="button"
      className={className}
      onClick={() => context?.onOpenChange(true)}
      {...props}
    >
      {children}
    </button>
  );
}

export function DrawerContent({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  const context = useContext(DrawerContext);
  if (!context?.open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/70 p-4">
      <div
        className={cn(
          'h-full w-full max-w-md rounded-2xl border border-slate-700 bg-slate-950 p-6 text-slate-100 shadow-2xl',
          className,
        )}
        {...props}
      >
        {children}
      </div>
    </div>
  );
}

export function DrawerHeader({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('mb-4 flex flex-col gap-1.5', className)} {...props} />;
}

export function DrawerTitle({ className, ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return <h2 className={cn('text-lg font-semibold', className)} {...props} />;
}

export function DrawerDescription({ className, ...props }: HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn('text-sm text-slate-400', className)} {...props} />;
}

export function DrawerFooter({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('mt-6 flex justify-end gap-2', className)} {...props} />;
}

export function DrawerClose({
  children,
  className,
  ...props
}: HTMLAttributes<HTMLButtonElement>) {
  const context = useContext(DrawerContext);
  return (
    <button
      type="button"
      className={className}
      onClick={() => context?.onOpenChange(false)}
      {...props}
    >
      {children}
    </button>
  );
}
