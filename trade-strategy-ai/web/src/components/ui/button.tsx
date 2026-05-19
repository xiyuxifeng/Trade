import type { ButtonHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

const buttonVariants = {
  default:
    'bg-sky-500 text-white hover:bg-sky-600 focus-visible:ring-sky-400/50 shadow-lg shadow-sky-950/10',
  secondary:
    'bg-slate-100 text-slate-900 hover:bg-slate-200 focus-visible:ring-slate-400/50 border border-slate-200',
  outline:
    'border border-slate-200 bg-transparent text-slate-700 hover:bg-slate-50 focus-visible:ring-slate-400/50',
  ghost: 'bg-transparent text-slate-700 hover:bg-slate-100 focus-visible:ring-slate-400/50',
  destructive:
    'bg-rose-500 text-white hover:bg-rose-600 focus-visible:ring-rose-400/50 shadow-lg shadow-rose-950/10',
};

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: keyof typeof buttonVariants;
  size?: 'sm' | 'md' | 'lg';
};

export function Button({ className, variant = 'default', size = 'md', ...props }: ButtonProps) {
  const sizeClasses = {
    sm: 'h-8 px-3 text-xs',
    md: 'h-10 px-4 text-sm',
    lg: 'h-11 px-5 text-sm',
  };

  return (
    <button
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 disabled:pointer-events-none disabled:opacity-50',
        buttonVariants[variant],
        sizeClasses[size],
        className,
      )}
      {...props}
    />
  );
}
