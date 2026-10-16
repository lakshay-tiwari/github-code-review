"use client";

import React, { useState } from "react";
import { Plus, X, AlertCircle, CheckCircle } from "lucide-react";
import { GitHubIcon } from "@/components/icons/github";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function AddRepoDialog() {
  const [isOpen, setIsOpen] = useState(false);
  const [repoUrl, setRepoUrl] = useState("");
  const [error, setError] = useState("");
  const [isSubmitted, setIsSubmitted] = useState(false);

  const validateGitHubUrl = (url: string) => {
    const githubRegex = /^https?:\/\/github\.com\/[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+(\/)?$/;
    return githubRegex.test(url.trim());
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!repoUrl.trim()) {
      setError("Please provide a GitHub repository URL");
      return;
    }

    if (!validateGitHubUrl(repoUrl)) {
      setError("Must be a valid public GitHub URL (e.g. https://github.com/fastapi/fastapi)");
      return;
    }

    setIsSubmitted(true);
  };

  const handleClose = () => {
    setIsOpen(false);
    setRepoUrl("");
    setError("");
    setIsSubmitted(false);
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
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4"
        >
          <div className="relative w-full max-w-lg rounded-xl border border-zinc-800 bg-zinc-900 p-6 shadow-2xl">
            {/* Close button */}
            <button
              onClick={handleClose}
              aria-label="Close dialog"
              className="absolute right-4 top-4 text-zinc-400 hover:text-white transition-colors"
            >
              <X className="h-5 w-5" />
            </button>

            <div className="flex items-center gap-2 mb-2">
              <GitHubIcon className="h-5 w-5 text-indigo-400" />
              <h2 id="dialog-title" className="text-base font-semibold text-white">
                Index Public GitHub Repository
              </h2>
            </div>

            <p className="text-xs text-zinc-400 mb-6">
              Enter the URL of any public GitHub codebase. Cortex will clone, parse with Tree-sitter, and generate vector embeddings.
            </p>

            {isSubmitted ? (
              <div className="rounded-lg border border-indigo-500/30 bg-indigo-500/10 p-4 text-xs">
                <div className="flex items-center gap-2 text-indigo-300 font-medium mb-1">
                  <CheckCircle className="h-4 w-4 text-indigo-400" />
                  <span>Validation Passed — URL Ready</span>
                </div>
                <p className="text-zinc-300 mt-2">
                  Repository: <code className="font-mono text-white bg-zinc-950 px-1.5 py-0.5 rounded">{repoUrl}</code>
                </p>
                <div className="mt-4 rounded border border-amber-800/60 bg-amber-950/40 p-2.5 text-amber-200">
                  <strong>Notice:</strong> Background cloning, Tree-sitter parsing, and Celery indexing jobs will be activated in <strong>Phase 4</strong>.
                </div>
                <div className="mt-4 flex justify-end">
                  <Button variant="outline" size="sm" onClick={handleClose}>
                    Close
                  </Button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <Input
                  label="GitHub Repository URL"
                  placeholder="https://github.com/psf/requests"
                  value={repoUrl}
                  onChange={(e) => {
                    setRepoUrl(e.target.value);
                    if (error) setError("");
                  }}
                  error={error}
                  helperText="Supports public Git repositories only."
                  autoFocus
                />

                <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3 text-xs text-zinc-400 space-y-1">
                  <div className="flex items-center gap-1.5 font-medium text-zinc-300">
                    <AlertCircle className="h-3.5 w-3.5 text-indigo-400" />
                    <span>Security &amp; Pipeline Guardrails</span>
                  </div>
                  <p className="text-[11px] leading-relaxed">
                    No code execution takes place. Binaries and large media files are excluded during indexing.
                  </p>
                </div>

                <div className="flex items-center justify-end gap-3 pt-2">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={handleClose}
                  >
                    Cancel
                  </Button>
                  <Button type="submit" size="sm">
                    Submit Repository
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
