"use client";

import React from "react";
import { Plus, Trash2, MessageSquare, PanelLeftClose } from "lucide-react";

export interface Repository {
  id: string;
  name: string;
  owner: string;
  default_branch: string;
  status: string;
}

export interface Conversation {
  id: string;
  repository_id: string;
  title: string;
  created_at: string;
}

export interface ChatHistorySidebarProps {
  repositories: Repository[];
  selectedRepoId: string;
  onSelectRepo: (repoId: string) => void;
  conversations: Conversation[];
  activeConvId: string;
  onSelectConv: (convId: string) => void;
  onNewConv: () => void;
  onDeleteConv: (convId: string) => void;
  showCollapseButton?: boolean;
  onCollapse?: () => void;
}

export function ChatHistorySidebar({
  repositories,
  selectedRepoId,
  onSelectRepo,
  conversations,
  activeConvId,
  onSelectConv,
  onNewConv,
  onDeleteConv,
  showCollapseButton = false,
  onCollapse,
}: ChatHistorySidebarProps) {
  return (
    <aside className="w-full h-full flex flex-col bg-slate-50/80 dark:bg-zinc-950/80 overflow-hidden select-none transition-colors">
      {/* Active Repo selector */}
      <div className="p-4 border-b border-slate-200/80 dark:border-zinc-800/80 shrink-0">
        <label
          htmlFor="active-repo-select"
          className="text-[10px] font-semibold text-slate-500 dark:text-zinc-500 uppercase tracking-widest block mb-2"
        >
          Active Repository
        </label>
        <select
          id="active-repo-select"
          className="w-full rounded-lg bg-white dark:bg-zinc-900 border border-slate-300 dark:border-zinc-800 px-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 transition-colors appearance-none cursor-pointer"
          value={selectedRepoId}
          onChange={(e) => onSelectRepo(e.target.value)}
        >
          {repositories.length === 0 ? (
            <option value="">No repositories indexed</option>
          ) : (
            repositories.map((repo) => (
              <option key={repo.id} value={repo.id}>
                {repo.owner}/{repo.name}
              </option>
            ))
          )}
        </select>
      </div>

      {/* Conversations header */}
      <div className="flex items-center justify-between px-4 py-3 shrink-0 border-b border-slate-200/60 dark:border-zinc-800/40">
        <span className="text-[10px] font-semibold text-slate-500 dark:text-zinc-500 uppercase tracking-widest">
          Threads
        </span>
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={onNewConv}
            disabled={!selectedRepoId}
            aria-label="New chat thread"
            className="flex items-center gap-1.5 text-[11px] text-slate-600 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-white disabled:opacity-40 transition-colors bg-slate-100 hover:bg-slate-200 dark:bg-zinc-800/60 dark:hover:bg-zinc-700/60 border border-slate-300/80 dark:border-zinc-700/60 rounded-lg px-2.5 py-1 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-indigo-500 cursor-pointer disabled:cursor-not-allowed"
          >
            <Plus className="h-3 w-3" />
            <span>New</span>
          </button>

          {showCollapseButton && onCollapse && (
            <button
              type="button"
              onClick={onCollapse}
              aria-label="Collapse Chat History"
              title="Collapse Chat History"
              className="p-1 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-100 dark:text-zinc-500 dark:hover:text-zinc-200 dark:hover:bg-zinc-900 border border-transparent hover:border-slate-200 dark:hover:border-zinc-800 transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-indigo-500 cursor-pointer"
            >
              <PanelLeftClose className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Conversations list (independent scroll container) */}
      <div className="flex-1 overflow-y-auto px-2 py-2 space-y-0.5 min-h-0">
        {conversations.length === 0 ? (
          <div className="text-center py-8 px-4">
            <MessageSquare className="h-6 w-6 text-slate-300 dark:text-zinc-700 mx-auto mb-2" />
            <p className="text-xs text-slate-500 dark:text-zinc-600">No threads yet. Start a new chat.</p>
          </div>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              role="button"
              tabIndex={0}
              className={`group flex items-center justify-between px-3 py-2.5 rounded-lg text-xs cursor-pointer transition-all ${
                activeConvId === conv.id
                  ? "bg-indigo-50 text-indigo-900 border border-indigo-200 font-medium dark:bg-indigo-600/15 dark:text-indigo-200 dark:border-indigo-500/25 shadow-2xs"
                  : "text-slate-600 dark:text-zinc-400 hover:bg-slate-100/80 hover:text-slate-900 dark:hover:bg-zinc-800/60 dark:hover:text-zinc-200 border border-transparent"
              }`}
              onClick={() => onSelectConv(conv.id)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onSelectConv(conv.id);
                }
              }}
            >
              <div className="flex items-center gap-2 min-w-0">
                <MessageSquare
                  className={`h-3 w-3 shrink-0 ${
                    activeConvId === conv.id ? "text-indigo-600 dark:text-indigo-400" : "text-slate-400 dark:text-zinc-600"
                  }`}
                />
                <span className="truncate">{conv.title}</span>
              </div>
              <button
                type="button"
                className="opacity-0 group-hover:opacity-100 p-1 rounded text-slate-400 hover:text-red-600 dark:hover:text-red-400 transition-all shrink-0 focus:opacity-100 cursor-pointer"
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteConv(conv.id);
                }}
                title="Delete thread"
                aria-label={`Delete thread ${conv.title}`}
              >
                <Trash2 className="h-3 w-3" />
              </button>
            </div>
          ))
        )}
      </div>
    </aside>
  );
}
