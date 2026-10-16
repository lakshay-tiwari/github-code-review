import { DashboardHeader } from "@/components/dashboard/header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Sparkles,
  GitPullRequest,
  CheckCircle2,
  FileCode2,
} from "lucide-react";

export default function ChatWorkspacePage() {
  return (
    <>
      <DashboardHeader
        title="Codebase Chat &amp; Workspace"
        subtitle="Conversational RAG interface with verified line-level citations"
      />

      <main className="flex-1 p-6 lg:p-8 max-w-5xl space-y-6">
        <Card className="border-indigo-900/40 bg-indigo-950/20">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 mb-3">
              <Badge variant="indigo">Scheduled for Phase 6</Badge>
              <span className="text-xs text-zinc-400">
                LangGraph RAG Workflow &amp; Response Streaming
              </span>
            </div>

            <h2 className="text-xl font-bold text-white">
              Interactive Codebase RAG Workspace
            </h2>

            <p className="mt-2 text-xs sm:text-sm text-zinc-300 leading-relaxed max-w-2xl">
              This workspace will stream grounded answers directly from FastAPI,
              utilizing a LangGraph-orchestrated workflow. In accordance with the
              architectural guidelines, no fake AI responses or mock chat histories
              are generated before actual backend wiring.
            </p>
          </CardContent>
        </Card>

        {/* Workflow capabilities card */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Card className="p-4">
            <CardContent className="p-0">
              <div className="flex items-center gap-2 text-indigo-400 mb-2">
                <FileCode2 className="h-4 w-4" />
                <h3 className="text-xs font-semibold text-white">
                  Validated Citations
                </h3>
              </div>
              <p className="text-[11px] text-zinc-400 leading-relaxed">
                Every generated response cites exact file paths and line ranges backed
                by the indexed Git commit SHA.
              </p>
            </CardContent>
          </Card>

          <Card className="p-4">
            <CardContent className="p-0">
              <div className="flex items-center gap-2 text-cyan-400 mb-2">
                <Sparkles className="h-4 w-4" />
                <h3 className="text-xs font-semibold text-white">
                  Streaming SSE
                </h3>
              </div>
              <p className="text-[11px] text-zinc-400 leading-relaxed">
                Direct streaming from FastAPI via server-side proxy handlers without
                blocking ingestion queues.
              </p>
            </CardContent>
          </Card>

          <Card className="p-4">
            <CardContent className="p-0">
              <div className="flex items-center gap-2 text-emerald-400 mb-2">
                <GitPullRequest className="h-4 w-4" />
                <h3 className="text-xs font-semibold text-white">
                  Checkpointed History
                </h3>
              </div>
              <p className="text-[11px] text-zinc-400 leading-relaxed">
                Durable PostgreSQL conversation history coupled with LangGraph
                thread checkpointing.
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Phase Roadmap Details */}
        <Card className="p-6">
          <CardContent className="p-0 space-y-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Implementation Timeline for this Workspace
            </h3>
            <ul className="space-y-3 text-xs text-zinc-300">
              <li className="flex items-start gap-2.5">
                <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                <span>
                  <strong>Phase 1 &amp; Phase 2:</strong> Infrastructure established, Clerk authentication shell and design system in place.
                </span>
              </li>
              <li className="flex items-start gap-2.5">
                <span className="h-4 w-4 rounded-full border border-zinc-700 bg-zinc-800 flex items-center justify-center text-[10px] text-zinc-400 shrink-0 mt-0.5">
                  3
                </span>
                <span>
                  <strong>Phase 3:</strong> Backend models, Groq LLM provider, Qdrant adapter, Neo4j adapter, Celery queue.
                </span>
              </li>
              <li className="flex items-start gap-2.5">
                <span className="h-4 w-4 rounded-full border border-zinc-700 bg-zinc-800 flex items-center justify-center text-[10px] text-zinc-400 shrink-0 mt-0.5">
                  4-5
                </span>
                <span>
                  <strong>Phase 4 &amp; 5:</strong> Repository cloning, Tree-sitter syntax chunking, vector indexing into Qdrant.
                </span>
              </li>
              <li className="flex items-start gap-2.5">
                <span className="h-4 w-4 rounded-full border border-indigo-500 bg-indigo-500/20 flex items-center justify-center text-[10px] text-indigo-300 shrink-0 mt-0.5">
                  6
                </span>
                <span>
                  <strong>Phase 6:</strong> LangGraph RAG chat integration, real-time token streaming, citation badges, and chat history.
                </span>
              </li>
            </ul>
          </CardContent>
        </Card>
      </main>
    </>
  );
}
