export interface ManualCitation {
  source_pdf: string;
  filename: string;
  title: string;
  page_first: number;
  page_last: number;
  preview: string;
}

export interface IssueCitation {
  issue_id: number;
  issue_type: string;
  sim_name: string;
  note_type: string;
  preview: string;
}

export interface ChatResponse {
  text: string;
  manual_citations: ManualCitation[];
  issue_citations: IssueCitation[];
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
    return _err(`Network error reaching the app backend: ${e instanceof Error ? e.message : String(e)}`, "network");
  }
  if (!resp.ok) {
    let detail = "";
    try { detail = await resp.text(); } catch {}
    return _err(`Request failed (${resp.status} ${resp.statusText}).\n\n${detail.slice(0, 600)}`, `http_${resp.status}`);
  }
  try {
    return await resp.json();
  } catch (e) {
    return _err(`Could not parse server response: ${e instanceof Error ? e.message : String(e)}`, "parse");
  }
}

function _err(text: string, error: string): ChatResponse {
  return { text, manual_citations: [], issue_citations: [], error };
}
