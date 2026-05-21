export type Chunk =
  | { type: "text"; content: string }
  | { type: "tool_call"; content: { name: string; args: string } };

export async function* streamChat(messages: { role: string; content: string }[]): AsyncGenerator<Chunk> {
  const resp = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
  });
  if (!resp.body) throw new Error("no stream");
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
      yield JSON.parse(line.slice(5).trim()) as Chunk;
    }
  }
}
