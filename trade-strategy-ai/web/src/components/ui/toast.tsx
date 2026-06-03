import { useEffect, useRef, useState } from 'react';
import { cn } from '@/lib/utils';

type ToastPayload = {
  title: string;
  description?: string;
};

type ToastItem = ToastPayload & {
  id: string;
};

const TOAST_EVENT = 'trade-strategy-ai:toast';
const TOAST_DURATION_MS = 5000;

export function toast(payload: ToastPayload) {
  window.dispatchEvent(new CustomEvent(TOAST_EVENT, { detail: payload }));
}

export function Toaster() {
  const [items, setItems] = useState<ToastItem[]>([]);
  const timerIds = useRef<number[]>([]);

  useEffect(() => {
    const handler = (event: Event) => {
      const customEvent = event as CustomEvent<ToastPayload>;
      const id = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`;
      setItems((current) => [...current.slice(-2), { id, ...customEvent.detail }]);

      const timerId = window.setTimeout(() => {
        setItems((current) => current.filter((item) => item.id !== id));
      }, TOAST_DURATION_MS);
      timerIds.current.push(timerId);
    };

    window.addEventListener(TOAST_EVENT, handler as EventListener);
    return () => {
      window.removeEventListener(TOAST_EVENT, handler as EventListener);
      timerIds.current.forEach((timerId) => window.clearTimeout(timerId));
      timerIds.current = [];
    };
  }, []);

  if (!items.length) {
    return null;
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 flex w-full max-w-sm flex-col gap-3 px-4">
      {items.map((item) => (
        <div
          key={item.id}
          className={cn(
            'rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 shadow-2xl',
          )}
        >
          <p className="font-medium">{item.title}</p>
          {item.description ? <p className="mt-1 text-slate-600">{item.description}</p> : null}
        </div>
      ))}
    </div>
  );
}
