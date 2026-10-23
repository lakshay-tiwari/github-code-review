"use client";

import { useEffect, useState, useRef } from "react";
import {
  GitFork,
  Code2,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Copy,
  Check,
  AlertTriangle,
  Loader2,
} from "lucide-react";
import { sanitizeMermaidChart } from "@/lib/mermaid-sanitizer";

interface MermaidDiagramProps {
  chart: string;
}

function cleanupMermaidDom(id: string) {
  if (typeof document === "undefined") return;
  const el = document.getElementById(id);
  if (el) el.remove();
  const dEl = document.getElementById("d" + id);
  if (dEl) dEl.remove();
  document.querySelectorAll('svg[id^="dmermaid-"]').forEach((node) => node.remove());
  document.querySelectorAll('div[id^="dmermaid-"]').forEach((node) => node.remove());
  document.querySelectorAll('svg[id^="mermaid-"]').forEach((node) => {
    if (node.textContent?.includes("Syntax error in text")) {
      node.remove();
    }
  });
}

export function MermaidDiagram({ chart }: MermaidDiagramProps) {
  const cleanChart = chart.trim();
  const [svg, setSvg] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(() => Boolean(cleanChart));
  const [error, setError] = useState<string | null>(null);
  const [showSource, setShowSource] = useState<boolean>(false);
  const [zoom, setZoom] = useState<number>(1);
  const [copied, setCopied] = useState<boolean>(false);
  const [retryCount, setRetryCount] = useState<number>(0);
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Listen to theme changes to re-render diagram with matching palette
  const [themeVersion, setThemeVersion] = useState(0);
  useEffect(() => {
    const handleThemeChange = () => {
      setThemeVersion((v) => v + 1);
    };
    window.addEventListener("cortex-theme-change", handleThemeChange);
    return () => window.removeEventListener("cortex-theme-change", handleThemeChange);
  }, []);

  useEffect(() => {
    let isMounted = true;

    const renderChart = async () => {
      setIsLoading(true);
      setError(null);

      const baseId = `mermaid-${Math.random().toString(36).substring(2, 9)}`;
      const isDark = typeof document !== "undefined" && document.documentElement.classList.contains("dark");

      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({
          startOnLoad: false,
          theme: isDark ? "dark" : "neutral",
          securityLevel: "loose",
          suppressErrorRendering: true,
          fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
          themeVariables: isDark
            ? {
                darkMode: true,
                background: "#09090b",
                primaryColor: "#4f46e5",
                primaryTextColor: "#f4f4f5",
                primaryBorderColor: "#6366f1",
                lineColor: "#818cf8",
                secondaryColor: "#18181b",
                tertiaryColor: "#27272a",
                noteBkgColor: "#1e1b4b",
                noteTextColor: "#e0e7ff",
                noteBorderColor: "#4338ca",
              }
            : {
                darkMode: false,
                background: "#ffffff",
                primaryColor: "#e0e7ff",
                primaryTextColor: "#0f172a",
                primaryBorderColor: "#4f46e5",
                lineColor: "#4f46e5",
                secondaryColor: "#f1f5f9",
                tertiaryColor: "#f8fafc",
                noteBkgColor: "#eef2ff",
                noteTextColor: "#312e81",
                noteBorderColor: "#818cf8",
              },
        });

        let renderedSvg: string;

        try {
          const res = await mermaid.render(baseId, cleanChart);
          renderedSvg = res.svg;
        } catch {
          cleanupMermaidDom(baseId);
          const sanitized = sanitizeMermaidChart(cleanChart);
          const retryId = `${baseId}-retry`;
          const res = await mermaid.render(retryId, sanitized);
          renderedSvg = res.svg;
        }

        if (isMounted) {
          setSvg(renderedSvg);
          setError(null);
          setIsLoading(false);
        }
      } catch (err: unknown) {
        cleanupMermaidDom(baseId);
        if (isMounted) {
          const errMsg = err instanceof Error ? err.message : String(err);
          setError(errMsg);
          setIsLoading(false);
        }
      }
    };

    if (cleanChart) {
      renderChart();
    }

    return () => {
      isMounted = false;
    };
  }, [cleanChart, retryCount, themeVersion]);

  const handleRetry = () => {
    setSvg(null);
    setError(null);
    setRetryCount((c) => c + 1);
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(cleanChart);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
    }
  };

  const handleZoomIn = () => setZoom((prev) => Math.min(prev + 0.2, 2.0));
  const handleZoomOut = () => setZoom((prev) => Math.max(prev - 0.2, 0.6));
  const handleZoomReset = () => setZoom(1);

  return (
    <div className="my-5 rounded-xl border border-slate-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 overflow-hidden shadow-xs transition-colors">
      {/* Header Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-2.5 bg-slate-50 dark:bg-zinc-900/90 border-b border-slate-200 dark:border-zinc-800/80">
        <div className="flex items-center gap-2">
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

        {/* Action Controls */}
        <div className="flex items-center gap-1">
          {!showSource && svg && !error && (
            <div className="flex items-center gap-0.5 mr-2 border-r border-slate-200 dark:border-zinc-800 pr-2">
              <button
                type="button"
                onClick={handleZoomOut}
                aria-label="Zoom out"
                title="Zoom out"
                className="p-1 rounded text-slate-500 hover:text-slate-900 hover:bg-slate-200 dark:text-zinc-400 dark:hover:text-white dark:hover:bg-zinc-800 transition-colors cursor-pointer"
              >
                <ZoomOut className="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                onClick={handleZoomReset}
                title="Reset zoom"
                className="px-1.5 py-0.5 text-[10px] font-mono text-slate-500 hover:text-slate-900 hover:bg-slate-200 dark:text-zinc-400 dark:hover:text-white dark:hover:bg-zinc-800 rounded transition-colors cursor-pointer"
              >
                {Math.round(zoom * 100)}%
              </button>
              <button
                type="button"
                onClick={handleZoomIn}
                aria-label="Zoom in"
                title="Zoom in"
                className="p-1 rounded text-slate-500 hover:text-slate-900 hover:bg-slate-200 dark:text-zinc-400 dark:hover:text-white dark:hover:bg-zinc-800 transition-colors cursor-pointer"
              >
                <ZoomIn className="h-3.5 w-3.5" />
              </button>
              {zoom !== 1 && (
                <button
                  type="button"
                  onClick={handleZoomReset}
                  title="Reset"
                  className="p-1 rounded text-slate-500 hover:text-slate-900 hover:bg-slate-200 dark:text-zinc-400 dark:hover:text-white dark:hover:bg-zinc-800 transition-colors cursor-pointer"
                >
                  <RotateCcw className="h-3 w-3" />
                </button>
              )}
            </div>
          )}

          <button
            type="button"
            onClick={() => setShowSource((prev) => !prev)}
            className="flex items-center gap-1 px-2 py-1 rounded text-[11px] text-slate-600 hover:text-slate-900 hover:bg-slate-200/80 dark:text-zinc-400 dark:hover:text-white dark:hover:bg-zinc-800 transition-colors cursor-pointer"
          >
            <Code2 className="h-3.5 w-3.5" />
            <span>{showSource ? "Diagram" : "Source"}</span>
          </button>

          <button
            type="button"
            onClick={handleCopy}
            className="flex items-center gap-1 px-2 py-1 rounded text-[11px] text-slate-600 hover:text-slate-900 hover:bg-slate-200/80 dark:text-zinc-400 dark:hover:text-white dark:hover:bg-zinc-800 transition-colors cursor-pointer"
            title="Copy diagram source"
          >
            {copied ? (
              <>
                <Check className="h-3.5 w-3.5 text-emerald-500" />
                <span className="text-emerald-600 dark:text-emerald-400">Copied</span>
              </>
            ) : (
              <>
                <Copy className="h-3.5 w-3.5" />
                <span>Copy</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Diagram Body */}
      {showSource || error ? (
        <div className="p-4 bg-slate-900 dark:bg-zinc-950 font-mono text-xs">
          {error && (
            <div className="flex items-center justify-between gap-2 mb-3 px-3 py-2 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                <span>Diagram preview unavailable due to syntax. Displaying raw source:</span>
              </div>
              <button
                type="button"
                onClick={handleRetry}
                className="flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium text-amber-200 hover:text-white bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 transition-colors cursor-pointer shrink-0"
              >
                <RotateCcw className="h-3 w-3" />
                <span>Retry</span>
              </button>
            </div>
          )}
          <pre className="overflow-x-auto text-slate-200 dark:text-zinc-300 leading-relaxed">
            <code>{cleanChart}</code>
          </pre>
        </div>
      ) : isLoading && !svg ? (
        <div className="flex flex-col items-center justify-center p-8 gap-2.5 text-slate-500 dark:text-zinc-500 text-xs min-h-[140px]">
          <Loader2 className="h-5 w-5 animate-spin text-indigo-600 dark:text-indigo-400" />
          <span>Rendering architecture diagram…</span>
        </div>
      ) : svg ? (
        <div
          ref={containerRef}
          className="relative overflow-x-auto p-6 bg-slate-50/50 dark:bg-zinc-950/70 flex justify-center items-center min-h-[160px]"
        >
          <div
            className="w-full flex justify-center items-center [&_svg]:max-w-full [&_svg]:h-auto transition-transform duration-150 origin-top"
            style={{ transform: `scale(${zoom})` }}
            dangerouslySetInnerHTML={{ __html: svg }}
          />
        </div>
      ) : (
        <div className="p-4 text-xs text-slate-500 dark:text-zinc-500">No diagram data</div>
      )}
    </div>
  );
}
