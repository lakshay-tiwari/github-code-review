"use client";

import { useState } from "react";
import { DashboardHeader } from "@/components/dashboard/header";
import { RepoList } from "@/components/dashboard/repo-list";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Database, GitFork, ShieldCheck } from "lucide-react";

export default function DashboardPage() {
  const [activeCount, setActiveCount] = useState<number | null>(null);

  return (
    <>
      <DashboardHeader
        title="Repositories"
        subtitle="Manage and index your public GitHub codebases"
      />

      <main className="flex-1 p-6 lg:p-8 space-y-8 max-w-7xl">
        {/* Metric / Status Cards */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Card className="p-4">
            <CardContent className="p-0 flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-500 dark:text-zinc-400 font-medium">
                  Active Repositories
                </p>
                <p className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
                  {activeCount !== null ? activeCount : "..."}
                </p>
                <p className="text-[11px] text-slate-500 dark:text-zinc-400 mt-0.5">
                  Phase 4 Ingestion Pipeline
                </p>
              </div>
              <div className="h-10 w-10 rounded-lg bg-slate-100 dark:bg-zinc-800 flex items-center justify-center text-slate-600 dark:text-zinc-400">
                <GitFork className="h-5 w-5" />
              </div>
            </CardContent>
          </Card>

          <Card className="p-4">
            <CardContent className="p-0 flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-500 dark:text-zinc-400 font-medium">
                  Vector Store (Qdrant)
                </p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="h-2 w-2 rounded-full bg-emerald-500" />
                  <span className="text-sm font-semibold text-slate-900 dark:text-white">Online</span>
                </div>
                <p className="text-[11px] text-slate-500 dark:text-zinc-400 mt-0.5">
                  Port 6333 / Local Docker
                </p>
              </div>
              <div className="h-10 w-10 rounded-lg bg-cyan-50 border border-cyan-200 text-cyan-600 dark:bg-cyan-950/40 dark:border-cyan-800/40 dark:text-cyan-400 flex items-center justify-center">
                <Database className="h-5 w-5" />
              </div>
            </CardContent>
          </Card>

          <Card className="p-4">
            <CardContent className="p-0 flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-500 dark:text-zinc-400 font-medium">
                  Authentication &amp; Scope
                </p>
                <div className="flex items-center gap-1.5 mt-1">
                  <Badge variant="success" className="text-[11px] py-0 px-2">
                    Clerk Verified
                  </Badge>
                </div>
                <p className="text-[11px] text-slate-500 dark:text-zinc-400 mt-0.5">
                  Server-side token protection
                </p>
              </div>
              <div className="h-10 w-10 rounded-lg bg-indigo-50 border border-indigo-200 text-indigo-600 dark:bg-indigo-950/40 dark:border-indigo-800/40 dark:text-indigo-400 flex items-center justify-center">
                <ShieldCheck className="h-5 w-5" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Repository List Section */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500 dark:text-zinc-400">
              Connected Codebases
            </h2>
          </div>
          <RepoList onCountChange={setActiveCount} />
        </div>
      </main>
    </>
  );
}
