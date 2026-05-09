import type { HTMLAttributes, ReactNode } from 'react';
import { createContext, useContext } from 'react';
import { cn } from '@/lib/utils';

type DialogContextValue = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

const DialogContext = createContext<DialogContextValue | null>(null);

export function Dialog({
  open,
  onOpenChange,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: ReactNode;
}) {
  return <DialogContext.Provider value={{ open, onOpenChange }}>{children}</DialogContext.Provider>;
}

export function DialogTrigger({
  children,
  className,
  ...props
}: HTMLAttributes<HTMLButtonElement>) {
  const context = useContext(DialogContext);
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

export function DialogContent({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  const context = useContext(DialogContext);
  if (!context?.open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-4">
      <div
        className={cn(
          'w-full max-w-lg rounded-2xl border border-slate-700 bg-slate-950 p-6 text-slate-100 shadow-2xl',
          className,
        )}
        {...props}
      >
        {children}
      </div>
    </div>
  );
}

export function DialogHeader({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('mb-4 flex flex-col gap-1.5', className)} {...props} />;
}

export function DialogTitle({ className, ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return <h2 className={cn('text-lg font-semibold', className)} {...props} />;
}

export function DialogDescription({ className, ...props }: HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn('text-sm text-slate-400', className)} {...props} />;
}

export function DialogFooter({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('mt-6 flex justify-end gap-2', className)} {...props} />;
}

export function DialogClose({
  children,
  className,
  ...props
}: HTMLAttributes<HTMLButtonElement>) {
  const context = useContext(DialogContext);
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
