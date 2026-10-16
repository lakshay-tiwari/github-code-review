"use client";

import React, { useState } from "react";
import { FolderGit2, AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { AddRepoDialog } from "@/components/dashboard/add-repo-dialog";

interface RepoListProps {
  initialLoading?: boolean;
}

export function RepoList({ initialLoading = false }: RepoListProps) {
  const [isLoading] = useState(initialLoading);
  const [hasError, setHasError] = useState(false);

  // In Phase 2, repositories are not yet persisted to database (PostgreSQL tables and Celery worker arrive in Phase 3 & 4)
  const repositories: unknown[] = [];

  if (isLoading) {
    return (
      <div className="space-y-4" aria-label="Loading repositories">
        <div className="flex items-center justify-between">
          <Skeleton className="h-5 w-40" />
          <Skeleton className="h-9 w-32" />
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Skeleton className="h-44 w-full" />
          <Skeleton className="h-44 w-full" />
          <Skeleton className="h-44 w-full" />
        </div>
      </div>
    );
  }

  if (hasError) {
    return (
      <Card className="border-red-900/50 bg-red-950/20 text-center py-12">
        <CardContent className="flex flex-col items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-900/40 text-red-400">
            <AlertTriangle className="h-6 w-6" />
          </div>
          <h3 className="text-base font-semibold text-white">
            Unable to load repositories
          </h3>
          <p className="max-w-md text-xs text-zinc-400">
            An error occurred connecting to the repository store. Please try again.
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setHasError(false)}
            className="mt-2 gap-2"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Retry</span>
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (repositories.length === 0) {
    return (
      <Card className="border-dashed border-zinc-800 bg-zinc-900/30 text-center py-16 px-6">
        <CardContent className="flex flex-col items-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-zinc-800/80 text-zinc-400 mb-4 border border-zinc-700/50">
            <FolderGit2 className="h-7 w-7" />
          </div>

          <h3 className="text-lg font-semibold text-white">
            No repositories indexed yet
          </h3>

          <p className="mt-2 max-w-md text-xs sm:text-sm text-zinc-400 leading-relaxed">
            Connect any public GitHub repository to index its source code, extract
            symbol relations, and enable semantic retrieval.
          </p>

          <div className="mt-6 flex flex-col sm:flex-row items-center gap-3">
            <AddRepoDialog />
          </div>

          <div className="mt-8 rounded-lg border border-zinc-800/80 bg-zinc-950/60 p-3 max-w-md text-left">
            <div className="text-[11px] font-mono text-indigo-400">
              # Phase 2 Foundation State
            </div>
            <p className="text-[11px] text-zinc-400 mt-1">
              Durable PostgreSQL persistence and Alembic migrations will be configured in <strong>Phase 3A</strong>. Background indexing workers will be wired up in <strong>Phase 4</strong>.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return null;
}
