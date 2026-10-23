"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { UserButton } from "@clerk/nextjs";
import { Badge } from "@/components/ui/badge";
import { MarkdownRenderer } from "@/components/chat/markdown-renderer";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { createSSEStreamAccumulator } from "@/lib/sse-parser";
import { DashboardSidebar } from "@/components/dashboard/sidebar";
import {
  ChatHistorySidebar,
  Repository,
  Conversation,
} from "@/components/chat/chat-history-sidebar";
import {
  ResizablePanelGroup,
  ResizablePanel,
  ResizableHandle,
} from "@/components/ui/resizable";
import type { ImperativePanelHandle } from "react-resizable-panels";
import {
  Send,
  Loader2,
  FileCode2,
  MessageSquare,
  Sparkles,
  GitBranch,
  FolderGit2,
  AlertCircle,
  Copy,
  Check,
  Terminal,
  PanelLeft,
  Menu,
  X,
} from "lucide-react";

interface Citation {
  file_path: string;
  start_line: number;
  end_line: number;
  commit_sha?: string;
  symbol_name?: string | null;
  snippet?: string | null;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  status: string;
  citations?: Citation[] | null;
  created_at: string;
}

const COLLAPSED_STORAGE_KEY = "cortex_chat_collapsed_v2";

function CitationChip({ cite }: { cite: Citation }) {
  const [copied, setCopied] = useState(false);
  const fileName = cite.file_path.split("/").pop();

  const handleCopy = () => {
    navigator.clipboard.writeText(
      `${cite.file_path}:${cite.start_line}-${cite.end_line}`
    );
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      title={`Click to copy reference: ${cite.file_path}:${cite.start_line}-${cite.end_line}`}
      className="group inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 border border-slate-200/90 hover:border-indigo-500/50 text-[11px] font-mono text-slate-700 dark:bg-zinc-800 dark:hover:bg-zinc-700 dark:border-zinc-700 dark:hover:border-indigo-500/50 dark:text-zinc-200 transition-colors cursor-pointer"
    >
      <FileCode2 className="h-3 w-3 text-indigo-600 dark:text-indigo-400 shrink-0" />
      <span
        className="text-slate-800 dark:text-zinc-200 font-medium truncate max-w-[140px]"
        title={cite.file_path}
      >
        {fileName}
      </span>
      <span className="text-indigo-600 dark:text-indigo-400 font-medium shrink-0">
        :{cite.start_line}-{cite.end_line}
      </span>
      {cite.symbol_name && (
        <span className="text-emerald-600 dark:text-emerald-400 shrink-0 text-[10px]">
          · {cite.symbol_name}
        </span>
      )}
      {copied ? (
        <Check className="h-3 w-3 text-emerald-500 shrink-0" />
      ) : (
        <Copy className="h-2.5 w-2.5 text-slate-400 group-hover:text-slate-600 dark:text-zinc-500 dark:group-hover:text-zinc-300 shrink-0" />
      )}
    </button>
  );
}

function CopyMessageButton({ content }: { content: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
    }
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      aria-label="Copy entire answer as Markdown"
      className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-medium text-slate-500 hover:text-slate-900 hover:bg-slate-200/70 border border-transparent hover:border-slate-300/60 dark:text-zinc-400 dark:hover:text-white dark:hover:bg-zinc-800 dark:border-transparent dark:hover:border-zinc-700/60 transition-colors cursor-pointer"
      title="Copy entire answer as Markdown"
    >
      {copied ? (
        <>
          <Check className="h-3 w-3 text-emerald-500" />
          <span className="text-emerald-600 dark:text-emerald-400">Copied</span>
        </>
      ) : (
        <>
          <Copy className="h-3 w-3" />
          <span>Copy</span>
        </>
      )}
    </button>
  );
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-2 py-3 px-1 text-slate-500 dark:text-zinc-400 text-xs">
      <div className="flex gap-1.5 items-center">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-1.5 w-1.5 rounded-full bg-indigo-600 dark:bg-indigo-400 animate-bounce"
            style={{
              animationDelay: `${i * 150}ms`,
              animationDuration: "900ms",
            }}
          />
        ))}
      </div>
      <span className="text-[11px] text-slate-500 dark:text-zinc-500">
        Searching codebase & formulating technical analysis…
      </span>
    </div>
  );
}

