import { describe, it, expect, vi } from "vitest";
import { parseSSEBlock, createSSEStreamAccumulator } from "@/lib/sse-parser";

describe("parseSSEBlock", () => {
  it("preserves leading spaces in data fields", () => {
    const block = "event: chunk\ndata:  world";
    const parsed = parseSSEBlock(block);
    expect(parsed).not.toBeNull();
    expect(parsed?.event).toBe("chunk");
    // "data:  world" -> strips single space after "data:", leaves " world"
    expect(parsed?.data).toBe(" world");
  });

  it("handles multi-line data fields without losing whitespace", () => {
    const block = "event: chunk\ndata: line1\ndata:   indented line2";
    const parsed = parseSSEBlock(block);
    expect(parsed?.data).toBe("line1\n  indented line2");
  });

  it("handles empty data line representing newline", () => {
    const block = "event: chunk\ndata: \n";
    const parsed = parseSSEBlock(block);
    expect(parsed?.data).toBe("");
  });

  it("parses JSON events correctly", () => {
    const block = 'event: citations\ndata: [{"file_path":"src/main.py","start_line":10,"end_line":20}]';
    const parsed = parseSSEBlock(block);
    expect(parsed?.event).toBe("citations");
    const json = JSON.parse(parsed?.data || "[]");
    expect(json).toHaveLength(1);
    expect(json[0].file_path).toBe("src/main.py");
  });
});

describe("createSSEStreamAccumulator", () => {
  it("accumulates chunks across fragmented byte streams without dropping spaces", () => {
    const onChunk = vi.fn();
    const onDone = vi.fn();
    const accumulator = createSSEStreamAccumulator({
      onChunk,
      onDone,
    });

    const encoder = new TextEncoder();
    const decoder = new TextDecoder();

    // Stream arrives in fragmented pieces
    const part1 = encoder.encode("event: chunk\ndata: The");
    const part2 = encoder.encode(" function\n\nevent: chunk\ndata:  returns");
    const part3 = encoder.encode(" None.\n\nevent: done\ndata: {\"status\":\"completed\"}\n\n");

    accumulator.push(part1, decoder);
    expect(onChunk).not.toHaveBeenCalled(); // part1 incomplete

    accumulator.push(part2, decoder);
    // part1 + part2 forms "The function"
    expect(onChunk).toHaveBeenCalledWith("The function", "The function");

    accumulator.push(part3, decoder);
    expect(onChunk).toHaveBeenCalledWith(" returns None.", "The function returns None.");
    expect(onDone).toHaveBeenCalledWith({ status: "completed" }, "The function returns None.");
    expect(accumulator.getAccumulatedText()).toBe("The function returns None.");
  });

  it("handles errors while preserving partial text", () => {
    const onError = vi.fn();
    const accumulator = createSSEStreamAccumulator({ onError });
    const encoder = new TextEncoder();
    const decoder = new TextDecoder();

    accumulator.push(encoder.encode("event: chunk\ndata: Partial response\n\n"), decoder);
    accumulator.push(encoder.encode("event: error\ndata: {\"error\":\"LLM rate limit\"}\n\n"), decoder);

    expect(onError).toHaveBeenCalledWith("LLM rate limit", "Partial response");
    expect(accumulator.getAccumulatedText()).toBe("Partial response");
  });
});
