"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  FolderGit2,
  AlertTriangle,
  RefreshCw,
  GitBranch,
  GitCommit,
  Clock,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  MessageSquare,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { AddRepoDialog } from "@/components/dashboard/add-repo-dialog";

export interface RepositoryItem {
  id: string;
  owner_id: string;
  github_url: string;
  owner: string;
  name: string;
  default_branch: string;
  latest_commit_sha?: string | null;
  status: "pending" | "indexing" | "ready" | "failed";
  error_message?: string | null;
  created_at: string;
  updated_at: string;
  latest_job?: {
    id: string;
    status: string;
    progress: number;
    current_step?: string | null;
  } | null;
}

interface RepoListProps {
  initialLoading?: boolean;
  onCountChange?: (count: number) => void;
}

export function RepoList({
  initialLoading = true,
  onCountChange,
}: RepoListProps) {
  const [repositories, setRepositories] = useState<RepositoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(initialLoading);
  const [hasError, setHasError] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fetchRepositories = useCallback(async (isManualRefresh = false) => {
    if (isManualRefresh) setIsRefreshing(true);
    try {
      const res = await fetch("/api/repositories", { cache: "no-store" });
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        setErrorMessage(
          errorData.detail || errorData.error || "An error occurred connecting to the repository store."
        );
        setHasError(true);
        return;
      }
      const data = await res.json();
      const items: RepositoryItem[] = data.repositories || data.items || [];
      setRepositories(items);
      onCountChange?.(items.length);
      setHasError(false);
      setErrorMessage(null);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to connect to backend");
      setHasError(true);
    } finally {
      setIsLoading(false);
      if (isManualRefresh) setIsRefreshing(false);
    }
  }, [onCountChange]);

  useEffect(() => {
    fetchRepositories();
  }, [fetchRepositories]);

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
      <Card className="border-red-900/50 bg-red-950/20 text-center py-12 px-6">
        <CardContent className="flex flex-col items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-900/40 text-red-400">
            <AlertTriangle className="h-6 w-6" />
          </div>
          <h3 className="text-base font-semibold text-white">
            Unable to load repositories
          </h3>
          <p className="max-w-md text-xs text-zinc-400">
            {errorMessage || "An error occurred connecting to the repository store. Please try again."}
          </p>
          <div className="mt-2 flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setIsLoading(true);
                setHasError(false);
                fetchRepositories();
              }}
              className="gap-2"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              <span>Retry</span>
            </Button>
            <AddRepoDialog onSuccess={() => fetchRepositories(false)} />
          </div>
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
            Submit any public GitHub repository. Cortex will validate its structure,
            extract code symbols, and dispatch background ingestion jobs.
          </p>

          <div className="mt-6 flex flex-col sm:flex-row items-center gap-3">
            <AddRepoDialog onSuccess={() => fetchRepositories(false)} />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-medium text-zinc-300">
            Connected Repositories ({repositories.length})
          </h2>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => fetchRepositories(true)}
            className="h-7 w-7 p-0 text-zinc-400 hover:text-white"
            title="Refresh repository list"
          >
            <RefreshCw
              className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin" : ""}`}
            />
          </Button>
        </div>
        <AddRepoDialog onSuccess={() => fetchRepositories(false)} />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {repositories.map((repo) => (
          <Card
            key={repo.id}
            className="border-zinc-800 bg-zinc-900/60 hover:border-zinc-700 transition-colors flex flex-col justify-between"
          >
            <CardContent className="p-5 space-y-3.5">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="text-xs text-zinc-400 truncate">{repo.owner}</div>
                  <h3 className="text-sm font-semibold text-white truncate flex items-center gap-1.5">
                    <span>{repo.name}</span>
                    <a
                      href={repo.github_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-zinc-500 hover:text-zinc-300 transition-colors"
                      title="Open on GitHub"
                    >
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  </h3>
                </div>

                {repo.status === "ready" && (
                  <div className="flex items-center gap-1.5">
                    <Badge variant="success" className="gap-1 text-[10px]">
                      <CheckCircle2 className="h-2.5 w-2.5" />
                      <span>Ready</span>
                    </Badge>
                    <Link
                      href={`/dashboard/chat?repo_id=${repo.id}`}
                      className="inline-flex items-center gap-1 text-[10px] font-medium text-indigo-400 hover:text-indigo-300 transition-colors bg-indigo-950/40 hover:bg-indigo-900/50 border border-indigo-800/40 px-2 py-0.5 rounded-md"
                    >
                      <MessageSquare className="h-2.5 w-2.5" />
                      <span>Chat</span>
                    </Link>
                  </div>
                )}
                {repo.status === "indexing" && (
                  <Badge variant="warning" className="gap-1 text-[10px]">
                    <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-ping" />
                    <span>Indexing</span>
                  </Badge>
                )}
                {repo.status === "pending" && (
                  <Badge variant="secondary" className="gap-1 text-[10px]">
                    <Clock className="h-2.5 w-2.5" />
                    <span>Queued</span>
                  </Badge>
                )}
                {repo.status === "failed" && (
                  <Badge variant="destructive" className="gap-1 text-[10px]">
                    <AlertCircle className="h-2.5 w-2.5" />
                    <span>Failed</span>
                  </Badge>
                )}
              </div>

              {/* Branch and commit info */}
              <div className="flex items-center gap-3 text-xs text-zinc-400">
                <div className="flex items-center gap-1">
                  <GitBranch className="h-3.5 w-3.5 text-zinc-500" />
                  <span className="font-mono text-[11px]">
                    {repo.default_branch}
                  </span>
                </div>
                {repo.latest_commit_sha && (
                  <div className="flex items-center gap-1">
                    <GitCommit className="h-3.5 w-3.5 text-zinc-500" />
                    <span className="font-mono text-[11px] text-zinc-300">
                      {repo.latest_commit_sha.slice(0, 7)}
                    </span>
                  </div>
                )}
              </div>

              {/* Progress bar if actively indexing or queued */}
              {(repo.status === "indexing" || repo.status === "pending") &&
                repo.latest_job && (
                  <div className="space-y-1.5 pt-1">
                    <div className="flex justify-between text-[11px] text-zinc-400">
                      <span className="truncate">
                        {repo.latest_job.current_step || "Queueing..."}
                      </span>
                      <span>{repo.latest_job.progress}%</span>
                    </div>
                    <div className="w-full bg-zinc-800 rounded-full h-1.5 overflow-hidden">
                      <div
                        className="bg-indigo-500 h-1.5 rounded-full transition-all duration-500"
                        style={{ width: `${Math.max(5, repo.latest_job.progress)}%` }}
                      />
                    </div>
                  </div>
                )}

              {/* Error display */}
              {repo.status === "failed" && repo.error_message && (
                <div className="rounded border border-red-900/60 bg-red-950/40 p-2 text-[11px] text-red-300">
                  {repo.error_message}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
