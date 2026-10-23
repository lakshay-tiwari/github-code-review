import React from "react";

export function Skeleton({
  className = "",
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`animate-pulse rounded-md bg-slate-200 dark:bg-zinc-800/60 motion-reduce:animate-none ${className}`}
      {...props}
    />
  );
}
