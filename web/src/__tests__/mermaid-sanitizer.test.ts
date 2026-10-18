import { describe, it, expect } from "vitest";
import mermaid from "mermaid";
import { sanitizeMermaidChart } from "@/lib/mermaid-sanitizer";

describe("sanitizeMermaidChart", () => {
  it("quotes node labels containing parentheses and slashes inside square brackets", () => {
    const raw = `flowchart TD
    subgraph NextJS["Next.js (App Router)"]
        API[API Routes<br/>app/api/_]
        Auth[Auth wrappers<br/>lib/auth/]
        Prisma[Prisma ORM<br/>(PlanetScale DB)]
        Redis[Upstash Redis]
        Tinybird[Tinybird Analytics]
        Stripe[Stripe / PayPal]
        Resend[Resend Email]
        Cron[QStash-signed cron routes<br/>app/(ee)/api/cron/]
    end

    Client -->|HTTP request| API
    API -->|auth check| Auth
    Auth -->|workspace/role data| Prisma
    API -->|business logic| Service[Service layer<br/>(link, partner, payout, etc.)]
    Service -->|read/write| Prisma
    Service -->|cache| Redis
    Service -->|track event| Tinybird`;

    const sanitized = sanitizeMermaidChart(raw);
    expect(sanitized).toContain('Prisma["Prisma ORM<br/>(PlanetScale DB)"]');
    expect(sanitized).toContain('API["API Routes<br/>app/api/_"]');
    expect(sanitized).toContain('Cron["QStash-signed cron routes<br/>app/(ee)/api/cron/"]');
    expect(sanitized).toContain('Service["Service layer<br/>(link, partner, payout, etc.)"]');
  });

  it("parses successfully with mermaid.parse in jsdom", async () => {
    mermaid.initialize({
      startOnLoad: false,
      suppressErrorRendering: true,
    });

    const raw = `flowchart TD
    subgraph NextJS["Next.js (App Router)"]
        API[API Routes<br/>app/api/_]
        Auth[Auth wrappers<br/>lib/auth/]
        Prisma[Prisma ORM<br/>(PlanetScale DB)]
        Redis[Upstash Redis]
        Tinybird[Tinybird Analytics]
        Stripe[Stripe / PayPal]
        Resend[Resend Email]
        Cron[QStash-signed cron routes<br/>app/(ee)/api/cron/]
    end

    Client -->|HTTP request| API
    API -->|auth check| Auth
    Auth -->|workspace/role data| Prisma
    API -->|business logic| Service[Service layer<br/>(link, partner, payout, etc.)]
    Service -->|read/write| Prisma
    Service -->|cache| Redis
    Service -->|track event| Tinybird`;

    const sanitized = sanitizeMermaidChart(raw);
    const result = await mermaid.parse(sanitized);
    expect(result).toBeTruthy();
  });
});
