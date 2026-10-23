"use client";

import Link from "next/link";
import { Show, UserButton } from "@clerk/nextjs";
import { Code2, LayoutDashboard } from "lucide-react";
import { GitHubIcon } from "@/components/icons/github";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme/theme-toggle";

export function Navbar() {
  return (
    <header className="sticky top-0 z-50 border-b border-slate-200/80 dark:border-zinc-800/80 bg-white/80 dark:bg-zinc-950/80 backdrop-blur-md transition-colors">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6 lg:px-8">
        {/* Brand */}
        <Link
          href="/"
          className="flex items-center gap-2.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 rounded-md"
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-tr from-indigo-600 via-indigo-500 to-violet-500 font-mono font-bold text-white shadow-md shadow-indigo-600/20">
            <Code2 className="h-5 w-5" />
          </div>
          <span className="text-lg font-bold tracking-tight text-slate-900 dark:text-white">
            Cortex
          </span>
          <span className="rounded-full border border-indigo-500/30 bg-indigo-50 dark:bg-indigo-500/10 px-2 py-0.5 text-[10px] font-semibold tracking-wide uppercase text-indigo-700 dark:text-indigo-300">
            RAG
          </span>
        </Link>

        {/* Links, Theme Switcher & Auth State */}
        <div className="flex items-center gap-3 sm:gap-4">
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="GitHub Repository"
            className="flex items-center gap-1.5 text-xs text-slate-600 hover:text-slate-900 dark:text-zinc-400 dark:hover:text-zinc-200 transition-colors"
          >
            <GitHubIcon className="h-4 w-4" />
            <span className="hidden sm:inline">GitHub</span>
          </a>

          {/* Theme Switcher */}
          <ThemeToggle size="sm" />

          <Show when="signed-out">
            <Link href="/sign-in">
              <Button variant="ghost" size="sm">
                Sign In
              </Button>
            </Link>
            <Link href="/sign-up">
              <Button variant="primary" size="sm">
                Get Started
              </Button>
            </Link>
          </Show>

          <Show when="signed-in">
            <Link href="/dashboard">
              <Button variant="outline" size="sm" className="gap-2">
                <LayoutDashboard className="h-4 w-4" />
                <span>Dashboard</span>
              </Button>
            </Link>
            <UserButton
              appearance={{
                elements: {
                  avatarBox: "h-8 w-8 ring-1 ring-slate-300 dark:ring-zinc-700",
                },
              }}
            />
          </Show>
        </div>
      </div>
    </header>
  );
}
