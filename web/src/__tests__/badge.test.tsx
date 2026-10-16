import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { Badge } from "@/components/ui/badge";

describe("Badge component", () => {
  it("renders with child text", () => {
    render(<Badge>Phase 2 Active</Badge>);
    expect(screen.getByText("Phase 2 Active")).toBeDefined();
  });

  it("applies variant classes correctly", () => {
    const { container } = render(
      <Badge variant="indigo">Verified Engine</Badge>
    );
    const span = container.querySelector("span");
    expect(span?.className).toContain("bg-indigo-950/60");
  });
});
