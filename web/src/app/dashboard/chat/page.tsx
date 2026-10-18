"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { DashboardHeader } from "@/components/dashboard/header";
import { Badge } from "@/components/ui/badge";
import { MarkdownRenderer } from "@/components/chat/markdown-renderer";
import { createSSEStreamAccumulator } from "@/lib/sse-parser";
import {
  Send,
  Loader2,
  FileCode2,
  Plus,
  Trash2,
  MessageSquare,
  Sparkles,
  GitBranch,
  FolderGit2,
  AlertCircle,
  Copy,
  Check,
  Terminal,
} from "lucide-react";

interface Repository {
  id: string;
  name: string;
  owner: string;
  default_branch: string;
  status: string;
}

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

interface Conversation {
  id: string;
  repository_id: string;
  title: string;
  created_at: string;
}

function CitationChip({ cite }: { cite: Citation }) {
  const [copied, setCopied] = useState(false);
  const fileName = cite.file_path.split("/").pop();

  const handleCopy = () => {
    navigator.clipboard.writeText(`${cite.file_path}:${cite.start_line}-${cite.end_line}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      title={`Click to copy reference: ${cite.file_path}:${cite.start_line}-${cite.end_line}`}
      className="group inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-zinc-850 hover:bg-zinc-800 border border-zinc-750 hover:border-indigo-500/50 text-[11px] font-mono text-zinc-300 transition-colors cursor-pointer"
    >
      <FileCode2 className="h-3 w-3 text-indigo-400 shrink-0" />
      <span className="text-zinc-200 font-medium truncate max-w-[140px]" title={cite.file_path}>
        {fileName}
      </span>
      <span className="text-indigo-400 font-medium shrink-0">
        :{cite.start_line}-{cite.end_line}
      </span>
      {cite.symbol_name && (
        <span className="text-emerald-400 shrink-0 text-[10px]">· {cite.symbol_name}</span>
      )}
      {copied ? (
        <Check className="h-3 w-3 text-emerald-400 shrink-0" />
      ) : (
        <Copy className="h-2.5 w-2.5 text-zinc-500 group-hover:text-zinc-300 shrink-0" />
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
      className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-medium text-zinc-400 hover:text-white hover:bg-zinc-800 border border-transparent hover:border-zinc-700/60 transition-colors"
      title="Copy entire answer as Markdown"
    >
      {copied ? (
        <>
          <Check className="h-3 w-3 text-emerald-400" />
          <span className="text-emerald-400">Copied</span>
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
    <div className="flex items-center gap-2 py-3 px-1 text-zinc-400 text-xs">
      <div className="flex gap-1.5 items-center">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-1.5 w-1.5 rounded-full bg-indigo-400 animate-bounce"
            style={{ animationDelay: `${i * 150}ms`, animationDuration: "900ms" }}
          />
        ))}
      </div>
      <span className="text-[11px] text-zinc-500">Searching codebase & formulating technical analysis…</span>
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

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingText]);

  // Auto-resize textarea
  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputPrompt(e.target.value);
    const ta = e.target;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 160) + "px";
  };

  // Load user repositories
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

  // Load conversations when repo changes
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

  // Create new conversation
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

  // Delete conversation
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

  // Submit message and stream SSE
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
        const res = await fetch(`/api/conversations/${currentConvId}/messages`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content: prompt }),
        });

        if (!res.ok) {
          const errJson = await res.json().catch(() => ({}));
          throw new Error(errJson.detail || "Server error during streaming");
        }

        const reader = res.body?.getReader();
        if (!reader) throw new Error("No readable stream response");

        const decoder = new TextDecoder("utf-8");
        let collectedCitations: Citation[] = [];

        // Use robust SSE accumulator that preserves exact whitespace, multi-line chunks, and newlines
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

  // Cmd/Ctrl+Enter to send
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const activeRepo = repositories.find((r) => r.id === selectedRepoId);

  return (
    <>
      <DashboardHeader
        title="Codebase Chat"
        subtitle="Conversational RAG with verified line-level citations"
      />

      <main className="flex-1 flex flex-col lg:flex-row gap-0 overflow-hidden" style={{ height: "calc(100vh - 80px)" }}>
        {/* ─── Left Sidebar ─────────────────────────────────────── */}
        <aside className="w-full lg:w-64 xl:w-72 flex flex-col border-r border-zinc-800 bg-zinc-950/80 shrink-0 overflow-hidden">
          {/* Repo selector */}
          <div className="p-4 border-b border-zinc-800/80">
            <label className="text-[10px] font-semibold text-zinc-500 uppercase tracking-widest block mb-2">
              Active Repository
            </label>
            <select
              className="w-full rounded-lg bg-zinc-900 border border-zinc-800 px-3 py-2 text-xs text-white focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 transition-colors appearance-none cursor-pointer"
              value={selectedRepoId}
              onChange={(e) => {
                setSelectedRepoId(e.target.value);
                setMessages([]);
                setActiveConvId("");
              }}
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
          <div className="flex items-center justify-between px-4 py-3">
            <span className="text-[10px] font-semibold text-zinc-500 uppercase tracking-widest">
              Threads
            </span>
            <button
              onClick={handleNewConversation}
              disabled={!selectedRepoId}
              className="flex items-center gap-1.5 text-[11px] text-zinc-400 hover:text-white disabled:opacity-40 transition-colors bg-zinc-800/60 hover:bg-zinc-700/60 border border-zinc-700/60 rounded-lg px-2.5 py-1"
            >
              <Plus className="h-3 w-3" />
              New
            </button>
          </div>

          {/* Conversations list */}
          <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-0.5">
            {conversations.length === 0 ? (
              <div className="text-center py-8 px-4">
                <MessageSquare className="h-6 w-6 text-zinc-700 mx-auto mb-2" />
                <p className="text-xs text-zinc-600">No threads yet. Start a new chat.</p>
              </div>
            ) : (
              conversations.map((conv) => (
                <div
                  key={conv.id}
                  className={`group flex items-center justify-between px-3 py-2.5 rounded-lg text-xs cursor-pointer transition-all ${
                    activeConvId === conv.id
                      ? "bg-indigo-600/15 text-indigo-200 border border-indigo-500/25"
                      : "text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-200 border border-transparent"
                  }`}
                  onClick={() => {
                    setActiveConvId(conv.id);
                  }}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <MessageSquare
                      className={`h-3 w-3 shrink-0 ${
                        activeConvId === conv.id ? "text-indigo-400" : "text-zinc-600"
                      }`}
                    />
                    <span className="truncate">{conv.title}</span>
                  </div>
                  <button
                    className="opacity-0 group-hover:opacity-100 p-1 rounded hover:text-red-400 transition-all shrink-0"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteConversation(conv.id);
                    }}
                    title="Delete thread"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </div>
              ))
            )}
          </div>
        </aside>

        {/* ─── Main Chat Pane ────────────────────────────────────── */}
        <section className="flex-1 flex flex-col min-w-0 overflow-hidden bg-zinc-950">
          {/* Chat header bar */}
          <div className="shrink-0 border-b border-zinc-800/80 px-5 py-3 bg-zinc-900/40 backdrop-blur-sm flex items-center justify-between gap-3">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="h-7 w-7 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center shrink-0">
                <Sparkles className="h-3.5 w-3.5 text-indigo-400" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold text-white leading-none">Cortex RAG</p>
                <p className="text-[10px] text-zinc-500 mt-0.5 leading-none">
                  Grounded · Technical Documentation View
                </p>
              </div>
              <Badge variant="indigo" className="text-[9px] py-0 px-1.5 shrink-0">
                Verified RAG
              </Badge>
            </div>

            {activeRepo && (
              <div className="flex items-center gap-3 text-[11px] text-zinc-500 shrink-0">
                <span className="flex items-center gap-1">
                  <FolderGit2 className="h-3 w-3" />
                  <span className="text-zinc-300 font-medium">{activeRepo.name}</span>
                </span>
                <span className="flex items-center gap-1">
                  <GitBranch className="h-3 w-3" />
                  <span>{activeRepo.default_branch}</span>
                </span>
              </div>
            )}
          </div>

          {/* ── Messages scroll area ── */}
          <div className="flex-1 overflow-y-auto overflow-x-hidden">
            <div className="max-w-4xl mx-auto w-full px-4 sm:px-6 py-6 space-y-7">
              {/* Empty state */}
              {messages.length === 0 && !isStreaming && (
                <div className="flex flex-col items-center justify-center min-h-[50vh] text-center space-y-5">
                  <div className="relative">
                    <div className="h-16 w-16 rounded-2xl bg-indigo-600/15 border border-indigo-500/25 flex items-center justify-center">
                      <Sparkles className="h-7 w-7 text-indigo-400" />
                    </div>
                    <div className="absolute -bottom-1 -right-1 h-5 w-5 rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center">
                      <div className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                    </div>
                  </div>
                  <div className="space-y-1.5">
                    <h3 className="text-base font-semibold text-white">
                      Codebase Technical Architecture & QA
                    </h3>
                    <p className="text-xs text-zinc-400 max-w-md leading-relaxed">
                      Ask repository questions, explore architecture diagrams, inspect function workflows, and review grounded code citations.
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
                        onClick={() => setInputPrompt(q)}
                        className="text-xs px-3.5 py-1.5 rounded-full border border-zinc-700/60 text-zinc-300 hover:text-white hover:border-indigo-500/60 hover:bg-indigo-500/10 transition-all text-left"
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
                  {/* Assistant avatar */}
                  {msg.role === "assistant" && (
                    <div className="h-8 w-8 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center shrink-0 mt-1 shadow-sm">
                      <Sparkles className="h-4 w-4 text-indigo-400" />
                    </div>
                  )}

                  <div
                    className={`min-w-0 ${
                      msg.role === "user" ? "max-w-xl" : "flex-1"
                    }`}
                  >
                    {msg.role === "user" ? (
                      /* User query bubble */
                      <div className="bg-indigo-600 text-white rounded-2xl rounded-br-sm px-4 py-3 text-sm leading-relaxed shadow-sm break-words">
                        {msg.content}
                      </div>
                    ) : (
                      /* Technical Report Assistant Card */
                      <article className="bg-zinc-900/60 border border-zinc-800 rounded-2xl rounded-tl-sm overflow-hidden shadow-sm">
                        {/* Report Header Bar */}
                        <div className="flex items-center justify-between px-5 py-2.5 bg-zinc-900/90 border-b border-zinc-800/80">
                          <div className="flex items-center gap-2">
                            <Terminal className="h-3.5 w-3.5 text-indigo-400" />
                            <span className="text-xs font-semibold text-zinc-200">
                              Codebase Analysis
                            </span>
                            {msg.status === "failed" ? (
                              <Badge variant="destructive" className="text-[9px] py-0 px-1.5">
                                Interrupted
                              </Badge>
                            ) : (
                              <span className="text-[10px] text-zinc-500">
                                Grounded Report
                              </span>
                            )}
                          </div>
                          <CopyMessageButton content={msg.content} />
                        </div>

                        {/* Report Body */}
                        <div className="px-5 sm:px-6 py-5 text-zinc-200">
                          <MarkdownRenderer content={msg.content} />
                        </div>

                        {/* Citations Footer */}
                        {msg.citations && msg.citations.length > 0 && (
                          <div className="px-5 sm:px-6 py-3 bg-zinc-950/60 border-t border-zinc-800/80 space-y-2">
                            <div className="flex items-center gap-1.5">
                              <FileCode2 className="h-3.5 w-3.5 text-indigo-400" />
                              <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
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

                  {/* User avatar */}
                  {msg.role === "user" && (
                    <div className="h-8 w-8 rounded-xl bg-zinc-800 border border-zinc-700 flex items-center justify-center shrink-0 mt-1 text-xs font-bold text-zinc-300">
                      U
                    </div>
                  )}
                </div>
              ))}

              {/* Streaming / In-Progress Card */}
              {isStreaming && (
                <div className="flex gap-3.5 justify-start">
                  <div className="h-8 w-8 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center shrink-0 mt-1">
                    <Loader2 className="h-4 w-4 text-indigo-400 animate-spin" />
                  </div>

                  <div className="flex-1 bg-zinc-900/60 border border-zinc-800 rounded-2xl rounded-tl-sm overflow-hidden shadow-sm min-w-0">
                    {/* Header */}
                    <div className="flex items-center justify-between px-5 py-2.5 bg-zinc-900/90 border-b border-zinc-800/80">
                      <div className="flex items-center gap-2">
                        <Loader2 className="h-3.5 w-3.5 text-indigo-400 animate-spin" />
                        <span className="text-xs font-semibold text-zinc-200">
                          Generating Codebase Analysis…
                        </span>
                      </div>
                      <Badge variant="indigo" className="text-[9px] py-0 px-1.5 animate-pulse">
                        Streaming
                      </Badge>
                    </div>

                    {/* Live citations if ready before text */}
                    {streamingCitations.length > 0 && (
                      <div className="px-5 sm:px-6 py-2.5 bg-zinc-950/40 border-b border-zinc-800/60 space-y-1.5">
                        <div className="flex items-center gap-1.5">
                          <FileCode2 className="h-3 w-3 text-indigo-400" />
                          <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
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

                    {/* Live streaming text or typing indicator */}
                    <div className="px-5 sm:px-6 py-5">
                      {streamingText ? (
                        <div>
                          <MarkdownRenderer content={streamingText} />
                          <div className="flex items-center gap-2 mt-4 text-xs text-indigo-400/80 animate-pulse">
                            <span className="h-1.5 w-1.5 rounded-full bg-indigo-400" />
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
                <div className="flex items-start gap-2.5 p-3.5 bg-red-950/30 border border-red-900/40 rounded-xl text-xs text-red-300">
                  <AlertCircle className="h-4 w-4 shrink-0 text-red-400 mt-0.5" />
                  <span className="leading-relaxed">{errorMsg}</span>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* ── Input composer area ── */}
          <div className="shrink-0 border-t border-zinc-800/80 bg-zinc-900/50 backdrop-blur-sm p-4">
            <div className="max-w-4xl mx-auto">
              <form
                onSubmit={handleSendMessage}
                className="relative flex items-end gap-2 bg-zinc-900 border border-zinc-700/60 rounded-2xl px-4 py-3 focus-within:border-indigo-500/60 focus-within:ring-1 focus-within:ring-indigo-500/20 transition-all shadow-sm"
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
                  className="flex-1 resize-none bg-transparent text-sm text-white placeholder-zinc-500 focus:outline-none leading-relaxed disabled:opacity-50 max-h-40"
                  style={{ minHeight: "24px" }}
                />
                <button
                  type="submit"
                  disabled={isStreaming || !inputPrompt.trim() || !selectedRepoId}
                  className="shrink-0 h-8 w-8 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center transition-all hover:scale-105 active:scale-95"
                  aria-label="Send message"
                >
                  {isStreaming ? (
                    <Loader2 className="h-3.5 w-3.5 text-white animate-spin" />
                  ) : (
                    <Send className="h-3.5 w-3.5 text-white" />
                  )}
                </button>
              </form>
              <p className="text-center text-[10px] text-zinc-500 mt-2">
                Press <kbd className="font-mono text-zinc-400">⌘</kbd>+<kbd className="font-mono text-zinc-400">Enter</kbd> to send
              </p>
            </div>
          </div>
        </section>
      </main>
    </>
  );
}
