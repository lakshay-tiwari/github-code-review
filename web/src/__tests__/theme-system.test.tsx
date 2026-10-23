import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import React from "react";
import { ThemeProvider, useTheme } from "@/components/theme/theme-provider";
import { ThemeToggle } from "@/components/theme/theme-toggle";

function TestConsumer() {
  const { theme, resolvedTheme, setTheme, toggleTheme } = useTheme();
  return (
    <div>
      <span data-testid="theme">{theme}</span>
      <span data-testid="resolvedTheme">{resolvedTheme}</span>
      <button data-testid="set-light" onClick={() => setTheme("light")}>
        Light
      </button>
      <button data-testid="set-dark" onClick={() => setTheme("dark")}>
        Dark
      </button>
      <button data-testid="toggle" onClick={toggleTheme}>
        Toggle
      </button>
    </div>
  );
}

describe("Dual-Theme System", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove("dark", "light");
    vi.clearAllMocks();
  });

  it("initializes with dark mode by default when no storage exists", () => {
    render(
      <ThemeProvider>
        <TestConsumer />
      </ThemeProvider>
    );

    expect(screen.getByTestId("theme").textContent).toBe("dark");
    expect(screen.getByTestId("resolvedTheme").textContent).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("loads stored theme from localStorage", () => {
    localStorage.setItem("cortex-theme", "light");

    render(
      <ThemeProvider>
        <TestConsumer />
      </ThemeProvider>
    );

    expect(screen.getByTestId("theme").textContent).toBe("light");
    expect(screen.getByTestId("resolvedTheme").textContent).toBe("light");
    expect(document.documentElement.classList.contains("light")).toBe(true);
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("switches theme, updates DOM classes and saves to localStorage", () => {
    const themeEventListener = vi.fn();
    window.addEventListener("cortex-theme-change", themeEventListener);

    render(
      <ThemeProvider>
        <TestConsumer />
      </ThemeProvider>
    );

    // Switch to light
    act(() => {
      fireEvent.click(screen.getByTestId("set-light"));
    });

    expect(screen.getByTestId("resolvedTheme").textContent).toBe("light");
    expect(document.documentElement.classList.contains("light")).toBe(true);
    expect(document.documentElement.classList.contains("dark")).toBe(false);
    expect(localStorage.getItem("cortex-theme")).toBe("light");
    expect(themeEventListener).toHaveBeenCalled();

    // Switch to dark
    act(() => {
      fireEvent.click(screen.getByTestId("set-dark"));
    });

    expect(screen.getByTestId("resolvedTheme").textContent).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(document.documentElement.classList.contains("light")).toBe(false);
    expect(localStorage.getItem("cortex-theme")).toBe("dark");

    window.removeEventListener("cortex-theme-change", themeEventListener);
  });

  it("toggles theme back and forth using toggleTheme", () => {
    render(
      <ThemeProvider>
        <TestConsumer />
      </ThemeProvider>
    );

    expect(screen.getByTestId("resolvedTheme").textContent).toBe("dark");

    act(() => {
      fireEvent.click(screen.getByTestId("toggle"));
    });

    expect(screen.getByTestId("resolvedTheme").textContent).toBe("light");
    expect(document.documentElement.classList.contains("light")).toBe(true);

    act(() => {
      fireEvent.click(screen.getByTestId("toggle"));
    });

    expect(screen.getByTestId("resolvedTheme").textContent).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("renders ThemeToggle with accessible button and toggles state", () => {
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>
    );

    const toggleBtn = screen.getByRole("button", { name: /switch to light theme/i });
    expect(toggleBtn).toBeDefined();

    act(() => {
      fireEvent.click(toggleBtn);
    });

    expect(screen.getByRole("button", { name: /switch to dark theme/i })).toBeDefined();
    expect(document.documentElement.classList.contains("light")).toBe(true);
  });
});
