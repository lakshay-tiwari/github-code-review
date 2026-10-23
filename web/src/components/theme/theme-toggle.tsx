"use client";

import React, { useEffect, useState } from "react";
import { Sun, Moon } from "lucide-react";
import { useTheme } from "@/components/theme/theme-provider";

export interface ThemeToggleProps {
  className?: string;
  size?: "sm" | "md";
}

export function ThemeToggle({ className = "", size = "md" }: ThemeToggleProps) {
  const { resolvedTheme, toggleTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const isDark = mounted ? resolvedTheme === "dark" : true;

  const sizeClasses =
    size === "sm"
      ? "h-8 w-8 text-xs"
      : "h-9 w-9 text-sm";

  const iconSize = size === "sm" ? "h-4 w-4" : "h-4.5 w-4.5";

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
      title={isDark ? "Switch to light theme (Cmd/Ctrl+Shift+T)" : "Switch to dark theme (Cmd/Ctrl+Shift+T)"}
      className={`relative inline-flex items-center justify-center rounded-lg border transition-all duration-200 cursor-pointer select-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 ${sizeClasses} ${
        isDark
          ? "border-zinc-800 bg-zinc-900/90 text-zinc-300 hover:text-white hover:bg-zinc-800 hover:border-zinc-700 active:bg-zinc-800 shadow-xs focus-visible:ring-offset-zinc-950"
          : "border-slate-200/90 bg-white/90 text-slate-700 hover:text-slate-900 hover:bg-slate-50 hover:border-slate-300 active:bg-slate-100 shadow-xs shadow-slate-200/60 focus-visible:ring-offset-white"
      } ${className}`}
    >
      <span className="sr-only">Toggle theme</span>

      {/* Sun Icon (Visible in dark mode to indicate switching to light) */}
      <Sun
        className={`${iconSize} transition-all duration-300 ${
          isDark
            ? "rotate-0 scale-100 opacity-100 text-amber-400/90"
            : "-rotate-90 scale-0 opacity-0 absolute"
        }`}
      />

      {/* Moon Icon (Visible in light mode to indicate switching to dark) */}
      <Moon
        className={`${iconSize} transition-all duration-300 ${
          isDark
            ? "rotate-90 scale-0 opacity-0 absolute"
            : "rotate-0 scale-100 opacity-100 text-indigo-600"
        }`}
      />
    </button>
  );
}
