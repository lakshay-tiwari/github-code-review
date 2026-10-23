"use client";

import { UserButton } from "@clerk/nextjs";
import { Badge } from "@/components/ui/badge";
import { ThemeToggle } from "@/components/theme/theme-toggle";

interface HeaderProps {
  title: string;
  subtitle?: string;
}

export function DashboardHeader({ title, subtitle }: HeaderProps) {
  return (
    <header className="h-16 border-b border-slate-200/80 dark:border-zinc-800 bg-white/80 dark:bg-zinc-950/80 px-6 flex items-center justify-between backdrop-blur-sm sticky top-0 z-40 transition-colors">
      <div>
        <h1 className="text-base font-semibold text-slate-900 dark:text-white tracking-tight">
          {title}
        </h1>
        {subtitle && <p className="text-xs text-slate-500 dark:text-zinc-400">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-3">
        <Badge variant="outline" className="hidden sm:inline-flex">
          V1 Foundation Shell
        </Badge>
        <ThemeToggle size="sm" />
        <UserButton
          appearance={{
            elements: {
              avatarBox: "h-8 w-8 ring-1 ring-slate-300 dark:ring-zinc-700",
            },
          }}
        />
      </div>
    </header>
  );
}
