import type { ButtonHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

const buttonVariants = {
  default:
    'bg-sky-500 text-slate-950 hover:bg-sky-400 focus-visible:ring-sky-400/50 shadow-lg shadow-sky-950/20',
  secondary:
    'bg-slate-800 text-slate-100 hover:bg-slate-700 focus-visible:ring-slate-500/50 border border-slate-700',
  outline:
    'border border-slate-700 bg-transparent text-slate-100 hover:bg-slate-800 focus-visible:ring-slate-500/50',
  ghost: 'bg-transparent text-slate-100 hover:bg-slate-800 focus-visible:ring-slate-500/50',
  destructive:
    'bg-rose-500 text-white hover:bg-rose-400 focus-visible:ring-rose-400/50 shadow-lg shadow-rose-950/20',
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
