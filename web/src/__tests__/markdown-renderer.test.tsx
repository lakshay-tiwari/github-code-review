import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MarkdownRenderer } from "@/components/chat/markdown-renderer";

// Mock clipboard
Object.assign(navigator, {
  clipboard: {
    writeText: vi.fn().mockResolvedValue(undefined),
  },
});

describe("MarkdownRenderer", () => {
  it("preserves whitespace between words and paragraphs", () => {
    const markdown = "The quick brown fox jumps over the lazy dog.\n\nSecond paragraph with multiple sentences.";
    const { container } = render(<MarkdownRenderer content={markdown} />);

    expect(container.textContent).toContain("The quick brown fox jumps over the lazy dog.");
    expect(container.textContent).toContain("Second paragraph with multiple sentences.");
    const paragraphs = container.querySelectorAll("p");
    expect(paragraphs.length).toBe(2);
  });

  it("renders headings with visual hierarchy and anchor IDs", () => {
    const markdown = "# System Architecture\n\n## Data Flow\n\n### Vector Pipeline";
    const { container } = render(<MarkdownRenderer content={markdown} />);

    const h1 = container.querySelector("h1");
    const h2 = container.querySelector("h2");
    const h3 = container.querySelector("h3");

    expect(h1).not.toBeNull();
    expect(h1?.id).toBe("system-architecture");
    expect(h1?.textContent).toContain("System Architecture");

    expect(h2).not.toBeNull();
    expect(h2?.id).toBe("data-flow");
    expect(h2?.textContent).toContain("Data Flow");

    expect(h3).not.toBeNull();
    expect(h3?.textContent).toContain("Vector Pipeline");
  });

  it("renders markdown tables as responsive HTML tables without showing raw markdown pipes", () => {
    const markdown = `
| Component | Responsibility | Status |
| :--- | :--- | :--- |
| API Gateway | Routes client requests | Active |
| Worker Node | Indexes repositories | Idle |
`;
    const { container } = render(<MarkdownRenderer content={markdown} />);

    const table = container.querySelector("table");
    expect(table).not.toBeNull();

    const headers = container.querySelectorAll("th");
    expect(headers.length).toBe(3);
    expect(headers[0].textContent).toBe("Component");
    expect(headers[1].textContent).toBe("Responsibility");
    expect(headers[2].textContent).toBe("Status");

    const rows = container.querySelectorAll("tbody tr");
    expect(rows.length).toBe(2);
    expect(rows[0].textContent).toContain("API Gateway");
    expect(rows[0].textContent).toContain("Routes client requests");
  });

  it("renders syntax-highlighted code blocks with language and copy button", () => {
    const markdown = "```python\ndef calculate_sum(a, b):\n    return a + b\n```";
    render(<MarkdownRenderer content={markdown} />);

    expect(screen.getByText(/python/i)).toBeDefined();
    expect(screen.getByText("Copy")).toBeDefined();
    expect(screen.getByText(/calculate_sum/)).toBeDefined();
  });

  it("renders Mermaid diagrams for mermaid-fenced code blocks", () => {
    const markdown = "```mermaid\nflowchart TD\n    A[Client] --> B[API]\n    B --> C[PostgreSQL]\n```";
    render(<MarkdownRenderer content={markdown} />);

    // Renders the Architecture Diagram header and mermaid badge
    expect(screen.getByText("Architecture Diagram")).toBeDefined();
    expect(screen.getByText("Mermaid")).toBeDefined();
  });

  it("handles complex mermaid diagrams with unquoted parentheses in node labels", () => {
    const markdown = `\`\`\`mermaid
flowchart TD
    subgraph NextJS["Next.js (App Router)"]
        API[API Routes<br/>app/api/_]
        Prisma[Prisma ORM<br/>(PlanetScale DB)]
    end
    API --> Prisma
\`\`\``;
    render(<MarkdownRenderer content={markdown} />);
    expect(screen.getAllByText("Architecture Diagram").length).toBeGreaterThan(0);
  });

  it("sanitizes unsafe javascript: links while keeping external links safe", () => {
    const markdown = "[Malicious link](javascript:alert(1)) and [Legit docs](https://github.com/cortex)";
    const { container } = render(<MarkdownRenderer content={markdown} />);

    // Malicious link should not have a javascript: href
    const maliciousAnchor = container.querySelector('a[href^="javascript:"]');
    expect(maliciousAnchor).toBeNull();

    // Safe external link should have target=_blank and rel=noopener noreferrer
    const legitAnchor = container.querySelector('a[href="https://github.com/cortex"]');
    expect(legitAnchor).not.toBeNull();
    expect(legitAnchor?.getAttribute("target")).toBe("_blank");
    expect(legitAnchor?.getAttribute("rel")).toContain("noopener noreferrer");
  });

  it("renders nested lists with indentation", () => {
    const markdown = `
- Backend Services
  - FastAPI
  - Celery
- Databases
  - PostgreSQL
  - Qdrant
`;
    const { container } = render(<MarkdownRenderer content={markdown} />);

    const uls = container.querySelectorAll("ul");
    expect(uls.length).toBeGreaterThanOrEqual(2);
    expect(container.textContent).toContain("FastAPI");
    expect(container.textContent).toContain("PostgreSQL");
  });
});
