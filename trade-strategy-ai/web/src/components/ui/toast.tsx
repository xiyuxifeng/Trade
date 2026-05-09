import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';

type ToastPayload = {
  title: string;
  description?: string;
};

const TOAST_EVENT = 'trade-strategy-ai:toast';

export function toast(payload: ToastPayload) {
  window.dispatchEvent(new CustomEvent(TOAST_EVENT, { detail: payload }));
}

export function Toaster() {
  const [items, setItems] = useState<ToastPayload[]>([]);

  useEffect(() => {
    const handler = (event: Event) => {
      const customEvent = event as CustomEvent<ToastPayload>;
      setItems((current) => [...current.slice(-2), customEvent.detail]);
    };

    window.addEventListener(TOAST_EVENT, handler as EventListener);
    return () => window.removeEventListener(TOAST_EVENT, handler as EventListener);
  }, []);

  if (!items.length) {
    return null;
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 flex w-full max-w-sm flex-col gap-3 px-4">
      {items.map((item, index) => (
        <div
          key={`${item.title}-${index}`}
          className={cn(
            'rounded-xl border border-slate-700 bg-slate-950/95 px-4 py-3 text-sm text-slate-100 shadow-2xl',
          )}
        >
          <p className="font-medium">{item.title}</p>
          {item.description ? <p className="mt-1 text-slate-400">{item.description}</p> : null}
        </div>
      ))}
    </div>
  );
}
