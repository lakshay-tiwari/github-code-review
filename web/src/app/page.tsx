export default function Home() {
  return (
    <div className="flex min-h-screen flex-col bg-zinc-950 text-zinc-100 antialiased selection:bg-indigo-500 selection:text-white">
      {/* Navigation header */}
      <header className="border-b border-zinc-800/80 bg-zinc-950/70 backdrop-blur-md sticky top-0 z-50">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-tr from-indigo-600 to-violet-500 font-mono font-bold text-white shadow-lg shadow-indigo-500/20">
              C
            </div>
            <span className="text-lg font-semibold tracking-tight text-white">
              Cortex
            </span>
            <span className="rounded-full border border-indigo-500/30 bg-indigo-500/10 px-2.5 py-0.5 text-xs font-medium text-indigo-300">
              Phase 1 Foundation
            </span>
          </div>

          <div className="flex items-center gap-4">
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-zinc-400 transition-colors hover:text-zinc-200"
            >
              GitHub Codebase RAG
            </a>
          </div>
        </div>
      </header>

      {/* Hero section */}
      <main className="flex-1">
        <section className="relative overflow-hidden pt-20 pb-28">
          <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_80%_60%_at_50%_-20%,rgba(99,102,241,0.18),transparent)]" />
          <div className="mx-auto max-w-4xl px-6 text-center lg:px-8">
            <div className="inline-flex items-center gap-2 rounded-full border border-zinc-800 bg-zinc-900/80 px-3.5 py-1.5 text-xs text-zinc-300 backdrop-blur-sm">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>Project Foundation &amp; Local Infrastructure Active</span>
            </div>

            <h1 className="mt-8 text-4xl font-extrabold tracking-tight text-white sm:text-6xl">
              Chat with any public GitHub codebase.
            </h1>

            <p className="mt-6 text-lg leading-8 text-zinc-400">
              Syntax-aware Tree-sitter code chunking, hybrid Qdrant vector retrieval,
              Neo4j relationship graphs, and LangGraph workflow orchestration with
              strict citations.
            </p>

            <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
              <div className="flex items-center gap-2 rounded-lg border border-zinc-800 bg-zinc-900/90 px-4 py-2.5 text-sm font-mono text-zinc-300">
                <span className="text-zinc-500">$</span>
                <span>docker compose up -d</span>
              </div>
              <div className="flex items-center gap-2 rounded-lg border border-zinc-800 bg-zinc-900/90 px-4 py-2.5 text-sm font-mono text-zinc-300">
                <span className="text-zinc-500">$</span>
                <span>uvicorn app.main:app --reload</span>
              </div>
            </div>
          </div>
        </section>

        {/* Core Architecture Cards */}
        <section className="border-t border-zinc-900 bg-zinc-950/50 py-16">
          <div className="mx-auto max-w-7xl px-6 lg:px-8">
            <h2 className="text-center text-sm font-semibold uppercase tracking-wider text-zinc-400">
              Phase 1 Core Infrastructure Stack
            </h2>
            <div className="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-6">
                <div className="text-sm font-mono font-semibold text-indigo-400">
                  PostgreSQL 16
                </div>
                <div className="mt-1 text-xs text-zinc-400">Port 5432</div>
                <p className="mt-3 text-xs leading-5 text-zinc-400">
                  Durable relational storage for repositories, indexing jobs, conversations, and messages.
                </p>
              </div>

              <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-6">
                <div className="text-sm font-mono font-semibold text-rose-400">
                  Redis 7
                </div>
                <div className="mt-1 text-xs text-zinc-400">Port 6379</div>
                <p className="mt-3 text-xs leading-5 text-zinc-400">
                  Asynchronous task broker and result backend for Celery ingestion workers.
                </p>
              </div>

              <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-6">
                <div className="text-sm font-mono font-semibold text-cyan-400">
                  Qdrant Vector DB
                </div>
                <div className="mt-1 text-xs text-zinc-400">Port 6333 / 6334</div>
                <p className="mt-3 text-xs leading-5 text-zinc-400">
                  High-performance semantic vector index with payload filters for repo and commit SHA.
                </p>
              </div>

              <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-6">
                <div className="text-sm font-mono font-semibold text-amber-400">
                  Neo4j Graph DB
                </div>
                <div className="mt-1 text-xs text-zinc-400">Port 7474 / 7687</div>
                <p className="mt-3 text-xs leading-5 text-zinc-400">
                  Code symbol graph indexing imports, dependencies, call hierarchies, and long-term memory.
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-900 py-8 text-center text-xs text-zinc-400">
        <p>Cortex Codebase RAG • Clean Modular Architecture</p>
      </footer>
    </div>
  );
}
