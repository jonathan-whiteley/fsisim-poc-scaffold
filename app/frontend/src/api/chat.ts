export interface ChatResponse {
  text: string;
  tool_calls: { name: string; args: string }[];
  error: string | null;
}

export async function sendChat(messages: { role: string; content: string }[]): Promise<ChatResponse> {
  let resp: Response;
  try {
    resp = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ messages }),
    });
  } catch (e) {
    return {
      text: `Network error reaching the app backend: ${e instanceof Error ? e.message : String(e)}`,
      tool_calls: [],
      error: "network",
    };
  }

  if (!resp.ok) {
    let detail = "";
    try { detail = await resp.text(); } catch {}
    return {
      text: `Request failed (${resp.status} ${resp.statusText}).\n\n${detail.slice(0, 600)}`,
      tool_calls: [],
      error: `http_${resp.status}`,
    };
  }

  try {
    return await resp.json();
  } catch (e) {
    return {
      text: `Could not parse server response: ${e instanceof Error ? e.message : String(e)}`,
      tool_calls: [],
      error: "parse",
    };
  }
}
