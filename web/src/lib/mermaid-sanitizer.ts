/**
 * Sanitizes Mermaid flowchart text to fix common LLM syntax generation issues.
 *
 * Common issues:
 * 1. Node labels containing parentheses, brackets, or slashes without quotes:
 *    `Prisma[Prisma ORM<br/>(PlanetScale DB)]` -> `Prisma["Prisma ORM<br/>(PlanetScale DB)"]`
 *    `Cron[cron routes<br/>app/(ee)/api/cron/]` -> `Cron["cron routes<br/>app/(ee)/api/cron/"]`
 * 2. Node labels in parentheses containing nested parentheses:
 *    `Node(text (extra))` -> `Node("text (extra)")`
 * 3. Cylinder shapes with unquoted text:
 *    `DB[(PostgreSQL (v15))]` -> `DB[("PostgreSQL (v15)")]`
 * 4. Rhombus labels containing parentheses:
 *    `Node{label (extra)}` -> `Node{"label (extra)"}`
 */
export function sanitizeMermaidChart(chart: string): string {
  if (!chart) return chart;

  const lines = chart.split("\n");
  const processedLines = lines.map((line) => {
    let modified = line;

    // 1. Square brackets: ID[label] where label is unquoted
    modified = modified.replace(/([a-zA-Z0-9_-]+)\[([^"\]]+)\]/g, (match, id, label) => {
      const trimmed = label.trim();
      if (trimmed.startsWith('"') && trimmed.endsWith('"')) {
        return match;
      }
      // Cylinder shape: ID[(label)]
      if (trimmed.startsWith("(") && trimmed.endsWith(")")) {
        const inner = trimmed.slice(1, -1).trim();
        if (inner.startsWith('"') && inner.endsWith('"')) {
          return match;
        }
        const safeInner = inner.replace(/"/g, "'");
        return `${id}[("${safeInner}")]`;
      }
      const safeLabel = trimmed.replace(/"/g, "'");
      return `${id}["${safeLabel}"]`;
    });

    // 2. Stadium shape: ID([label])
    modified = modified.replace(/([a-zA-Z0-9_-]+)\(\[([^"\]]+)\]\)/g, (match, id, label) => {
      const trimmed = label.trim();
      if (trimmed.startsWith('"') && trimmed.endsWith('"')) {
        return match;
      }
      const safeLabel = trimmed.replace(/"/g, "'");
      return `${id}(["${safeLabel}"])`;
    });

    // 3. Rounded: ID(label with nested parentheses)
    modified = modified.replace(/([a-zA-Z0-9_-]+)\(([^"()]+(?:\([^"()]+\)[^"()]*)+)\)/g, (match, id, label) => {
      const trimmed = label.trim();
      if (trimmed.startsWith('"') && trimmed.endsWith('"')) {
        return match;
      }
      const safeLabel = trimmed.replace(/"/g, "'");
      return `${id}("${safeLabel}")`;
    });

    // 4. Rhombus: ID{label} containing parentheses or slashes
    modified = modified.replace(/([a-zA-Z0-9_-]+)\{([^"{}]+)\}/g, (match, id, label) => {
      const trimmed = label.trim();
      if (trimmed.startsWith('"') && trimmed.endsWith('"')) {
        return match;
      }
      if (trimmed.includes("(") || trimmed.includes(")") || trimmed.includes("/")) {
        const safeLabel = trimmed.replace(/"/g, "'");
        return `${id}{"${safeLabel}"}`;
      }
      return match;
    });

    return modified;
  });

  return processedLines.join("\n");
}
