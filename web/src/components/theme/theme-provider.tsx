"use client";

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  useMemo,
} from "react";

export type Theme = "dark" | "light" | "system";
export type ResolvedTheme = "dark" | "light";

interface ThemeContextValue {
  theme: Theme;
  resolvedTheme: ResolvedTheme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
}

const THEME_STORAGE_KEY = "cortex-theme";

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

function getSystemTheme(): ResolvedTheme {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return "dark";
  }
  try {
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  } catch {
    return "dark";
  }
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("dark");
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>("dark");
  const [mounted, setMounted] = useState(false);

  // Initialize theme from storage or system on mount
  useEffect(() => {
    let initialTheme: Theme = "dark";
    try {
      const stored = localStorage.getItem(THEME_STORAGE_KEY) as Theme | null;
      if (stored === "dark" || stored === "light" || stored === "system") {
        initialTheme = stored;
      } else {
        // Default to dark mode to preserve existing primary identity
        initialTheme = "dark";
      }
    } catch {
      // Storage unavailable
    }

    const sysTheme = getSystemTheme();
    const resolved = initialTheme === "system" ? sysTheme : initialTheme;

    setThemeState(initialTheme);
    setResolvedTheme(resolved);

    // Apply to html element
    const root = document.documentElement;
    if (resolved === "dark") {
      root.classList.add("dark");
      root.classList.remove("light");
    } else {
      root.classList.remove("dark");
      root.classList.add("light");
    }

    setMounted(true);
  }, []);

  // Update theme and persist
  const setTheme = useCallback((newTheme: Theme) => {
    setThemeState(newTheme);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, newTheme);
    } catch {
      // Storage unavailable
    }

    const sysTheme = getSystemTheme();
    const resolved = newTheme === "system" ? sysTheme : newTheme;
    setResolvedTheme(resolved);

    const root = document.documentElement;
    if (resolved === "dark") {
      root.classList.add("dark");
      root.classList.remove("light");
    } else {
      root.classList.remove("dark");
      root.classList.add("light");
    }

    // Dispatch custom event for canvas/SVG listeners (e.g., Mermaid)
    if (typeof window !== "undefined") {
      window.dispatchEvent(
        new CustomEvent("cortex-theme-change", { detail: { theme: newTheme, resolvedTheme: resolved } })
      );
    }
  }, []);

  // Simple toggle between light and dark
  const toggleTheme = useCallback(() => {
    setTheme(resolvedTheme === "dark" ? "light" : "dark");
  }, [resolvedTheme, setTheme]);

  // Listen to system preference changes when in 'system' mode
  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return;
    }
    try {
      const media = window.matchMedia("(prefers-color-scheme: dark)");

      const handleChange = (e: MediaQueryListEvent) => {
        if (theme === "system") {
          const nextResolved: ResolvedTheme = e.matches ? "dark" : "light";
          setResolvedTheme(nextResolved);
          const root = document.documentElement;
          if (nextResolved === "dark") {
            root.classList.add("dark");
            root.classList.remove("light");
          } else {
            root.classList.remove("dark");
            root.classList.add("light");
          }
          window.dispatchEvent(
            new CustomEvent("cortex-theme-change", {
              detail: { theme: "system", resolvedTheme: nextResolved },
            })
          );
        }
      };

      media.addEventListener("change", handleChange);
      return () => media.removeEventListener("change", handleChange);
    } catch {
      // ignore
    }
  }, [theme]);

  const value = useMemo(
    () => ({
      theme,
      resolvedTheme: mounted ? resolvedTheme : "dark",
      setTheme,
      toggleTheme,
    }),
    [theme, resolvedTheme, mounted, setTheme, toggleTheme]
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (!context) {
    return {
      theme: "dark",
      resolvedTheme: "dark",
      setTheme: () => {},
      toggleTheme: () => {},
    };
  }
  return context;
}
