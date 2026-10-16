"use client";

import { UserButton } from "@clerk/nextjs";
import { Badge } from "@/components/ui/badge";

interface HeaderProps {
  title: string;
  subtitle?: string;
}

export function DashboardHeader({ title, subtitle }: HeaderProps) {
  return (
    <header className="h-16 border-b border-zinc-800 bg-zinc-950/80 px-6 flex items-center justify-between backdrop-blur-sm sticky top-0 z-40">
      <div>
        <h1 className="text-base font-semibold text-white tracking-tight">
          {title}
        </h1>
        {subtitle && <p className="text-xs text-zinc-400">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-3">
        <Badge variant="outline" className="hidden sm:inline-flex">
          V1 Foundation Shell
        </Badge>
        <UserButton
          appearance={{
            elements: {
              avatarBox: "h-8 w-8 ring-1 ring-zinc-700",
            },
          }}
        />
      </div>
    </header>
  );
}
