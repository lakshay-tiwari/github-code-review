"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Code2,
  FolderGit2,
  MessageSquare,
  Network,
  Settings,
  PanelLeftClose,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { ThemeToggle } from "@/components/theme/theme-toggle";

export interface DashboardSidebarProps {
  className?: string;
  showCollapseButton?: boolean;
  onCollapse?: () => void;
  onItemClick?: () => void;
}

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

export function DashboardSidebar({
  className,
  showCollapseButton = false,
  onCollapse,
  onItemClick,
}: DashboardSidebarProps = {}) {
  const pathname = usePathname();

  const defaultClasses =
    "w-64 border-r border-slate-200/80 dark:border-zinc-800 bg-white dark:bg-zinc-950 flex flex-col justify-between p-4 shrink-0 min-h-screen transition-colors";

  return (
    <aside className={className || defaultClasses}>
      <div className="space-y-6">
        {/* Brand */}
        <div className="flex items-center justify-between">
          <Link
            href="/"
            onClick={onItemClick}
            className="flex items-center gap-2.5 px-2 py-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 rounded-md min-w-0 flex-1"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 font-mono font-bold text-white shadow-sm shadow-indigo-600/30 shrink-0">
              <Code2 className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <div className="text-sm font-bold tracking-tight text-slate-900 dark:text-white leading-none truncate">
                Cortex
              </div>
              <div className="text-[10px] text-slate-500 dark:text-zinc-400 mt-0.5 truncate">
                Codebase RAG
              </div>
            </div>
          </Link>

          {showCollapseButton && onCollapse && (
            <button
              type="button"
              onClick={onCollapse}
              aria-label="Collapse Main Sidebar (Ctrl+B)"
              title="Collapse Main Sidebar (Ctrl+B)"
              className="p-1.5 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-100 dark:text-zinc-400 dark:hover:text-white dark:hover:bg-zinc-900 border border-transparent hover:border-slate-200 dark:hover:border-zinc-800 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 shrink-0 cursor-pointer"
            >
              <PanelLeftClose className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Navigation list */}
        <nav className="space-y-1" aria-label="Dashboard Navigation">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;

            if (item.disabled) {
              return (
                <div
                  key={item.name}
                  className="flex items-center justify-between rounded-lg px-3 py-2 text-xs font-medium text-slate-400 dark:text-zinc-500 opacity-60 cursor-not-allowed select-none"
                  aria-disabled="true"
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className="h-4 w-4" />
                    <span>{item.name}</span>
                  </div>
                  {item.badge && (
                    <span className="text-[10px] font-mono text-slate-500 dark:text-zinc-400 border border-slate-200 dark:border-zinc-800 rounded px-1.5 py-0.5">
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
                onClick={onItemClick}
                className={`flex items-center justify-between rounded-lg px-3 py-2 text-xs font-medium transition-colors ${
                  isActive
                    ? "bg-indigo-50 text-indigo-700 border border-indigo-200/80 dark:bg-indigo-600/10 dark:text-indigo-300 dark:border-indigo-500/20 font-semibold shadow-2xs"
                    : "text-slate-600 dark:text-zinc-400 hover:bg-slate-100 hover:text-slate-900 dark:hover:bg-zinc-900 dark:hover:text-zinc-200"
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

      <div className="space-y-3">
        {/* Theme row */}
        <div className="flex items-center justify-between px-3 py-2 rounded-lg border border-slate-200/80 dark:border-zinc-800 bg-slate-50/70 dark:bg-zinc-900/40 text-xs text-slate-600 dark:text-zinc-400">
          <span className="text-[11px] font-medium">Theme Mode</span>
          <ThemeToggle size="sm" />
        </div>

        {/* Infrastructure indicator */}
        <div className="rounded-lg border border-slate-200/80 dark:border-zinc-800/80 bg-slate-50/80 dark:bg-zinc-900/60 p-3 text-xs transition-colors">
          <div className="flex items-center gap-2 text-slate-800 dark:text-zinc-300 font-medium mb-1">
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
            <span>Local Engine Active</span>
          </div>
          <p className="text-[11px] text-slate-500 dark:text-zinc-400 leading-relaxed">
            FastAPI &amp; Docker stack connected. Ingestion unlocks in Phase 4.
          </p>
        </div>
      </div>
    </aside>
  );
}
