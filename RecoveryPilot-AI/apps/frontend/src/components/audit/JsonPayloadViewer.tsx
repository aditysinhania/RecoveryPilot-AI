import { JsonHighlight } from "@/components/shared/JsonHighlight";

interface JsonPayloadViewerProps {
  value: unknown;
}

function asRecord(value: unknown): Record<string, unknown> {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return { value };
}

/** Pretty-printed JSON payload. Wraps the shared highlighter. */
export function JsonPayloadViewer({ value }: JsonPayloadViewerProps) {
  return <JsonHighlight value={asRecord(value)} />;
}
