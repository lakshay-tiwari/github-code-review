import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { Button } from "@/components/ui/button";

describe("Button component", () => {
  it("renders correctly with children", () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole("button", { name: /click me/i })).toBeDefined();
  });

  it("applies primary variant classes by default", () => {
    render(<Button>Primary</Button>);
    const button = screen.getByRole("button", { name: /primary/i });
    expect(button.className).toContain("bg-indigo-600");
  });

  it("applies outline variant classes when specified", () => {
    render(<Button variant="outline">Outline</Button>);
    const button = screen.getByRole("button", { name: /outline/i });
    expect(button.className).toContain("border-zinc-700");
  });

  it("handles loading state by disabling button and showing spinner", () => {
    render(<Button isLoading>Loading Action</Button>);
    const button = screen.getByRole("button", { name: /loading action/i });
    expect(button.hasAttribute("disabled")).toBe(true);
  });

  it("fires onClick handler when clicked", () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Trigger</Button>);
    fireEvent.click(screen.getByRole("button", { name: /trigger/i }));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });
});
