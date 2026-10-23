"use client";

import React, { useState } from "react";
import { Plus, X, AlertCircle, CheckCircle, Loader2 } from "lucide-react";
import { GitHubIcon } from "@/components/icons/github";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface AddRepoDialogProps {
  onSuccess?: () => void;
}

interface SubmittedRepo {
  id: string;
  owner: string;
  name: string;
  default_branch: string;
  latest_commit_sha?: string | null;
  status: string;
  latest_job?: {
    id: string;
    status: string;
  } | null;
}

export function AddRepoDialog({ onSuccess }: AddRepoDialogProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [repoUrl, setRepoUrl] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submittedRepo, setSubmittedRepo] = useState<SubmittedRepo | null>(null);

  const validateGitHubUrl = (url: string) => {
    const githubRegex =
      /^https?:\/\/(?:www\.)?github\.com\/[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+(?:\.git)?\/?$/;
    return githubRegex.test(url.trim());
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    const trimmed = repoUrl.trim();
    if (!trimmed) {
      setError("Please provide a GitHub repository URL");
      return;
    }

    if (!validateGitHubUrl(trimmed)) {
      setError(
        "Must be a valid public GitHub URL (e.g. https://github.com/fastapi/fastapi)"
      );
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await fetch("/api/repositories", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ github_url: trimmed }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.detail || data.error || "Failed to submit repository");
        setIsSubmitting(false);
        return;
      }

      setSubmittedRepo(data);
      onSuccess?.();
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : "Network error connecting to Cortex API"
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setIsOpen(false);
    setRepoUrl("");
    setError("");
    setSubmittedRepo(null);
  };

  return (
    <>
      <Button onClick={() => setIsOpen(true)} className="gap-2">
        <Plus className="h-4 w-4" />
        <span>Add Repository</span>
      </Button>

      {isOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="dialog-title"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 dark:bg-black/70 backdrop-blur-xs p-4"
        >
          <div className="relative w-full max-w-lg rounded-xl border border-slate-200/90 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-6 shadow-2xl">
            {/* Close button */}
            <button
              onClick={handleClose}
              aria-label="Close dialog"
              className="absolute right-4 top-4 text-slate-400 hover:text-slate-700 dark:text-zinc-400 dark:hover:text-white transition-colors cursor-pointer"
            >
              <X className="h-5 w-5" />
            </button>

            <div className="flex items-center gap-2 mb-2">
              <GitHubIcon className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
              <h2 id="dialog-title" className="text-base font-semibold text-slate-900 dark:text-white">
                Index Public GitHub Repository
              </h2>
            </div>

            <p className="text-xs text-slate-600 dark:text-zinc-400 mb-6">
              Enter the URL of any public GitHub codebase. Cortex will validate, clone, and dispatch a background indexing job.
            </p>

            {submittedRepo ? (
              <div className="rounded-lg border border-emerald-300 dark:border-emerald-500/30 bg-emerald-50 dark:bg-emerald-950/20 p-4 text-xs">
                <div className="flex items-center gap-2 text-emerald-800 dark:text-emerald-300 font-medium mb-1">
                  <CheckCircle className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                  <span>Repository Submitted &amp; Enqueued</span>
                </div>
                <div className="space-y-1.5 mt-3 text-slate-700 dark:text-zinc-300">
                  <p>
                    Target:{" "}
                    <code className="font-mono text-slate-900 bg-slate-200/80 dark:text-white dark:bg-zinc-950 px-1.5 py-0.5 rounded">
                      {submittedRepo.owner}/{submittedRepo.name}
                    </code>
                  </p>
                  <p>
                    Branch:{" "}
                    <span className="text-slate-500 dark:text-zinc-400 font-mono">
                      {submittedRepo.default_branch}
                    </span>
                  </p>
                  {submittedRepo.latest_commit_sha && (
                    <p>
                      Commit:{" "}
                      <span className="text-indigo-600 dark:text-indigo-400 font-mono text-[11px]">
                        {submittedRepo.latest_commit_sha.slice(0, 7)}
                      </span>
                    </p>
                  )}
                  {submittedRepo.latest_job && (
                    <p className="text-[11px] text-slate-500 dark:text-zinc-400 pt-1">
                      Job ID:{" "}
                      <span className="font-mono text-slate-700 dark:text-zinc-300">
                        {submittedRepo.latest_job.id}
                      </span>{" "}
                      ({submittedRepo.latest_job.status})
                    </p>
                  )}
                </div>
                <div className="mt-4 flex justify-end">
                  <Button variant="outline" size="sm" onClick={handleClose}>
                    Done
                  </Button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <Input
                  label="GitHub Repository URL"
                  placeholder="https://github.com/psf/requests"
                  value={repoUrl}
                  disabled={isSubmitting}
                  onChange={(e) => {
                    setRepoUrl(e.target.value);
                    if (error) setError("");
                  }}
                  helperText="Only public repositories with read permissions are supported currently."
                />

                {error && (
                  <div className="flex items-center gap-2 text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/50 p-2.5 rounded-lg">
                    <AlertCircle className="h-4 w-4 shrink-0" />
                    <span>{error}</span>
                  </div>
                )}

                <div className="flex items-center justify-end gap-2 pt-2">
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={handleClose}
                    disabled={isSubmitting}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    disabled={isSubmitting || !repoUrl.trim()}
                    className="gap-2"
                  >
                    {isSubmitting ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        <span>Validating...</span>
                      </>
                    ) : (
                      <span>Submit Codebase</span>
                    )}
                  </Button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </>
  );
}
