"use client";

import React, { memo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { CodeBlock } from "@/components/chat/code-block";
import { MermaidDiagram } from "@/components/chat/mermaid-diagram";
import { ExternalLink, Hash, Loader2, GitFork } from "lucide-react";

interface MarkdownRendererProps {
  content: string;
  isStreaming?: boolean;
}

/**
 * Detects whether a markdown string has an open (unclosed) mermaid code fence.
 * Returns { cleanContent, hasOpenMermaid }.
 * - cleanContent: content with the incomplete mermaid block removed
 * - hasOpenMermaid: true if we stripped an incomplete block
 */
function stripIncompleteMermaidBlocks(content: string): {
  cleanContent: string;
  hasOpenMermaid: boolean;
} {
  const fencePattern = /```(\w*)\n/g;

  let lastMermaidStart = -1;
  let match: RegExpExecArray | null;

  while ((match = fencePattern.exec(content)) !== null) {
    if (match[1].toLowerCase() === "mermaid") {
      lastMermaidStart = match.index;
    }
  }

  if (lastMermaidStart === -1) {
    return { cleanContent: content, hasOpenMermaid: false };
  }

  // Check if this last mermaid block has a closing fence
  const afterOpenFence = content.slice(lastMermaidStart);
  const lines = afterOpenFence.split("\n");
  let hasClosure = false;
  for (let i = 1; i < lines.length; i++) {
    if (/^```\s*$/.test(lines[i])) {
      hasClosure = true;
      break;
    }
  }

  if (hasClosure) {
    return { cleanContent: content, hasOpenMermaid: false };
  }

  // Strip the incomplete mermaid block
  const cleanContent = content.slice(0, lastMermaidStart);
  return { cleanContent, hasOpenMermaid: true };
}

// Generate URL slug for heading anchor links
function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, "")
    .replace(/\s+/g, "-")
    .slice(0, 50);
}

// Check whether a link URL is safe to render
function isSafeUrl(url?: string): boolean {
  if (!url) return false;
  const trimmed = url.trim().toLowerCase();
  return (
    trimmed.startsWith("http://") ||
    trimmed.startsWith("https://") ||
    trimmed.startsWith("/") ||
    trimmed.startsWith("#") ||
    trimmed.startsWith("mailto:")
  );
}

/** Placeholder shown while a mermaid block is still being streamed */
function MermaidStreamingPlaceholder() {
  return (
    <div className="my-5 rounded-xl border border-slate-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 overflow-hidden shadow-xs transition-colors">
      <div className="flex items-center gap-2 px-4 py-2.5 bg-slate-50 dark:bg-zinc-900/90 border-b border-slate-200 dark:border-zinc-800/80">
        <div className="p-1 rounded bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
          <GitFork className="h-3.5 w-3.5" />
        </div>
        <span className="text-xs font-semibold text-slate-800 dark:text-zinc-200">
          Architecture Diagram
        </span>
        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono uppercase bg-slate-100 text-slate-600 border border-slate-200 dark:bg-zinc-800 dark:text-zinc-400 dark:border-zinc-700/50">
          Mermaid
        </span>
      </div>
      <div className="flex flex-col items-center justify-center p-8 gap-2.5 text-slate-500 dark:text-zinc-500 text-xs min-h-[120px]">
        <Loader2 className="h-5 w-5 animate-spin text-indigo-600 dark:text-indigo-400" />
        <span className="text-slate-600 dark:text-zinc-400">Building diagram — waiting for complete data…</span>
      </div>
    </div>
  );
}

