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
    <div className="flex min-h-screen flex-col bg-zinc-950 text-zinc-100 antialiased">
      <Navbar />

      <main className="flex-1">
        {/* Hero Section */}
        <section className="relative overflow-hidden pt-20 pb-24 lg:pt-32 lg:pb-36">
          <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_70%_50%_at_50%_-10%,rgba(99,102,241,0.15),transparent)]" />
          <div className="mx-auto max-w-7xl px-6 lg:px-8 text-center">
            <div className="inline-flex items-center gap-2 rounded-full border border-zinc-800 bg-zinc-900/90 px-3.5 py-1.5 text-xs text-zinc-300">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse motion-reduce:animate-none" />
              <span>Cortex Architecture Baseline V1 Active</span>
            </div>

            <h1 className="mx-auto mt-8 max-w-4xl text-4xl font-extrabold tracking-tight text-white sm:text-6xl lg:text-7xl">
              Retrieval-Augmented Generation for{" "}
              <span className="bg-gradient-to-r from-indigo-400 via-violet-300 to-indigo-200 bg-clip-text text-transparent">
                GitHub Codebases
              </span>
            </h1>

            <p className="mx-auto mt-6 max-w-2xl text-base sm:text-lg leading-8 text-zinc-400">
              Submit any public GitHub repository. Cortex indexes source code using
              Tree-sitter syntax-aware chunking, hybrid vector retrieval with Qdrant,
              and Neo4j code relationship graphs — delivering grounded answers with
              validated line-by-line citations.
            </p>

            <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
              <Link href="/dashboard">
                <Button size="lg" className="gap-2">
                  <span>Open Codebase Dashboard</span>
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
              <Link href="/sign-in">
                <Button variant="outline" size="lg">
                  Sign In with Clerk
                </Button>
              </Link>
            </div>

            {/* Architecture stack preview terminal */}
            <div className="mx-auto mt-16 max-w-3xl rounded-xl border border-zinc-800 bg-zinc-900/80 p-4 text-left shadow-2xl backdrop-blur-md">
              <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                <div className="flex items-center gap-2">
                  <span className="h-3 w-3 rounded-full bg-red-500/80" />
                  <span className="h-3 w-3 rounded-full bg-amber-500/80" />
                  <span className="h-3 w-3 rounded-full bg-emerald-500/80" />
                  <span className="ml-2 font-mono text-xs text-zinc-400">
                    cortex-stack ~ v1.0.0
                  </span>
                </div>
                <Badge variant="indigo">Verified Engine</Badge>
              </div>
              <div className="pt-3 font-mono text-xs leading-6 text-zinc-300">
                <p className="text-zinc-500"># Phase 1 &amp; Phase 2 foundation active</p>
                <p>
                  <span className="text-indigo-400">GET</span> /api/v1/health{" "}
                  <span className="text-emerald-400">→ 200 OK</span>{" "}
                  <span className="text-zinc-500">[PostgreSQL 16, Redis 7, Qdrant, Neo4j]</span>
                </p>
                <p>
                  <span className="text-indigo-400">AUTH</span> Clerk Session{" "}
                  <span className="text-emerald-400">→ Active</span>{" "}
                  <span className="text-zinc-500">[Server-side token verification]</span>
                </p>
                <p>
                  <span className="text-indigo-400">ROUTER</span> Protected /dashboard{" "}
                  <span className="text-emerald-400">→ Armed</span>
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Feature Grid */}
        <section className="border-t border-zinc-800/60 bg-zinc-950/60 py-20">
          <div className="mx-auto max-w-7xl px-6 lg:px-8">
            <div className="text-center">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-indigo-400">
                Architectural Capabilities
              </h2>
              <p className="mt-2 text-3xl font-bold tracking-tight text-white sm:text-4xl">
                Engineered for precision and reproducibility
              </p>
            </div>

            <div className="mt-14 grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
              <Card className="hover:border-zinc-700 transition-colors">
                <CardContent className="pt-6">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 mb-4">
                    <Terminal className="h-5 w-5" />
                  </div>
                  <h3 className="text-base font-semibold text-white">
                    Tree-sitter Syntax Chunking
                  </h3>
                  <p className="mt-2 text-xs leading-5 text-zinc-400">
                    AST-aware boundaries preserve functions, classes, and scopes. No
                    arbitrary character splits that destroy context.
                  </p>
                </CardContent>
              </Card>

              <Card className="hover:border-zinc-700 transition-colors">
                <CardContent className="pt-6">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 mb-4">
                    <Search className="h-5 w-5" />
                  </div>
                  <h3 className="text-base font-semibold text-white">
                    Qdrant Vector Retrieval
                  </h3>
                  <p className="mt-2 text-xs leading-5 text-zinc-400">
                    Dense semantic embeddings filtered strictly by repository ownership
                    and immutable commit SHA to guarantee zero cross-repo leakage.
                  </p>
                </CardContent>
              </Card>

              <Card className="hover:border-zinc-700 transition-colors">
                <CardContent className="pt-6">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20 mb-4">
                    <GitBranch className="h-5 w-5" />
                  </div>
                  <h3 className="text-base font-semibold text-white">
                    Neo4j Code Relationship Graph
                  </h3>
                  <p className="mt-2 text-xs leading-5 text-zinc-400">
                    Indexes imports, inheritance hierarchies, and function call chains
                    to trace multi-file dependencies reliably.
                  </p>
                </CardContent>
              </Card>

              <Card className="hover:border-zinc-700 transition-colors">
                <CardContent className="pt-6">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-violet-500/10 text-violet-400 border border-violet-500/20 mb-4">
                    <Layers className="h-5 w-5" />
                  </div>
                  <h3 className="text-base font-semibold text-white">
                    LangGraph Workflow
                  </h3>
                  <p className="mt-2 text-xs leading-5 text-zinc-400">
                    Multi-step agent graph coordinating question understanding,
                    retrieval grading, citation generation, and hallucination checks.
                  </p>
                </CardContent>
              </Card>

              <Card className="hover:border-zinc-700 transition-colors">
                <CardContent className="pt-6">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 mb-4">
                    <ShieldCheck className="h-5 w-5" />
                  </div>
                  <h3 className="text-base font-semibold text-white">
                    Strict Line-Level Citations
                  </h3>
                  <p className="mt-2 text-xs leading-5 text-zinc-400">
                    Every answer references exact file paths and line ranges backed by
                    the retrieved commit SHA. Never invented, never hallucinated.
                  </p>
                </CardContent>
              </Card>

              <Card className="hover:border-zinc-700 transition-colors">
                <CardContent className="pt-6">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20 mb-4">
                    <Database className="h-5 w-5" />
                  </div>
                  <h3 className="text-base font-semibold text-white">
                    Durable PostgreSQL History
                  </h3>
                  <p className="mt-2 text-xs leading-5 text-zinc-400">
                    Conversations and messages are durably stored in PostgreSQL with
                    authorization enforced across all tenant records.
                  </p>
                </CardContent>
              </Card>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-900 bg-zinc-950 py-10">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-6 sm:flex-row lg:px-8 text-xs text-zinc-400">
          <p>© 2026 Cortex Codebase RAG. All rights reserved.</p>
          <div className="flex items-center gap-6">
            <Link href="/sign-in" className="hover:text-zinc-200">
              Sign In
            </Link>
            <Link href="/dashboard" className="hover:text-zinc-200">
              Dashboard
            </Link>
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-zinc-200"
            >
              GitHub
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
