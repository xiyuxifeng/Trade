import type { ReactNode } from 'react';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';

type ConfirmDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  confirmDisabled?: boolean;
  onConfirm?: () => void | Promise<void>;
  children?: ReactNode;
};

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = '确认提交',
  cancelLabel = '取消',
  confirmDisabled = false,
  onConfirm,
  children,
}: ConfirmDialogProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const isConfirmDisabled = confirmDisabled || isSubmitting;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent aria-label={title} className="border-slate-200 bg-white text-slate-950" role="dialog">
        <DialogHeader>
          <DialogTitle className="text-slate-950">{title}</DialogTitle>
          <DialogDescription className="text-slate-600">{description}</DialogDescription>
        </DialogHeader>
        {children ? <div className="text-sm leading-6 text-slate-700">{children}</div> : null}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {cancelLabel}
          </Button>
          <Button
            disabled={isConfirmDisabled}
            onClick={async () => {
              if (isConfirmDisabled) {
                return;
              }

              setIsSubmitting(true);
              try {
                await onConfirm?.();
                onOpenChange(false);
              } catch {
                // Keep the dialog open so the caller can surface the error and the user can retry.
              } finally {
                setIsSubmitting(false);
              }
            }}
          >
            {confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
