import Link from "next/link";
import { Navbar } from "@/components/navigation/navbar";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  ArrowRight,
  Database,
  GitBranch,
  Layers,
  Search,
  ShieldCheck,
  Terminal,
} from "lucide-react";

export default function Home() {
  return (
    <div className="relative flex min-h-screen flex-col bg-slate-50 dark:bg-zinc-950 text-slate-900 dark:text-zinc-100 antialiased transition-colors selection:bg-indigo-500 selection:text-white">
      {/* Continuous ambient background mesh across the entire page */}
      <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
        {/* Top hero radial glow */}
        <div className="absolute -top-40 left-1/2 -translate-x-1/2 w-[1100px] h-[600px] bg-[radial-gradient(ellipse_at_center,rgba(99,102,241,0.14),transparent_65%)] dark:bg-[radial-gradient(ellipse_at_center,rgba(99,102,241,0.22),transparent_65%)] blur-2xl" />
        {/* Mid-page ambient subtle violet glow */}
        <div className="absolute top-[40%] left-1/2 -translate-x-1/2 w-[1000px] h-[600px] bg-[radial-gradient(ellipse_at_center,rgba(139,92,246,0.08),transparent_65%)] dark:bg-[radial-gradient(ellipse_at_center,rgba(139,92,246,0.12),transparent_65%)] blur-3xl" />
        {/* Lower ambient cyan/indigo glow */}
        <div className="absolute -bottom-20 left-1/2 -translate-x-1/2 w-[900px] h-[500px] bg-[radial-gradient(ellipse_at_center,rgba(56,189,248,0.06),transparent_65%)] dark:bg-[radial-gradient(ellipse_at_center,rgba(99,102,241,0.08),transparent_65%)] blur-3xl" />
      </div>

      <Navbar />

      <main className="flex-1">
        {/* Hero Section */}
        <section className="relative pt-20 pb-24 lg:pt-32 lg:pb-36">
          <div className="mx-auto max-w-7xl px-6 lg:px-8 text-center">
            <div className="inline-flex items-center gap-2 rounded-full border border-slate-200/90 dark:border-zinc-800 bg-white/90 dark:bg-zinc-900/90 px-3.5 py-1.5 text-xs text-slate-700 dark:text-zinc-300 shadow-xs shadow-slate-200/40 dark:shadow-none backdrop-blur-xs">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse motion-reduce:animate-none" />
              <span>Cortex Architecture Baseline V1 Active</span>
            </div>

            <h1 className="mx-auto mt-8 max-w-4xl text-4xl font-extrabold tracking-tight text-slate-900 dark:text-white sm:text-6xl lg:text-7xl">
              Retrieval-Augmented Generation for{" "}
              <span className="bg-gradient-to-r from-indigo-600 via-violet-600 to-indigo-500 dark:from-indigo-400 dark:via-violet-300 dark:to-indigo-200 bg-clip-text text-transparent">
                GitHub Codebases
              </span>
            </h1>

            <p className="mx-auto mt-6 max-w-2xl text-base sm:text-lg leading-8 text-slate-600 dark:text-zinc-400">
              Submit any public GitHub repository. Cortex indexes source code using
              Tree-sitter syntax-aware chunking, hybrid vector retrieval with Qdrant,
              and Neo4j code relationship graphs — delivering grounded answers with
              validated line-by-line citations.
            </p>

            <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
              <Link href="/dashboard">
                <Button
                  size="lg"
                  className="gap-2 bg-gradient-to-r from-indigo-600 via-indigo-500 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white shadow-lg shadow-indigo-600/25 border-0 hover:shadow-indigo-600/35 active:scale-[0.99] transition-all duration-200"
                >
                  <span>Open Codebase Dashboard</span>
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
              <Link href="/sign-in">
                <Button
                  variant="outline"
                  size="lg"
                  className="border-slate-300/90 dark:border-zinc-800 bg-white/70 dark:bg-zinc-900/60 backdrop-blur-xs text-slate-700 dark:text-zinc-200 hover:bg-slate-100/90 dark:hover:bg-zinc-800 hover:text-slate-900 dark:hover:text-white transition-all shadow-xs"
                >
                  Sign In with Clerk
                </Button>
              </Link>
            </div>

            {/* Architecture stack preview terminal — dual-mode elevated card */}
            <div className="mx-auto mt-16 max-w-3xl rounded-xl border border-slate-200/90 dark:border-zinc-800/90 bg-white/80 dark:bg-zinc-900/80 p-5 text-left shadow-xl shadow-indigo-500/5 dark:shadow-2xl dark:shadow-black/40 backdrop-blur-md transition-colors">
              <div className="flex items-center justify-between border-b border-slate-200/80 dark:border-zinc-800/80 pb-3">
                <div className="flex items-center gap-2">
                  <span className="h-3 w-3 rounded-full bg-red-500/80" />
                  <span className="h-3 w-3 rounded-full bg-amber-500/80" />
                  <span className="h-3 w-3 rounded-full bg-emerald-500/80" />
                  <span className="ml-2 font-mono text-xs text-slate-500 dark:text-zinc-400">
                    cortex-stack ~ v1.0.0
                  </span>
                </div>
                <Badge variant="indigo">Verified Engine</Badge>
              </div>
              <div className="pt-4 font-mono text-xs leading-6 text-slate-700 dark:text-zinc-300">
                <p className="text-slate-600 dark:text-zinc-500">
                  # Phase 1 &amp; Phase 2 foundation active
                </p>
                <p>
                  <span className="font-semibold text-indigo-600 dark:text-indigo-400">GET</span>{" "}
                  <span className="text-slate-800 dark:text-zinc-200">/api/v1/health</span>{" "}
                  <span className="font-medium text-emerald-600 dark:text-emerald-400">→ 200 OK</span>{" "}
                  <span className="text-slate-600 dark:text-zinc-500">
                    [PostgreSQL 16, Redis 7, Qdrant, Neo4j]
                  </span>
                </p>
                <p>
                  <span className="font-semibold text-indigo-600 dark:text-indigo-400">AUTH</span>{" "}
                  <span className="text-slate-800 dark:text-zinc-200">Clerk Session</span>{" "}
                  <span className="font-medium text-emerald-600 dark:text-emerald-400">→ Active</span>{" "}
                  <span className="text-slate-600 dark:text-zinc-500">
                    [Server-side token verification]
                  </span>
                </p>
                <p>
                  <span className="font-semibold text-indigo-600 dark:text-indigo-400">ROUTER</span>{" "}
                  <span className="text-slate-800 dark:text-zinc-200">Protected /dashboard</span>{" "}
                  <span className="font-medium text-emerald-600 dark:text-emerald-400">→ Armed</span>
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Feature Grid — Seamless background with subtle top hairline */}
        <section className="relative py-24 border-t border-slate-200/60 dark:border-zinc-800/60 bg-transparent transition-colors">
          <div className="mx-auto max-w-7xl px-6 lg:px-8">
            <div className="text-center">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                Architectural Capabilities
              </h2>
              <p className="mt-2 text-3xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-4xl">
                Engineered for precision and reproducibility
              </p>
            </div>

            <div className="mt-14 grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
              <Card className="hover:border-indigo-400/60 dark:hover:border-indigo-500/40 hover:shadow-xl hover:shadow-indigo-500/5 hover:-translate-y-1 transition-all duration-200 backdrop-blur-xs">
                <CardContent className="pt-6">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20 mb-4 shadow-xs">
                    <Terminal className="h-5 w-5" />
                  </div>
                  <h3 className="text-base font-semibold text-slate-900 dark:text-white">
                    Tree-sitter Syntax Chunking
                  </h3>
                  <p className="mt-2 text-xs leading-5 text-slate-600 dark:text-zinc-400">
                    AST-aware boundaries preserve functions, classes, and scopes. No
                    arbitrary character splits that destroy context.
                  </p>
                </CardContent>
              </Card>

              <Card className="hover:border-cyan-400/60 dark:hover:border-cyan-500/40 hover:shadow-xl hover:shadow-cyan-500/5 hover:-translate-y-1 transition-all duration-200 backdrop-blur-xs">
                <CardContent className="pt-6">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border border-cyan-500/20 mb-4 shadow-xs">
                    <Search className="h-5 w-5" />
                  </div>
                  <h3 className="text-base font-semibold text-slate-900 dark:text-white">
                    Qdrant Vector Retrieval
                  </h3>
                  <p className="mt-2 text-xs leading-5 text-slate-600 dark:text-zinc-400">
                    Dense semantic embeddings filtered strictly by repository ownership
                    and immutable commit SHA to guarantee zero cross-repo leakage.
                  </p>
                </CardContent>
              </Card>

              <Card className="hover:border-amber-400/60 dark:hover:border-amber-500/40 hover:shadow-xl hover:shadow-amber-500/5 hover:-translate-y-1 transition-all duration-200 backdrop-blur-xs">
                <CardContent className="pt-6">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 mb-4 shadow-xs">
                    <GitBranch className="h-5 w-5" />
                  </div>
                  <h3 className="text-base font-semibold text-slate-900 dark:text-white">
                    Neo4j Code Relationship Graph
                  </h3>
                  <p className="mt-2 text-xs leading-5 text-slate-600 dark:text-zinc-400">
                    Indexes imports, inheritance hierarchies, and function call chains
                    to trace multi-file dependencies reliably.
                  </p>
                </CardContent>
              </Card>

              <Card className="hover:border-violet-400/60 dark:hover:border-violet-500/40 hover:shadow-xl hover:shadow-violet-500/5 hover:-translate-y-1 transition-all duration-200 backdrop-blur-xs">
                <CardContent className="pt-6">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-violet-500/10 text-violet-600 dark:text-violet-400 border border-violet-500/20 mb-4 shadow-xs">
                    <Layers className="h-5 w-5" />
                  </div>
                  <h3 className="text-base font-semibold text-slate-900 dark:text-white">
                    LangGraph Workflow
                  </h3>
                  <p className="mt-2 text-xs leading-5 text-slate-600 dark:text-zinc-400">
                    Multi-step agent graph coordinating question understanding,
                    retrieval grading, citation generation, and hallucination checks.
                  </p>
                </CardContent>
              </Card>

              <Card className="hover:border-emerald-400/60 dark:hover:border-emerald-500/40 hover:shadow-xl hover:shadow-emerald-500/5 hover:-translate-y-1 transition-all duration-200 backdrop-blur-xs">
                <CardContent className="pt-6">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 mb-4 shadow-xs">
                    <ShieldCheck className="h-5 w-5" />
                  </div>
                  <h3 className="text-base font-semibold text-slate-900 dark:text-white">
                    Strict Line-Level Citations
                  </h3>
                  <p className="mt-2 text-xs leading-5 text-slate-600 dark:text-zinc-400">
                    Every answer references exact file paths and line ranges backed by
                    the retrieved commit SHA. Never invented, never hallucinated.
                  </p>
                </CardContent>
              </Card>

              <Card className="hover:border-rose-400/60 dark:hover:border-rose-500/40 hover:shadow-xl hover:shadow-rose-500/5 hover:-translate-y-1 transition-all duration-200 backdrop-blur-xs">
                <CardContent className="pt-6">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20 mb-4 shadow-xs">
                    <Database className="h-5 w-5" />
                  </div>
                  <h3 className="text-base font-semibold text-slate-900 dark:text-white">
                    Durable PostgreSQL History
                  </h3>
                  <p className="mt-2 text-xs leading-5 text-slate-600 dark:text-zinc-400">
                    Conversations and messages are durably stored in PostgreSQL with
                    authorization enforced across all tenant records.
                  </p>
                </CardContent>
              </Card>
            </div>
          </div>
        </section>
      </main>

      {/* Footer — Seamless integration */}
      <footer className="relative border-t border-slate-200/60 dark:border-zinc-900/80 bg-transparent py-12 transition-colors">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-6 sm:flex-row lg:px-8 text-xs text-slate-500 dark:text-zinc-400">
          <p>© 2026 Cortex Codebase RAG. All rights reserved.</p>
          <div className="flex items-center gap-6">
            <Link href="/sign-in" className="hover:text-slate-900 dark:hover:text-zinc-200 transition-colors">
              Sign In
            </Link>
            <Link href="/dashboard" className="hover:text-slate-900 dark:hover:text-zinc-200 transition-colors">
              Dashboard
            </Link>
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-slate-900 dark:hover:text-zinc-200 transition-colors"
            >
              GitHub
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
