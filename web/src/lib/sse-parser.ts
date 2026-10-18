/**
 * Utilities for robust Server-Sent Events (SSE) parsing on the frontend.
 *
 * Guarantees:
 * - Preserves exact whitespace and newlines across streamed chunks.
 * - Never calls `.trim()` on streamed text tokens.
 * - Handles multiline `data:` blocks and continuation lines.
 * - Tolerates partial chunks and arbitrary network packet boundaries.
 */

export interface SSEEvent {
  event: string;
  data: string;
}

/**
 * Parses a single complete SSE event block (text between double newlines).
 */
export function parseSSEBlock(block: string): SSEEvent | null {
  if (!block || !block.trim()) return null;

  const lines = block.split(/\r?\n/);
  if (lines.length > 0 && lines[lines.length - 1] === "") {
    lines.pop();
  }
  let event = "message";
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith(":")) {
      // Comment line, ignore per SSE specification
      continue;
    }
    if (line.startsWith("event:")) {
      let ev = line.slice(6);
      if (ev.startsWith(" ")) ev = ev.slice(1);
      event = ev.trim();
    } else if (line.startsWith("data:")) {
      let data = line.slice(5);
      // Strip only a single leading space if present per SSE spec
      if (data.startsWith(" ")) data = data.slice(1);
      dataLines.push(data);
    } else if (!line.includes(":") && dataLines.length > 0) {
      // Continuation line for data field
      dataLines.push(line);
    }
  }

  return {
    event,
    data: dataLines.join("\n"),
  };
}

export interface StreamAccumulatorCallbacks<TCitation = unknown> {
  onStart?: (data: { conversation_id?: string; user_message_id?: string; commit_sha?: string }) => void;
  onCitations?: (citations: TCitation[]) => void;
  onChunk?: (chunk: string, accumulated: string) => void;
  onDone?: (data: { message_id?: string; conversation_id?: string; status?: string }, fullText: string) => void;
  onError?: (error: string, partialText: string) => void;
}

/**
 * Creates a stream accumulator that decodes Uint8Array chunks and dispatches parsed SSE events.
 */
export function createSSEStreamAccumulator<TCitation = unknown>(
  callbacks: StreamAccumulatorCallbacks<TCitation>
) {
  let buffer = "";
  let accumulatedText = "";
  const boundaryRegex = /\r?\n\r?\n/;

  return {
    push(chunkBytes: Uint8Array, decoder: TextDecoder) {
      buffer += decoder.decode(chunkBytes, { stream: true });

      let match: RegExpExecArray | null;
      while ((match = boundaryRegex.exec(buffer)) !== null) {
        const block = buffer.slice(0, match.index);
        buffer = buffer.slice(match.index + match[0].length);

        const parsed = parseSSEBlock(block);
        if (!parsed) continue;

        if (parsed.event === "start") {
          try {
            callbacks.onStart?.(JSON.parse(parsed.data));
          } catch {
            callbacks.onStart?.({});
          }
        } else if (parsed.event === "citations") {
          try {
            const list = JSON.parse(parsed.data);
            if (Array.isArray(list)) {
              callbacks.onCitations?.(list as TCitation[]);
            }
          } catch {
            // ignore malformed citations
          }
        } else if (parsed.event === "chunk") {
          // Do NOT trim parsed.data - spaces and indentation must be strictly preserved!
          accumulatedText += parsed.data;
          callbacks.onChunk?.(parsed.data, accumulatedText);
        } else if (parsed.event === "done") {
          try {
            callbacks.onDone?.(JSON.parse(parsed.data), accumulatedText);
          } catch {
            callbacks.onDone?.({}, accumulatedText);
          }
        } else if (parsed.event === "error") {
          let errMsg = "Generation failed mid-stream";
          try {
            const errObj = JSON.parse(parsed.data);
            if (errObj.error) errMsg = errObj.error;
          } catch {
            if (parsed.data) errMsg = parsed.data;
          }
          callbacks.onError?.(errMsg, accumulatedText);
        }
      }
    },

    flush(decoder: TextDecoder) {
      buffer += decoder.decode();
      if (buffer.trim()) {
        const parsed = parseSSEBlock(buffer);
        if (parsed && parsed.event === "chunk") {
          accumulatedText += parsed.data;
          callbacks.onChunk?.(parsed.data, accumulatedText);
        }
      }
      buffer = "";
    },

    getAccumulatedText() {
      return accumulatedText;
    },
  };
}