export default function ChatWorkspacePage() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState<string>("");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string>("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputPrompt, setInputPrompt] = useState<string>("");
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [streamingCitations, setStreamingCitations] = useState<Citation[]>([]);
  const [streamingText, setStreamingText] = useState<string>("");
  const [errorMsg, setErrorMsg] = useState<string>("");

  // Responsive state
  const [isMounted, setIsMounted] = useState<boolean>(false);
  const [isMobile, setIsMobile] = useState<boolean>(false);
  const [isMobileMainOpen, setIsMobileMainOpen] = useState<boolean>(false);
  const [isMobileHistoryOpen, setIsMobileHistoryOpen] = useState<boolean>(false);

  // Panel collapse states
  const [isMainCollapsed, setIsMainCollapsed] = useState<boolean>(false);
  const [isHistoryCollapsed, setIsHistoryCollapsed] = useState<boolean>(false);

  // Panel refs for imperative collapse/expand
  const mainPanelRef = useRef<ImperativePanelHandle | null>(null);
  const historyPanelRef = useRef<ImperativePanelHandle | null>(null);

  // Scrolling & composer refs
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const isUserNearBottomRef = useRef<boolean>(true);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  // Screen size listener
  useEffect(() => {
    if (typeof window === "undefined") return;

    const media = window.matchMedia("(max-width: 1023px)");
    setIsMobile(media.matches);

    const handleMediaChange = (e: MediaQueryListEvent) => {
      setIsMobile(e.matches);
      if (!e.matches) {
        setIsMobileMainOpen(false);
        setIsMobileHistoryOpen(false);
      }
    };

    media.addEventListener("change", handleMediaChange);
    return () => media.removeEventListener("change", handleMediaChange);
  }, []);

  // Lock body scroll when mobile drawers are open
  useEffect(() => {
    if (typeof document === "undefined") return;
    if (isMobile && (isMobileMainOpen || isMobileHistoryOpen)) {
      const prev = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = prev;
      };
    }
  }, [isMobile, isMobileMainOpen, isMobileHistoryOpen]);

  // Load persisted collapse state & mark mounted
  useEffect(() => {
    setIsMounted(true);
    try {
      const raw = localStorage.getItem(COLLAPSED_STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed.mainSidebar) {
          setIsMainCollapsed(true);
          setTimeout(() => mainPanelRef.current?.collapse(), 50);
        }
        if (parsed.chatHistory) {
          setIsHistoryCollapsed(true);
          setTimeout(() => historyPanelRef.current?.collapse(), 50);
        }
      }
    } catch {
      // Ignore storage errors
    }
  }, []);

  const saveCollapsedState = useCallback(
    (mainVal: boolean, histVal: boolean) => {
      try {
        localStorage.setItem(
          COLLAPSED_STORAGE_KEY,
          JSON.stringify({ mainSidebar: mainVal, chatHistory: histVal })
        );
      } catch {
        // Ignore storage errors
      }
    },
    []
  );

  // Global keyboard shortcuts (Cmd+B / Ctrl+B to toggle sidebar, Escape to close drawers)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (isMobileMainOpen || isMobileHistoryOpen) {
          setIsMobileMainOpen(false);
          setIsMobileHistoryOpen(false);
        }
      }

      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "b") {
        const target = e.target as HTMLElement | null;
        const isEditable =
          target?.tagName === "INPUT" ||
          target?.tagName === "TEXTAREA" ||
          target?.isContentEditable;

        if (!isEditable) {
          e.preventDefault();
          if (isMobile) {
            setIsMobileMainOpen((prev) => !prev);
          } else {
            const panel = mainPanelRef.current;
            if (panel) {
              if (panel.isCollapsed()) {
                panel.expand();
                setIsMainCollapsed(false);
                saveCollapsedState(false, isHistoryCollapsed);
              } else {
                panel.collapse();
                setIsMainCollapsed(true);
                saveCollapsedState(true, isHistoryCollapsed);
              }
            }
          }
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [
    isMobile,
    isMobileMainOpen,
    isMobileHistoryOpen,
    isHistoryCollapsed,
    saveCollapsedState,
  ]);

  // Toggle handlers for desktop panels
  const handleToggleMainSidebar = useCallback(() => {
    if (isMobile) {
      setIsMobileMainOpen((prev) => !prev);
      return;
    }
    const panel = mainPanelRef.current;
    if (panel) {
      if (panel.isCollapsed()) {
        panel.expand();
        setIsMainCollapsed(false);
        saveCollapsedState(false, isHistoryCollapsed);
      } else {
        panel.collapse();
        setIsMainCollapsed(true);
        saveCollapsedState(true, isHistoryCollapsed);
      }
    }
  }, [isMobile, isHistoryCollapsed, saveCollapsedState]);

  const handleToggleHistorySidebar = useCallback(() => {
    if (isMobile) {
      setIsMobileHistoryOpen((prev) => !prev);
      return;
    }
    const panel = historyPanelRef.current;
    if (panel) {
      if (panel.isCollapsed()) {
        panel.expand();
        setIsHistoryCollapsed(false);
        saveCollapsedState(isMainCollapsed, false);
      } else {
        panel.collapse();
        setIsHistoryCollapsed(true);
        saveCollapsedState(isMainCollapsed, true);
      }
    }
  }, [isMobile, isMainCollapsed, saveCollapsedState]);

  // Independent scrolling: detect distance from bottom
  const handleScroll = useCallback(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    const threshold = 120;
    const dist = el.scrollHeight - el.scrollTop - el.clientHeight;
    isUserNearBottomRef.current = dist <= threshold;
  }, []);

  // When switching thread: scroll immediately to bottom
  useEffect(() => {
    if (activeConvId) {
      isUserNearBottomRef.current = true;
      requestAnimationFrame(() => {
        if (scrollContainerRef.current) {
          scrollContainerRef.current.scrollTop =
            scrollContainerRef.current.scrollHeight;
        }
      });
    }
  }, [activeConvId]);

  // When new messages or streaming chunks arrive: only follow if user was near bottom
  useEffect(() => {
    if (isUserNearBottomRef.current && scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop =
        scrollContainerRef.current.scrollHeight;
    }
  }, [messages, streamingText]);

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputPrompt(e.target.value);
    const ta = e.target;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 160) + "px";
  };

  // Load repositories
  useEffect(() => {
    let ignore = false;
    async function loadRepos() {
      try {
        const res = await fetch("/api/repositories");
        if (res.ok && !ignore) {
          const data = await res.json();
          const items: Repository[] = data.repositories || data.items || [];
          setRepositories(items);
          if (items.length > 0) {
            const searchParams =
              typeof window !== "undefined"
                ? new URLSearchParams(window.location.search)
                : null;
            const targetRepoId = searchParams?.get("repo_id");
            const matched = items.find((r) => r.id === targetRepoId);
            setSelectedRepoId(matched ? matched.id : items[0].id);
          }
        }
      } catch (err) {
        if (!ignore) console.error("Failed to load repositories:", err);
      }
    }
    loadRepos();
    return () => {
      ignore = true;
    };
  }, []);

  // Load conversations when selected repo changes
  useEffect(() => {
    if (!selectedRepoId) return;

    let ignore = false;
    async function loadConversations() {
      try {
        const res = await fetch(
          `/api/conversations?repository_id=${encodeURIComponent(selectedRepoId)}`
        );
        if (res.ok && !ignore) {
          const data = await res.json();
          const items: Conversation[] = data.items || [];
          setConversations(items);
          if (items.length > 0) {
            setActiveConvId(items[0].id);
          } else {
            setActiveConvId("");
            setMessages([]);
          }
        }
      } catch (err) {
        if (!ignore) console.error("Failed to load conversations:", err);
      }
    }
    loadConversations();
    return () => {
      ignore = true;
    };
  }, [selectedRepoId]);

  // Load messages when active conversation changes
  useEffect(() => {
    if (!activeConvId) return;

    let ignore = false;
    async function loadConversationMessages() {
      try {
        const res = await fetch(`/api/conversations/${activeConvId}`);
        if (res.ok && !ignore) {
          const data = await res.json();
          setMessages(data.messages || []);
        }
      } catch (err) {
        if (!ignore) console.error("Failed to load conversation messages:", err);
      }
    }
    loadConversationMessages();
    return () => {
      ignore = true;
    };
  }, [activeConvId]);

  const handleNewConversation = async () => {
    if (!selectedRepoId) return;
    setErrorMsg("");
    try {
      const selectedRepo = repositories.find((r) => r.id === selectedRepoId);
      const title = `${selectedRepo?.name || "Codebase"} Q&A`;

      const res = await fetch("/api/conversations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repository_id: selectedRepoId, title }),
      });

      if (res.ok) {
        const newConv: Conversation = await res.json();
        setConversations([newConv, ...conversations]);
        setActiveConvId(newConv.id);
        setMessages([]);
      } else {
        const err = await res.json();
        setErrorMsg(err.error || "Failed to create conversation");
      }
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : String(err));
    }
  };

  const handleDeleteConversation = async (convId: string) => {
    try {
      const res = await fetch(`/api/conversations/${convId}`, {
        method: "DELETE",
      });
      if (res.ok) {
        const remaining = conversations.filter((c) => c.id !== convId);
        setConversations(remaining);
        if (activeConvId === convId) {
          const nextActive = remaining.length > 0 ? remaining[0].id : "";
          setActiveConvId(nextActive);
          setMessages([]);
        }
      }
    } catch (err) {
      console.error("Failed to delete conversation:", err);
    }
  };

  const handleSendMessage = useCallback(
    async (e?: React.FormEvent) => {
      e?.preventDefault();
      if (!inputPrompt.trim() || isStreaming) return;

      setErrorMsg("");
      const prompt = inputPrompt.trim();
      setInputPrompt("");
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }

      let currentConvId = activeConvId;

      if (!currentConvId) {
        if (!selectedRepoId) {
          setErrorMsg("Please select an indexed repository first.");
          return;
        }
        try {
          const selectedRepo = repositories.find((r) => r.id === selectedRepoId);
          const title = prompt.slice(0, 40) || `${selectedRepo?.name} Q&A`;
          const res = await fetch("/api/conversations", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ repository_id: selectedRepoId, title }),
          });
          if (!res.ok) {
            setErrorMsg("Failed to start conversation");
            return;
          }
          const created: Conversation = await res.json();
          setConversations((prev) => [created, ...prev]);
          setActiveConvId(created.id);
          currentConvId = created.id;
        } catch {
          setErrorMsg("Error creating conversation thread.");
          return;
        }
      }

      const tempUserMsg: Message = {
        id: `temp-${Date.now()}`,
        role: "user",
        content: prompt,
        status: "completed",
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, tempUserMsg]);
      setIsStreaming(true);
      setStreamingText("");
      setStreamingCitations([]);

      try {
        const res = await fetch(
          `/api/conversations/${currentConvId}/messages`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ content: prompt }),
          }
        );

        if (!res.ok) {
          const errJson = await res.json().catch(() => ({}));
          throw new Error(errJson.detail || "Server error during streaming");
        }

        const reader = res.body?.getReader();
        if (!reader) throw new Error("No readable stream response");

        const decoder = new TextDecoder("utf-8");
        let collectedCitations: Citation[] = [];

        const accumulator = createSSEStreamAccumulator<Citation>({
          onCitations: (citations) => {
            collectedCitations = citations;
            setStreamingCitations(citations);
          },
          onChunk: (_chunk, accumulated) => {
            setStreamingText(accumulated);
          },
          onDone: (doneData, fullText) => {
            const assistantMsg: Message = {
              id: doneData.message_id || `asst-${Date.now()}`,
              role: "assistant",
              content: fullText,
              status: "completed",
              citations: collectedCitations,
              created_at: new Date().toISOString(),
            };
            setMessages((prev) => [...prev, assistantMsg]);
            setStreamingText("");
            setStreamingCitations([]);
          },
          onError: (errMsg, partialText) => {
            setErrorMsg(errMsg);
            if (partialText) {
              const partialMsg: Message = {
                id: `asst-${Date.now()}`,
                role: "assistant",
                content: partialText,
                status: "failed",
                citations: collectedCitations,
                created_at: new Date().toISOString(),
              };
              setMessages((prev) => [...prev, partialMsg]);
              setStreamingText("");
              setStreamingCitations([]);
            }
          },
        });

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          if (value) {
            accumulator.push(value, decoder);
          }
        }
        accumulator.flush(decoder);
      } catch (err: unknown) {
        setErrorMsg(err instanceof Error ? err.message : String(err));
      } finally {
        setIsStreaming(false);
      }
    },
    [inputPrompt, isStreaming, activeConvId, selectedRepoId, repositories]
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const activeRepo = repositories.find((r) => r.id === selectedRepoId);

  // Current chat pane (Column 3)
  const conversationPaneContent = (
    <section className="flex-1 flex flex-col h-full min-w-0 overflow-hidden bg-slate-50 dark:bg-zinc-950 transition-colors">
      {/* ── Conversation Header Bar ── */}
      <div className="shrink-0 border-b border-slate-200/80 dark:border-zinc-800/80 px-4 py-2.5 bg-white/80 dark:bg-zinc-900/40 backdrop-blur-sm flex items-center justify-between gap-3">
        {/* Left: Toggles & Title */}
        <div className="flex items-center gap-2 min-w-0">
          {isMobile ? (
            <>
              <button
                type="button"
                onClick={() => {
                  setIsMobileMainOpen(true);
                  setIsMobileHistoryOpen(false);
                }}
                aria-label="Open navigation menu"
                title="Open navigation menu"
                className="p-1.5 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-slate-300 dark:text-zinc-400 dark:hover:text-white dark:hover:bg-zinc-800/80 dark:border-zinc-800 transition-colors cursor-pointer"
              >
                <Menu className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={() => {
                  setIsMobileHistoryOpen(true);
                  setIsMobileMainOpen(false);
                }}
                aria-label="Open chat threads"
                title="Open chat threads"
                className="p-1.5 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-slate-300 dark:text-zinc-400 dark:hover:text-white dark:hover:bg-zinc-800/80 dark:border-zinc-800 transition-colors cursor-pointer"
              >
                <MessageSquare className="h-4 w-4" />
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                onClick={handleToggleMainSidebar}
                aria-label={
                  isMainCollapsed
                    ? "Restore Main Sidebar (Ctrl+B)"
                    : "Collapse Main Sidebar (Ctrl+B)"
                }
                title={
                  isMainCollapsed
                    ? "Restore Main Sidebar (Ctrl+B)"
                    : "Collapse Main Sidebar (Ctrl+B)"
                }
                className={`flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs font-medium border transition-colors cursor-pointer ${
                  isMainCollapsed
                    ? "bg-indigo-50 text-indigo-700 border-indigo-200 hover:bg-indigo-100 dark:bg-indigo-600/15 dark:text-indigo-300 dark:border-indigo-500/30 dark:hover:bg-indigo-600/25"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-100 border-slate-300/80 dark:text-zinc-400 dark:hover:text-zinc-200 dark:hover:bg-zinc-800 dark:border-zinc-800/80"
                }`}
              >
                <PanelLeft className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Nav</span>
              </button>

              <button
                type="button"
                onClick={handleToggleHistorySidebar}
                aria-label={
                  isHistoryCollapsed
                    ? "Restore Threads Sidebar"
                    : "Collapse Threads Sidebar"
                }
                title={
                  isHistoryCollapsed
                    ? "Restore Threads Sidebar"
                    : "Collapse Threads Sidebar"
                }
                className={`flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs font-medium border transition-colors cursor-pointer ${
                  isHistoryCollapsed
                    ? "bg-indigo-50 text-indigo-700 border-indigo-200 hover:bg-indigo-100 dark:bg-indigo-600/15 dark:text-indigo-300 dark:border-indigo-500/30 dark:hover:bg-indigo-600/25"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-100 border-slate-300/80 dark:text-zinc-400 dark:hover:text-zinc-200 dark:hover:bg-zinc-800 dark:border-zinc-800/80"
                }`}
              >
                <MessageSquare className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Threads</span>
              </button>
            </>
          )}

          <div className="h-4 w-px bg-slate-300 dark:bg-zinc-800 mx-1 hidden sm:block" />

          <div className="flex items-center gap-2 min-w-0">
            <div className="h-7 w-7 rounded-lg bg-indigo-50 border border-indigo-200 text-indigo-600 dark:bg-indigo-600/20 dark:border-indigo-500/30 dark:text-indigo-400 flex items-center justify-center shrink-0">
              <Sparkles className="h-3.5 w-3.5" />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-slate-900 dark:text-white leading-none shrink-0">
                Cortex RAG
              </p>
              <p className="text-[10px] text-slate-500 dark:text-zinc-500 mt-0.5 leading-none truncate hidden xl:block">
                Grounded · Technical Architecture View
              </p>
            </div>
            <Badge variant="indigo" className="text-[9px] py-0 px-1.5 shrink-0">
              Verified RAG
            </Badge>
          </div>
        </div>

        {/* Right: Active Repo info, Theme Switcher & User Profile Button */}
        <div className="flex items-center gap-2.5 sm:gap-3 shrink-0">
          {activeRepo && (
            <div className="hidden md:flex items-center gap-2.5 text-[11px] text-slate-600 dark:text-zinc-400 bg-slate-100 dark:bg-zinc-900/60 border border-slate-200 dark:border-zinc-800 rounded-lg px-2.5 py-1">
              <span className="flex items-center gap-1">
                <FolderGit2 className="h-3 w-3 text-indigo-600 dark:text-indigo-400" />
                <span className="text-slate-800 dark:text-zinc-200 font-medium truncate max-w-[120px]">
                  {activeRepo.name}
                </span>
              </span>
              <span className="text-slate-400 dark:text-zinc-600">·</span>
              <span className="flex items-center gap-1">
                <GitBranch className="h-3 w-3 text-slate-500 dark:text-zinc-500" />
                <span className="truncate max-w-[80px]">
                  {activeRepo.default_branch}
                </span>
              </span>
            </div>
          )}

          {/* Theme Switcher in Chat Header */}
          <ThemeToggle size="sm" />

          <UserButton
            appearance={{
              elements: {
                avatarBox: "h-7 w-7 ring-1 ring-slate-300 dark:ring-zinc-700",
              },
            }}
          />
        </div>
      </div>

      {/* ── Messages Scroll Area (independent container) ── */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto overflow-x-hidden min-h-0"
      >
        <div className="max-w-4xl mx-auto w-full px-4 sm:px-6 py-6 space-y-7">
          {/* Empty state */}
          {messages.length === 0 && !isStreaming && (
            <div className="flex flex-col items-center justify-center min-h-[50vh] text-center space-y-5">
              <div className="relative">
                <div className="h-16 w-16 rounded-2xl bg-indigo-50 border border-indigo-200 dark:bg-indigo-600/15 dark:border-indigo-500/25 flex items-center justify-center">
                  <Sparkles className="h-7 w-7 text-indigo-600 dark:text-indigo-400" />
                </div>
                <div className="absolute -bottom-1 -right-1 h-5 w-5 rounded-full bg-emerald-100 border border-emerald-300 dark:bg-emerald-500/20 dark:border-emerald-500/40 flex items-center justify-center">
                  <div className="h-1.5 w-1.5 rounded-full bg-emerald-500 dark:bg-emerald-400" />
                </div>
              </div>
              <div className="space-y-1.5">
                <h3 className="text-base font-semibold text-slate-900 dark:text-white">
                  Codebase Technical Architecture & QA
                </h3>
                <p className="text-xs text-slate-600 dark:text-zinc-400 max-w-md leading-relaxed">
                  Ask repository questions, explore architecture diagrams, inspect
                  function workflows, and review grounded code citations.
                </p>
              </div>
              <div className="flex flex-wrap gap-2 justify-center max-w-lg">
                {[
                  "What is the overall architecture and data flow?",
                  "How does authentication and token verification work?",
                  "Where is the semantic retrieval and indexing logic?",
                ].map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => setInputPrompt(q)}
                    className="text-xs px-3.5 py-1.5 rounded-full border border-slate-300 text-slate-700 hover:text-slate-900 hover:border-indigo-500 hover:bg-indigo-50 dark:border-zinc-700/60 dark:text-zinc-300 dark:hover:text-white dark:hover:border-indigo-500/60 dark:hover:bg-indigo-500/10 transition-all text-left cursor-pointer"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Message list */}
          {messages.map((msg, index) => (
            <div
              key={msg.id || index}
              className={`flex gap-3.5 ${
                msg.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              {msg.role === "assistant" && (
                <div className="h-8 w-8 rounded-xl bg-indigo-50 border border-indigo-200 text-indigo-600 dark:bg-indigo-600/20 dark:border-indigo-500/30 dark:text-indigo-400 flex items-center justify-center shrink-0 mt-1 shadow-xs">
                  <Sparkles className="h-4 w-4" />
                </div>
              )}

              <div
                className={`min-w-0 ${
                  msg.role === "user" ? "max-w-xl" : "flex-1"
                }`}
              >
                {msg.role === "user" ? (
                  <div className="bg-indigo-600 text-white rounded-2xl rounded-br-sm px-4 py-3 text-sm leading-relaxed shadow-sm break-words">
                    {msg.content}
                  </div>
                ) : (
                  <article className="bg-white dark:bg-zinc-900/60 border border-slate-200/90 dark:border-zinc-800 rounded-2xl rounded-tl-sm overflow-hidden shadow-xs dark:shadow-sm">
                    <div className="flex items-center justify-between px-5 py-2.5 bg-slate-50/90 dark:bg-zinc-900/90 border-b border-slate-200/80 dark:border-zinc-800/80">
                      <div className="flex items-center gap-2">
                        <Terminal className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-400" />
                        <span className="text-xs font-semibold text-slate-800 dark:text-zinc-200">
                          Codebase Analysis
                        </span>
                        {msg.status === "failed" ? (
                          <Badge
                            variant="destructive"
                            className="text-[9px] py-0 px-1.5"
                          >
                            Interrupted
                          </Badge>
                        ) : (
                          <span className="text-[10px] text-slate-500 dark:text-zinc-500">
                            Grounded Report
                          </span>
                        )}
                      </div>
                      <CopyMessageButton content={msg.content} />
                    </div>

                    <div className="px-5 sm:px-6 py-5 text-slate-800 dark:text-zinc-200">
                      <MarkdownRenderer content={msg.content} />
                    </div>

                    {msg.citations && msg.citations.length > 0 && (
                      <div className="px-5 sm:px-6 py-3 bg-slate-50/80 dark:bg-zinc-950/60 border-t border-slate-200/80 dark:border-zinc-800/80 space-y-2">
                        <div className="flex items-center gap-1.5">
                          <FileCode2 className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-400" />
                          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-600 dark:text-zinc-400">
                            Verified Source Citations ({msg.citations.length})
                          </span>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {msg.citations.map((cite, cIdx) => (
                            <CitationChip key={cIdx} cite={cite} />
                          ))}
                        </div>
                      </div>
                    )}
                  </article>
                )}
              </div>

              {msg.role === "user" && (
                <div className="h-8 w-8 rounded-xl bg-slate-200 border border-slate-300 dark:bg-zinc-800 dark:border-zinc-700 flex items-center justify-center shrink-0 mt-1 text-xs font-bold text-slate-700 dark:text-zinc-300">
                  U
                </div>
              )}
            </div>
          ))}

          {/* Streaming / In-Progress Card */}
          {isStreaming && (
            <div className="flex gap-3.5 justify-start">
              <div className="h-8 w-8 rounded-xl bg-indigo-50 border border-indigo-200 text-indigo-600 dark:bg-indigo-600/20 dark:border-indigo-500/30 dark:text-indigo-400 flex items-center justify-center shrink-0 mt-1">
                <Loader2 className="h-4 w-4 animate-spin" />
              </div>

              <div className="flex-1 bg-white dark:bg-zinc-900/60 border border-slate-200/90 dark:border-zinc-800 rounded-2xl rounded-tl-sm overflow-hidden shadow-xs dark:shadow-sm min-w-0">
                <div className="flex items-center justify-between px-5 py-2.5 bg-slate-50/90 dark:bg-zinc-900/90 border-b border-slate-200/80 dark:border-zinc-800/80">
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-400 animate-spin" />
                    <span className="text-xs font-semibold text-slate-800 dark:text-zinc-200">
                      Generating Codebase Analysis…
                    </span>
                  </div>
                  <Badge
                    variant="indigo"
                    className="text-[9px] py-0 px-1.5 animate-pulse"
                  >
                    Streaming
                  </Badge>
                </div>

                {streamingCitations.length > 0 && (
                  <div className="px-5 sm:px-6 py-2.5 bg-slate-50/60 dark:bg-zinc-950/40 border-b border-slate-200/60 dark:border-zinc-800/60 space-y-1.5">
                    <div className="flex items-center gap-1.5">
                      <FileCode2 className="h-3 w-3 text-indigo-600 dark:text-indigo-400" />
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-600 dark:text-zinc-400">
                        Grounded References ({streamingCitations.length})
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {streamingCitations.map((cite, cIdx) => (
                        <CitationChip key={cIdx} cite={cite} />
                      ))}
                    </div>
                  </div>
                )}

                <div className="px-5 sm:px-6 py-5">
                  {streamingText ? (
                    <div>
                      <MarkdownRenderer content={streamingText} isStreaming />
                      <div className="flex items-center gap-2 mt-4 text-xs text-indigo-600 dark:text-indigo-400 animate-pulse">
                        <span className="h-1.5 w-1.5 rounded-full bg-indigo-600 dark:bg-indigo-400" />
                        <span className="text-[11px]">Streaming analysis…</span>
                      </div>
                    </div>
                  ) : (
                    <TypingIndicator />
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Error alert */}
          {errorMsg && (
            <div className="flex items-start gap-2.5 p-3.5 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900/40 rounded-xl text-xs text-red-700 dark:text-red-300">
              <AlertCircle className="h-4 w-4 shrink-0 text-red-500 mt-0.5" />
              <span className="leading-relaxed">{errorMsg}</span>
            </div>
          )}
        </div>
      </div>

      {/* ── Input Composer Area ── */}
      <div className="shrink-0 border-t border-slate-200/80 dark:border-zinc-800/80 bg-white/70 dark:bg-zinc-900/50 backdrop-blur-sm p-4">
        <div className="max-w-4xl mx-auto">
          <form
            onSubmit={handleSendMessage}
            className="relative flex items-end gap-2 bg-white dark:bg-zinc-900 border border-slate-300 dark:border-zinc-700/60 rounded-2xl px-4 py-3 focus-within:border-indigo-500 focus-within:ring-1 focus-within:ring-indigo-500/20 transition-all shadow-xs"
          >
            <textarea
              ref={textareaRef}
              rows={1}
              placeholder={
                selectedRepoId
                  ? "Ask about architecture, functions, or implementation details…"
                  : "Select a repository to begin…"
              }
              value={inputPrompt}
              onChange={handleTextareaChange}
              onKeyDown={handleKeyDown}
              disabled={isStreaming || !selectedRepoId}
              className="flex-1 resize-none bg-transparent text-sm text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-zinc-500 focus:outline-none leading-relaxed disabled:opacity-50 max-h-40"
              style={{ minHeight: "24px" }}
            />
            <button
              type="submit"
              disabled={isStreaming || !inputPrompt.trim() || !selectedRepoId}
              className="shrink-0 h-8 w-8 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center transition-all hover:scale-105 active:scale-95 cursor-pointer shadow-xs"
              aria-label="Send message"
            >
              {isStreaming ? (
                <Loader2 className="h-3.5 w-3.5 text-white animate-spin" />
              ) : (
                <Send className="h-3.5 w-3.5 text-white" />
              )}
            </button>
          </form>
          <p className="text-center text-[10px] text-slate-500 dark:text-zinc-500 mt-2">
            Press{" "}
            <kbd className="font-mono text-slate-600 dark:text-zinc-400">⌘</kbd>+
            <kbd className="font-mono text-slate-600 dark:text-zinc-400">Enter</kbd> to send
          </p>
        </div>
      </div>
    </section>
  );

  return (
    <div className="h-full w-full overflow-hidden bg-slate-50 dark:bg-zinc-950 text-slate-900 dark:text-zinc-100 flex flex-col transition-colors">
      {isMobile ? (
        /* Mobile Layout: Conversation is primary, drawers for Navigation and Threads */
        <div className="relative h-full w-full flex flex-col overflow-hidden">
          <div className="flex-1 min-h-0 w-full overflow-hidden flex flex-col">
            {conversationPaneContent}
          </div>

          {/* Navigation Drawer */}
          {isMobileMainOpen && (
            <div
              className="fixed inset-0 z-50 flex"
              role="dialog"
              aria-modal="true"
              aria-label="Navigation drawer"
            >
              <div
                className="fixed inset-0 bg-black/60 dark:bg-black/70 backdrop-blur-sm transition-opacity"
                onClick={() => setIsMobileMainOpen(false)}
                aria-hidden="true"
              />
              <div className="relative z-10 w-72 max-w-[85vw] bg-white dark:bg-zinc-950 border-r border-slate-200 dark:border-zinc-800 shadow-2xl flex flex-col h-full overflow-y-auto">
                <div className="absolute top-3 right-3 z-20">
                  <button
                    type="button"
                    onClick={() => setIsMobileMainOpen(false)}
                    aria-label="Close navigation"
                    className="p-1.5 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-100 dark:text-zinc-400 dark:hover:text-white dark:hover:bg-zinc-900 border border-transparent hover:border-slate-200 dark:hover:border-zinc-800 transition-colors cursor-pointer"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
                <DashboardSidebar
                  className="w-full h-full flex flex-col justify-between p-4 bg-white dark:bg-zinc-950 overflow-y-auto min-w-0"
                  onItemClick={() => setIsMobileMainOpen(false)}
                />
              </div>
            </div>
          )}

          {/* Chat Threads Drawer */}
          {isMobileHistoryOpen && (
            <div
              className="fixed inset-0 z-50 flex"
              role="dialog"
              aria-modal="true"
              aria-label="Chat threads drawer"
            >
              <div
                className="fixed inset-0 bg-black/60 dark:bg-black/70 backdrop-blur-sm transition-opacity"
                onClick={() => setIsMobileHistoryOpen(false)}
                aria-hidden="true"
              />
              <div className="relative z-10 w-80 max-w-[90vw] bg-white dark:bg-zinc-950 border-r border-slate-200 dark:border-zinc-800 shadow-2xl flex flex-col h-full overflow-hidden">
                <div className="absolute top-3 right-3 z-20">
                  <button
                    type="button"
                    onClick={() => setIsMobileHistoryOpen(false)}
                    aria-label="Close threads"
                    className="p-1.5 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-100 dark:text-zinc-400 dark:hover:text-white dark:hover:bg-zinc-900 border border-transparent hover:border-slate-200 dark:hover:border-zinc-800 transition-colors cursor-pointer"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
                <ChatHistorySidebar
                  repositories={repositories}
                  selectedRepoId={selectedRepoId}
                  onSelectRepo={(id) => {
                    setSelectedRepoId(id);
                    setMessages([]);
                    setActiveConvId("");
                  }}
                  conversations={conversations}
                  activeConvId={activeConvId}
                  onSelectConv={(id) => {
                    setActiveConvId(id);
                    setIsMobileHistoryOpen(false);
                  }}
                  onNewConv={() => {
                    handleNewConversation();
                    setIsMobileHistoryOpen(false);
                  }}
                  onDeleteConv={handleDeleteConversation}
                  showCollapseButton={false}
                />
              </div>
            </div>
          )}
        </div>
      ) : (
        /* Desktop Layout: 3-column ResizablePanelGroup */
        <ResizablePanelGroup
          direction="horizontal"
          autoSaveId="cortex_chat_layout_v2"
          className="h-full w-full"
        >
          {/* Column 1: Main Application Sidebar */}
          <ResizablePanel
            ref={mainPanelRef}
            defaultSize={18}
            minSize={12}
            maxSize={28}
            collapsible={true}
            collapsedSize={0}
            onCollapse={() => {
              setIsMainCollapsed(true);
              saveCollapsedState(true, isHistoryCollapsed);
            }}
            onExpand={() => {
              setIsMainCollapsed(false);
              saveCollapsedState(false, isHistoryCollapsed);
            }}
            className="min-w-0"
          >
            <DashboardSidebar
              className="w-full h-full flex flex-col justify-between p-4 bg-white dark:bg-zinc-950 overflow-y-auto min-w-0"
              showCollapseButton={true}
              onCollapse={handleToggleMainSidebar}
            />
          </ResizablePanel>

          <ResizableHandle />

          {/* Column 2: Chat History Sidebar */}
          <ResizablePanel
            ref={historyPanelRef}
            defaultSize={20}
            minSize={14}
            maxSize={35}
            collapsible={true}
            collapsedSize={0}
            onCollapse={() => {
              setIsHistoryCollapsed(true);
              saveCollapsedState(isMainCollapsed, true);
            }}
            onExpand={() => {
              setIsHistoryCollapsed(false);
              saveCollapsedState(isMainCollapsed, false);
            }}
            className="min-w-0"
          >
            <ChatHistorySidebar
              repositories={repositories}
              selectedRepoId={selectedRepoId}
              onSelectRepo={(id) => {
                setSelectedRepoId(id);
                setMessages([]);
                setActiveConvId("");
              }}
              conversations={conversations}
              activeConvId={activeConvId}
              onSelectConv={(id) => setActiveConvId(id)}
              onNewConv={handleNewConversation}
              onDeleteConv={handleDeleteConversation}
              showCollapseButton={true}
              onCollapse={handleToggleHistorySidebar}
            />
          </ResizablePanel>

          <ResizableHandle />

          {/* Column 3: Current Conversation */}
          <ResizablePanel
            minSize={35}
            defaultSize={62}
            className="min-w-0"
          >
            {conversationPaneContent}
          </ResizablePanel>
        </ResizablePanelGroup>
      )}
    </div>
  );
}
