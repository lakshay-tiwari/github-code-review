import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { Input } from "@/components/ui/input";

describe("Input component", () => {
  it("renders with label and placeholder", () => {
    render(
      <Input
        label="GitHub Repository"
        placeholder="https://github.com/owner/repo"
      />
    );
    expect(screen.getByLabelText(/github repository/i)).toBeDefined();
    expect(
      screen.getByPlaceholderText("https://github.com/owner/repo")
    ).toBeDefined();
  });

  it("renders error message when error prop is provided", () => {
    render(<Input label="Repo URL" error="Invalid GitHub URL provided" />);
    expect(screen.getByText(/invalid github url provided/i)).toBeDefined();
  });

  it("updates value on change event", () => {
    const handleChange = vi.fn();
    render(
      <Input
        label="Repo URL"
        placeholder="URL"
        onChange={handleChange}
      />
    );
    const input = screen.getByPlaceholderText("URL") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "https://github.com/test/repo" } });
    expect(handleChange).toHaveBeenCalled();
  });
});
