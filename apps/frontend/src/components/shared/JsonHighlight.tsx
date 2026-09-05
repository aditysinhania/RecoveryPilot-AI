interface JsonHighlightProps {
  value: Record<string, unknown>;
}

function tokenize(json: string): { text: string; cls: string }[] {
  const tokens: { text: string; cls: string }[] = [];
  const pattern =
    /("(?:\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"\s*:)|("(?:\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*")|(-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)|\b(true|false|null)\b/g;
  let last = 0;
  let match = pattern.exec(json);
  while (match) {
    if (match.index > last) {
      tokens.push({ text: json.slice(last, match.index), cls: "text-zinc-500" });
    }
    if (match[1]) {
      tokens.push({ text: match[1], cls: "text-info" });
    } else if (match[2]) {
      tokens.push({ text: match[2], cls: "text-recovered" });
    } else if (match[3]) {
      tokens.push({ text: match[3], cls: "text-waiting" });
    } else {
      tokens.push({ text: match[4], cls: "text-ai" });
    }
    last = match.index + match[0].length;
    match = pattern.exec(json);
  }
  if (last < json.length) {
    tokens.push({ text: json.slice(last), cls: "text-zinc-500" });
  }
  return tokens;
}

/** Pretty-printed JSON with theme token colors. No highlight.js. */
export function JsonHighlight({ value }: JsonHighlightProps) {
  const pretty = JSON.stringify(value, null, 2);
  return (
    <pre className="mt-2 overflow-x-auto rounded-md bg-canvas p-2 font-mono text-[10px] leading-relaxed">
      {tokenize(pretty).map((token, index) => (
        <span key={`${token.cls}-${index}`} className={token.cls}>
          {token.text}
        </span>
      ))}
    </pre>
  );
}
