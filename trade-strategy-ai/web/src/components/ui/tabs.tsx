import type { HTMLAttributes } from 'react';
import { createContext, useContext, useMemo, useState } from 'react';
import { cn } from '@/lib/utils';

type TabsContextValue = {
  value: string;
  setValue: (value: string) => void;
};

const TabsContext = createContext<TabsContextValue | null>(null);

export function Tabs({
  value: controlledValue,
  defaultValue,
  onValueChange,
  children,
  className,
}: HTMLAttributes<HTMLDivElement> & {
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
}) {
  const [uncontrolledValue, setUncontrolledValue] = useState(defaultValue ?? '');
  const value = controlledValue ?? uncontrolledValue;

  const contextValue = useMemo<TabsContextValue>(
    () => ({
      value,
      setValue: (nextValue) => {
        setUncontrolledValue(nextValue);
        onValueChange?.(nextValue);
      },
    }),
    [onValueChange, value],
  );

  return (
    <TabsContext.Provider value={contextValue}>
      <div className={className}>{children}</div>
    </TabsContext.Provider>
  );
}

export function TabsList({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('inline-flex rounded-lg bg-slate-100 p-1', className)} {...props} />;
}

export function TabsTrigger({
  className,
  value,
  ...props
}: HTMLAttributes<HTMLButtonElement> & { value: string }) {
  const context = useContext(TabsContext);
  const active = context?.value === value;

  return (
    <button
      className={cn(
        'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
        active ? 'bg-sky-500 text-white' : 'text-slate-700 hover:bg-slate-200 hover:text-slate-950',
        className,
      )}
      onClick={() => context?.setValue(value)}
      type="button"
      {...props}
    />
  );
}

export function TabsContent({
  className,
  value,
  ...props
}: HTMLAttributes<HTMLDivElement> & { value: string }) {
  const context = useContext(TabsContext);
  if (context?.value !== value) {
    return null;
  }

  return <div className={cn('mt-4', className)} {...props} />;
}