function RawMarkdownRenderer({ content, isStreaming }: MarkdownRendererProps) {
  // During streaming, strip incomplete mermaid blocks to avoid failed renders
  const { cleanContent, hasOpenMermaid } = isStreaming
    ? stripIncompleteMermaidBlocks(content)
    : { cleanContent: content, hasOpenMermaid: false };

  return (
    <>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // ── Code & Diagrams ───────────────────────────────────────
          pre: ({ children }) => <>{children}</>,
          code({ className, children, ...props }) {
            const isInline = !className;
            const language = className?.replace("language-", "") ?? "";
            const codeStr = String(children).replace(/\n$/, "");

            if (isInline) {
              return (
                <code
                  className="px-1.5 py-0.5 rounded-md text-[0.84em] font-mono bg-slate-100 text-indigo-700 border border-slate-200/90 dark:bg-zinc-800 dark:text-indigo-200 dark:border-zinc-700/80 font-medium select-text break-all transition-colors"
                  {...props}
                >
                  {children}
                </code>
              );
            }

            // Render Mermaid diagrams for mermaid-fenced blocks
            if (language.toLowerCase() === "mermaid") {
              return <MermaidDiagram chart={codeStr} />;
            }

            // Syntax-highlighted code block for programming languages
            return <CodeBlock language={language} code={codeStr} />;
          },

          // ── Headings with Visual Hierarchy & Anchor IDs ──────────
          h1: ({ children }) => {
            const text = String(children);
            const slug = slugify(text);
            return (
              <h1
                id={slug}
                className="group flex items-center gap-2 text-lg font-bold text-slate-900 dark:text-white mt-7 mb-3.5 pb-2 border-b border-slate-200 dark:border-zinc-800 tracking-tight first:mt-0"
              >
                <span>{children}</span>
                <a
                  href={`#${slug}`}
                  aria-label={`Link to ${text}`}
                  className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-indigo-600 dark:text-zinc-500 dark:hover:text-indigo-400 transition-opacity"
                >
                  <Hash className="h-4 w-4" />
                </a>
              </h1>
            );
          },
          h2: ({ children }) => {
            const text = String(children);
            const slug = slugify(text);
            return (
              <h2
                id={slug}
                className="group flex items-center gap-2 text-base font-semibold text-slate-800 dark:text-zinc-100 mt-6 mb-2.5 pb-1 border-b border-slate-200/80 dark:border-zinc-800/60 tracking-tight first:mt-0"
              >
                <span>{children}</span>
                <a
                  href={`#${slug}`}
                  aria-label={`Link to ${text}`}
                  className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-indigo-600 dark:text-zinc-500 dark:hover:text-indigo-400 transition-opacity"
                >
                  <Hash className="h-3.5 w-3.5" />
                </a>
              </h2>
            );
          },
          h3: ({ children }) => (
            <h3 className="text-sm font-semibold text-slate-800 dark:text-zinc-200 mt-5 mb-2 first:mt-0 tracking-tight">
              {children}
            </h3>
          ),
          h4: ({ children }) => (
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-zinc-400 mt-4 mb-1.5 first:mt-0">
              {children}
            </h4>
          ),

          // ── Paragraphs & Spacing ──────────────────────────────────
          p: ({ children }) => (
            <p className="text-sm leading-relaxed text-slate-800 dark:text-zinc-200 mb-3.5 last:mb-0">
              {children}
            </p>
          ),

          // ── Lists with Proper Nesting and Indentation ────────────
          ul: ({ children }) => (
            <ul className="list-disc pl-6 space-y-1.5 my-3 text-sm text-slate-800 dark:text-zinc-200">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal pl-6 space-y-1.5 my-3 text-sm text-slate-800 dark:text-zinc-200">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="text-sm text-slate-800 dark:text-zinc-200 leading-relaxed pl-1 marker:text-indigo-600 dark:marker:text-indigo-400">
              {children}
            </li>
          ),

          // ── Blockquotes ───────────────────────────────────────────
          blockquote: ({ children }) => (
            <blockquote className="my-4 border-l-2 border-indigo-500 bg-indigo-50/70 dark:border-indigo-500/70 dark:bg-indigo-950/20 px-4 py-2.5 rounded-r-lg text-slate-700 dark:text-zinc-300 italic text-sm">
              {children}
            </blockquote>
          ),

          // ── Tables ────────────────────────────────────────────────
          table: ({ children }) => (
            <div className="my-4 w-full overflow-x-auto rounded-xl border border-slate-200 dark:border-zinc-800 bg-white/90 dark:bg-zinc-950/70 shadow-xs">
              <table className="w-full border-collapse text-left text-xs leading-normal">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="border-b border-slate-200 dark:border-zinc-800 bg-slate-50 dark:bg-zinc-900/90 text-slate-700 dark:text-zinc-300 font-semibold uppercase tracking-wider text-[11px]">
              {children}
            </thead>
          ),
          tbody: ({ children }) => (
            <tbody className="divide-y divide-slate-200 dark:divide-zinc-800/60 text-slate-700 dark:text-zinc-300">
              {children}
            </tbody>
          ),
          tr: ({ children }) => (
            <tr className="transition-colors hover:bg-slate-50 dark:hover:bg-zinc-800/40">
              {children}
            </tr>
          ),
          th: ({ children, style }) => (
            <th
              style={style}
              className="px-4 py-3 font-semibold text-slate-800 dark:text-zinc-200 border-r border-slate-200 dark:border-zinc-800/40 last:border-r-0 whitespace-nowrap"
            >
              {children}
            </th>
          ),
          td: ({ children, style }) => (
            <td
              style={style}
              className="px-4 py-2.5 text-slate-700 dark:text-zinc-300 border-r border-slate-200 dark:border-zinc-800/30 last:border-r-0 whitespace-normal break-words"
            >
              {children}
            </td>
          ),

          // ── Dividers ──────────────────────────────────────────────
          hr: () => <hr className="my-6 border-slate-200 dark:border-zinc-800" />,

          // ── Links ─────────────────────────────────────────────────
          a: ({ href, children }) => {
            const safe = isSafeUrl(href);
            if (!safe) {
              return <span>{children}</span>;
            }
            const isExternal = href?.startsWith("http://") || href?.startsWith("https://");
            return (
              <a
                href={href}
                target={isExternal ? "_blank" : undefined}
                rel={isExternal ? "noopener noreferrer" : undefined}
                className="inline-flex items-center gap-1 text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300 underline underline-offset-2 transition-colors font-medium"
              >
                <span>{children}</span>
                {isExternal && <ExternalLink className="h-3 w-3 shrink-0" />}
              </a>
            );
          },

          // ── Emphasis & Strong ─────────────────────────────────────
          strong: ({ children }) => (
            <strong className="font-semibold text-slate-900 dark:text-white">{children}</strong>
          ),
          em: ({ children }) => (
            <em className="italic text-slate-700 dark:text-zinc-300">{children}</em>
          ),
        }}
      >
        {cleanContent}
      </ReactMarkdown>
      {isStreaming && hasOpenMermaid && <MermaidStreamingPlaceholder />}
    </>
  );
}

export const MarkdownRenderer = memo(RawMarkdownRenderer);
