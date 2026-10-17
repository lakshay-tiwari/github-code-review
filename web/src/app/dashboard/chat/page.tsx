"use client";

import { useEffect, useState, useRef } from "react";
import { DashboardHeader } from "@/components/dashboard/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingText]);

  // Load user repositories
  useEffect(() => {
    async function loadRepos() {
      try {
        const res = await fetch("/api/repositories");
        if (res.ok) {
          const data = await res.json();
          const items: Repository[] = data.items || [];
          setRepositories(items);
          if (items.length > 0) {
            setSelectedRepoId(items[0].id);
          }
        }
      } catch (err) {
        console.error("Failed to load repositories:", err);
      }
    }
    loadRepos();
  }, []);

  // Load conversations when repo changes
  useEffect(() => {
    if (!selectedRepoId) return;

    async function loadConversations() {
      try {
        const res = await fetch(
          `/api/conversations?repository_id=${encodeURIComponent(selectedRepoId)}`
        );
        if (res.ok) {
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
        console.error("Failed to load conversations:", err);
      }
    }
    loadConversations();
  }, [selectedRepoId]);

  // Load messages when active conversation changes
  useEffect(() => {
    if (!activeConvId) {
      setMessages([]);
      return;
    }

    async function loadConversationMessages() {
      try {
        const res = await fetch(`/api/conversations/${activeConvId}`);
        if (res.ok) {
          const data = await res.json();
          setMessages(data.messages || []);
        }
      } catch (err) {
        console.error("Failed to load conversation messages:", err);
      }
    }
    loadConversationMessages();
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
        body: JSON.stringify({
          repository_id: selectedRepoId,
          title,
        }),
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
          setActiveConvId(remaining.length > 0 ? remaining[0].id : "");
          setMessages([]);
        }
      }
    } catch (err) {
      console.error("Failed to delete conversation:", err);
    }
  };

  // Submit message and stream SSE
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputPrompt.trim() || isStreaming) return;

    setErrorMsg("");
    const prompt = inputPrompt.trim();
    setInputPrompt("");

    let currentConvId = activeConvId;

    // Create conversation on the fly if none selected
    if (!currentConvId) {
      if (!selectedRepoId) {
        setErrorMsg("Please select an indexed repository first.");
        return;
      }
      try {
        const selectedRepo = repositories.find((r) => r.id === selectedRepoId);
        const title = prompt.slice(0, 30) || `${selectedRepo?.name} Q&A`;
        const res = await fetch("/api/conversations", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            repository_id: selectedRepoId,
            title,
          }),
        });
        if (!res.ok) {
          setErrorMsg("Failed to start conversation");
          return;
        }
        const created: Conversation = await res.json();
        setConversations([created, ...conversations]);
        setActiveConvId(created.id);
        currentConvId = created.id;
      } catch (err) {
        setErrorMsg("Error creating conversation thread.");
        return;
      }
    }

    // Optimistically add user turn to UI
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
      let buffer = "";
      let accumulatedContent = "";
      let collectedCitations: Citation[] = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const block of lines) {
          if (!block.trim()) continue;

          let eventType = "message";
          let dataStr = "";

          for (const line of block.split("\n")) {
            if (line.startsWith("event: ")) {
              eventType = line.replace("event: ", "").trim();
            } else if (line.startsWith("data: ")) {
              dataStr = line.replace("data: ", "").trim();
            }
          }

          if (eventType === "citations") {
            try {
              const parsed = JSON.parse(dataStr);
              collectedCitations = parsed;
              setStreamingCitations(parsed);
            } catch {
              // ignore json parse error
            }
          } else if (eventType === "chunk") {
            accumulatedContent += dataStr;
            setStreamingText(accumulatedContent);
          } else if (eventType === "error") {
            try {
              const errData = JSON.parse(dataStr);
              setErrorMsg(errData.error || "Generation interrupted");
            } catch {
              setErrorMsg("Generation failed mid-stream");
            }
          } else if (eventType === "done") {
            try {
              const doneData = JSON.parse(dataStr);
              const assistantMsg: Message = {
                id: doneData.message_id || `asst-${Date.now()}`,
                role: "assistant",
                content: accumulatedContent,
                status: "completed",
                citations: collectedCitations,
                created_at: new Date().toISOString(),
              };
              setMessages((prev) => [...prev, assistantMsg]);
              setStreamingText("");
              setStreamingCitations([]);
            } catch {
              // ignore
            }
          }
        }
      }
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : String(err));
    } finally {
      setIsStreaming(false);
    }
  };

  const handleCopyCode = (text: string, idx: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  return (
    <>
      <DashboardHeader
        title="Codebase Chat & Workspace"
        subtitle="Conversational RAG interface with verified line-level citations and thread checkpointing"
      />

      <main className="flex-1 p-4 lg:p-6 flex flex-col lg:flex-row gap-6 max-w-7xl mx-auto w-full h-[calc(100vh-80px)]">
        {/* Left Sidebar: Repositories & Conversations List */}
        <aside className="w-full lg:w-72 flex flex-col gap-4 border border-zinc-800 bg-zinc-950/60 rounded-xl p-4 shrink-0">
          <div>
            <label className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider block mb-1.5">
              Active Repository
            </label>
            <div className="relative">
              <select
                className="w-full rounded-lg bg-zinc-900 border border-zinc-800 px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                value={selectedRepoId}
                onChange={(e) => setSelectedRepoId(e.target.value)}
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
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-zinc-800">
            <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">
              Conversations
            </span>
            <Button
              size="sm"
              variant="outline"
              className="h-7 px-2 text-[11px] gap-1 border-zinc-700 bg-zinc-900 hover:bg-zinc-800 text-zinc-200"
              onClick={handleNewConversation}
              disabled={!selectedRepoId}
            >
              <Plus className="h-3 w-3" />
              New Chat
            </Button>
          </div>

          <div className="flex-1 overflow-y-auto space-y-1.5 pr-1">
            {conversations.length === 0 ? (
              <p className="text-xs text-zinc-500 text-center py-6">
                No active conversations for this repository. Click &quot;New Chat&quot; to begin.
              </p>
            ) : (
              conversations.map((conv) => (
                <div
                  key={conv.id}
                  className={`group flex items-center justify-between px-3 py-2 rounded-lg text-xs cursor-pointer transition-colors ${
                    activeConvId === conv.id
                      ? "bg-indigo-950/50 text-indigo-200 border border-indigo-900/40"
                      : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200"
                  }`}
                  onClick={() => setActiveConvId(conv.id)}
                >
                  <div className="flex items-center gap-2 truncate pr-2">
                    <MessageSquare className="h-3.5 w-3.5 shrink-0" />
                    <span className="truncate">{conv.title}</span>
                  </div>
                  <button
                    className="opacity-0 group-hover:opacity-100 hover:text-red-400 p-1 rounded transition-opacity"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteConversation(conv.id);
                    }}
                    title="Delete Conversation"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </div>
              ))
            )}
          </div>
        </aside>

        {/* Right Pane: Chat Window & Input Area */}
        <section className="flex-1 flex flex-col border border-zinc-800 bg-zinc-950/40 rounded-xl overflow-hidden">
          {/* Workspace Banner */}
          <div className="border-b border-zinc-800/80 px-6 py-3 bg-zinc-900/30 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-indigo-400" />
              <span className="text-xs font-medium text-white">
                Grounded LangGraph Codebase RAG
              </span>
              <Badge variant="indigo" className="text-[10px] py-0 px-2">
                Phase 6 Verified
              </Badge>
            </div>
            <div className="flex items-center gap-2 text-xs text-zinc-400">
              <FolderGit2 className="h-3.5 w-3.5 text-zinc-500" />
              <span>
                {repositories.find((r) => r.id === selectedRepoId)?.name || "Repository"}
              </span>
              <GitBranch className="h-3.5 w-3.5 text-zinc-500 ml-2" />
              <span>
                {repositories.find((r) => r.id === selectedRepoId)?.default_branch || "main"}
              </span>
            </div>
          </div>

          {/* Messages Flow Area */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {messages.length === 0 && !isStreaming && (
              <div className="h-full flex flex-col items-center justify-center text-center p-8 max-w-md mx-auto space-y-4">
                <div className="p-3 bg-indigo-950/40 border border-indigo-900/40 rounded-full text-indigo-400">
                  <Sparkles className="h-6 w-6" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white">
                    Ask questions about your codebase
                  </h3>
                  <p className="mt-1 text-xs text-zinc-400 leading-relaxed">
                    Cortex retrieves grounded Tree-sitter code chunks, validates evidence,
                    cites exact file paths and line ranges, and checkpoints each state.
                  </p>
                </div>
              </div>
            )}

            {messages.map((msg, index) => (
              <div
                key={msg.id || index}
                className={`flex gap-3 ${
                  msg.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                {msg.role === "assistant" && (
                  <div className="h-7 w-7 rounded-full bg-indigo-600/20 border border-indigo-500/40 flex items-center justify-center text-indigo-400 shrink-0 mt-0.5">
                    <Sparkles className="h-3.5 w-3.5" />
                  </div>
                )}

                <div
                  className={`max-w-2xl rounded-xl p-4 text-xs sm:text-sm ${
                    msg.role === "user"
                      ? "bg-indigo-600 text-white rounded-br-none"
                      : "bg-zinc-900/90 border border-zinc-800 text-zinc-200 rounded-bl-none space-y-3"
                  }`}
                >
                  <p className="whitespace-pre-wrap leading-relaxed">
                    {msg.content}
                  </p>

                  {/* Citations block for assistant messages */}
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="pt-2 border-t border-zinc-800/80 space-y-1.5">
                      <div className="flex items-center gap-1.5 text-[11px] font-semibold text-zinc-400">
                        <FileCode2 className="h-3 w-3 text-indigo-400" />
                        <span>Referenced Evidence ({msg.citations.length}):</span>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {msg.citations.map((cite, cIdx) => (
                          <span
                            key={cIdx}
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-zinc-800/80 border border-zinc-700/60 text-[10px] text-zinc-300 font-mono"
                          >
                            <span>{cite.file_path}</span>
                            <span className="text-indigo-400">
                              #L{cite.start_line}-L{cite.end_line}
                            </span>
                            {cite.symbol_name && (
                              <span className="text-emerald-400">
                                ({cite.symbol_name})
                              </span>
                            )}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {msg.role === "user" && (
                  <div className="h-7 w-7 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center text-zinc-400 shrink-0 mt-0.5 text-xs font-semibold">
                    U
                  </div>
                )}
              </div>
            ))}

            {/* In-flight streaming response turn */}
            {isStreaming && (
              <div className="flex gap-3 justify-start">
                <div className="h-7 w-7 rounded-full bg-indigo-600/20 border border-indigo-500/40 flex items-center justify-center text-indigo-400 shrink-0 mt-0.5">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                </div>

                <div className="max-w-2xl rounded-xl p-4 text-xs sm:text-sm bg-zinc-900/90 border border-zinc-800 text-zinc-200 rounded-bl-none space-y-3">
                  {streamingCitations.length > 0 && (
                    <div className="space-y-1.5 pb-2 border-b border-zinc-800/80">
                      <div className="flex items-center gap-1.5 text-[11px] font-semibold text-zinc-400">
                        <FileCode2 className="h-3 w-3 text-indigo-400" />
                        <span>Verified Citations ({streamingCitations.length}):</span>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {streamingCitations.map((cite, cIdx) => (
                          <span
                            key={cIdx}
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-zinc-800/80 border border-zinc-700/60 text-[10px] text-zinc-300 font-mono"
                          >
                            <span>{cite.file_path}</span>
                            <span className="text-indigo-400">
                              #L{cite.start_line}-L{cite.end_line}
                            </span>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  <p className="whitespace-pre-wrap leading-relaxed">
                    {streamingText || "Searching codebase and generating grounded response..."}
                  </p>
                </div>
              </div>
            )}

            {errorMsg && (
              <div className="flex items-center gap-2 p-3 bg-red-950/40 border border-red-900/40 rounded-lg text-xs text-red-300">
                <AlertCircle className="h-4 w-4 shrink-0 text-red-400" />
                <span>{errorMsg}</span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Prompt Submission Form */}
          <div className="p-4 border-t border-zinc-800 bg-zinc-900/40">
            <form onSubmit={handleSendMessage} className="flex gap-2">
              <input
                type="text"
                placeholder={
                  selectedRepoId
                    ? "Ask a question about this repository's code, architecture, or functions..."
                    : "Select a repository to begin asking questions..."
                }
                value={inputPrompt}
                onChange={(e) => setInputPrompt(e.target.value)}
                disabled={isStreaming || !selectedRepoId}
                className="flex-1 rounded-lg bg-zinc-900 border border-zinc-800 px-4 py-2.5 text-xs sm:text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-indigo-500 disabled:opacity-50"
              />
              <Button
                type="submit"
                disabled={isStreaming || !inputPrompt.trim() || !selectedRepoId}
                className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 h-auto"
              >
                {isStreaming ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </form>
          </div>
        </section>
      </main>
    </>
  );
}
