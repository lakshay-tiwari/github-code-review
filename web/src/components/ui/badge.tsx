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
    default: "bg-zinc-800 text-zinc-300 border-zinc-700",
    secondary: "bg-zinc-800/80 text-zinc-300 border-zinc-700/80",
    success: "bg-emerald-950/60 text-emerald-300 border-emerald-800/60",
    warning: "bg-amber-950/60 text-amber-300 border-amber-800/60",
    destructive: "bg-red-950/60 text-red-300 border-red-800/60",
    indigo: "bg-indigo-950/60 text-indigo-300 border-indigo-800/60",
    outline: "bg-transparent text-zinc-400 border-zinc-800",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${variantStyles[variant]} ${className}`}
      {...props}
    >
      {children}
    </span>
  );
}
