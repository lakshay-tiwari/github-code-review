import React from "react";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?:
    | "default"
    | "secondary"
    | "success"
    | "warning"
    | "destructive"
    | "indigo"
    | "outline";
}

export function Badge({
  className = "",
  variant = "default",
  children,
  ...props
}: BadgeProps) {
  const variantStyles = {
    default:
      "bg-slate-100 text-slate-700 border-slate-200 dark:bg-zinc-800 dark:text-zinc-300 dark:border-zinc-700",
    secondary:
      "bg-slate-100/80 text-slate-600 border-slate-200/80 dark:bg-zinc-800/80 dark:text-zinc-300 dark:border-zinc-700/80",
    success:
      "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800/60",
    warning:
      "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-800/60",
    destructive:
      "bg-red-50 text-red-700 border-red-200 dark:bg-red-950/60 dark:text-red-300 dark:border-red-800/60",
    indigo:
      "bg-indigo-50 text-indigo-700 border-indigo-200 dark:bg-indigo-950/60 dark:text-indigo-300 dark:border-indigo-800/60",
    outline:
      "bg-transparent text-slate-600 border-slate-300 dark:text-zinc-400 dark:border-zinc-800",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors ${variantStyles[variant]} ${className}`}
      {...props}
    >
      {children}
    </span>
  );
}
