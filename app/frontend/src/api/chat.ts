export type Chunk =
  | { type: "text"; content: string }
  | { type: "tool_call"; content: { name: string; args: string } };

export async function* streamChat(messages: { role: string; content: string }[]): AsyncGenerator<Chunk> {
  const resp = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    credentials: "include",
    body: JSON.stringify({ messages }),
  });

  if (!resp.ok) {
    let detail = "";
    try { detail = await resp.text(); } catch {}
    yield {
      type: "text",
      content: `Request failed (${resp.status}). ${detail.slice(0, 400) || resp.statusText}`,
    };
    return;
  }
  if (!resp.body) {
    yield { type: "text", content: "Server returned an empty response." };
    return;
  }

  const reader = resp.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const events = buf.split("\n\n");
    buf = events.pop() ?? "";
    for (const ev of events) {
      const line = ev.split("\n").find(l => l.startsWith("data:"));
      if (!line) continue;
      const payload = line.slice(5).trim();
      if (!payload) continue;
      try {
        yield JSON.parse(payload) as Chunk;
      } catch (e) {
        yield { type: "text", content: `[parse error on event: ${payload.slice(0, 200)}]` };
      }
    }
  }
}
