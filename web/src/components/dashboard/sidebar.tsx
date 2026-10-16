"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Code2,
  FolderGit2,
  MessageSquare,
  Network,
  Settings,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
  disabled?: boolean;
}

const navItems: NavItem[] = [
  {
    name: "Repositories",
    href: "/dashboard",
    icon: FolderGit2,
  },
  {
    name: "Code Chat",
    href: "/dashboard/chat",
    icon: MessageSquare,
    badge: "Phase 6",
  },
  {
    name: "Graph Explorer",
    href: "/dashboard/graph",
    icon: Network,
    badge: "Phase 7",
    disabled: true,
  },
  {
    name: "Settings",
    href: "/dashboard/settings",
    icon: Settings,
    badge: "Planned",
    disabled: true,
  },
];

export function DashboardSidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 border-r border-zinc-800 bg-zinc-950 flex flex-col justify-between p-4 shrink-0 min-h-screen">
      <div className="space-y-6">
        {/* Brand */}
        <Link
          href="/"
          className="flex items-center gap-2.5 px-2 py-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 rounded-md"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 font-mono font-bold text-white shadow-sm shadow-indigo-600/30">
            <Code2 className="h-4 w-4" />
          </div>
          <div>
            <div className="text-sm font-bold tracking-tight text-white leading-none">
              Cortex
            </div>
            <div className="text-[10px] text-zinc-400 mt-0.5">Codebase RAG</div>
          </div>
        </Link>

        {/* Navigation list */}
        <nav className="space-y-1" aria-label="Dashboard Navigation">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;

            if (item.disabled) {
              return (
                <div
                  key={item.name}
                  className="flex items-center justify-between rounded-lg px-3 py-2 text-xs font-medium text-zinc-400 opacity-60 cursor-not-allowed select-none"
                  aria-disabled="true"
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className="h-4 w-4" />
                    <span>{item.name}</span>
                  </div>
                  {item.badge && (
                    <span className="text-[10px] font-mono text-zinc-400 border border-zinc-800 rounded px-1.5 py-0.2">
                      {item.badge}
                    </span>
                  )}
                </div>
              );
            }

            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center justify-between rounded-lg px-3 py-2 text-xs font-medium transition-colors ${
                  isActive
                    ? "bg-indigo-600/10 text-indigo-300 border border-indigo-500/20"
                    : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Icon className="h-4 w-4" />
                  <span>{item.name}</span>
                </div>
                {item.badge && (
                  <Badge variant="indigo" className="text-[10px] py-0 px-1.5">
                    {item.badge}
                  </Badge>
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Infrastructure indicator */}
      <div className="rounded-lg border border-zinc-800/80 bg-zinc-900/60 p-3 text-xs">
        <div className="flex items-center gap-2 text-zinc-300 font-medium mb-1">
          <span className="h-2 w-2 rounded-full bg-emerald-400" />
          <span>Local Engine Active</span>
        </div>
        <p className="text-[11px] text-zinc-400 leading-relaxed">
          FastAPI &amp; Docker stack connected. Ingestion unlocks in Phase 4.
        </p>
      </div>
    </aside>
  );
}
