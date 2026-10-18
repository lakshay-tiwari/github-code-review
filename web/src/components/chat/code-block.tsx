"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";
import hljs from "highlight.js";

interface CodeBlockProps {
  language?: string;
  code: string;
}

export function CodeBlock({ language, code }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const cleanCode = code.replace(/\n$/, "");
  const lang = language ? language.toLowerCase().trim() : "";

  // Highlight syntax using highlight.js
  let highlightedHtml: string;
  try {
    if (lang && hljs.getLanguage(lang)) {
      highlightedHtml = hljs.highlight(cleanCode, { language: lang, ignoreIllegals: true }).value;
    } else {
      highlightedHtml = hljs.highlightAuto(cleanCode).value;
    }
  } catch {
    // Fallback if highlight fails
    highlightedHtml = cleanCode
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(cleanCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
    }
  };

  return (
    <div className="relative my-4 group/code rounded-xl overflow-hidden border border-zinc-800 bg-zinc-950 shadow-sm">
      {/* Code block header bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-zinc-900/90 border-b border-zinc-800/80 text-xs">
        <span className="font-mono text-[11px] font-medium tracking-wider text-zinc-400 uppercase">
          {lang || "code"}
        </span>
        <button
          onClick={handleCopy}
          type="button"
          aria-label="Copy code"
          className="flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] font-medium text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition-colors"
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5 text-emerald-400" />
              <span className="text-emerald-400">Copied</span>
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5 text-zinc-400 group-hover/code:text-zinc-200" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>

      {/* Code body */}
      <pre className="overflow-x-auto p-4 text-xs font-mono leading-relaxed text-zinc-200 selection:bg-indigo-500/30">
        <code
          className={`hljs ${lang ? `language-${lang}` : ""}`}
          dangerouslySetInnerHTML={{ __html: highlightedHtml }}
        />
      </pre>
    </div>
  );
}
