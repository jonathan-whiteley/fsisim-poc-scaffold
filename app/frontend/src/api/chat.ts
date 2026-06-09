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
  thread_id: string;
  text: string;
  manual_citations: ManualCitation[];
  issue_citations: IssueCitation[];
  assistant_message_id: string;
  error: string | null;
}

export interface ThreadSummary {
  thread_id: string;
  title: string;
  updated_at: string;
}

export interface ThreadMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
  mlflow_trace_id?: string;
}

export async function sendChat(content: string, threadId?: string): Promise<ChatResponse> {
  const resp = await fetch("/api/chat", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content, thread_id: threadId }),
  });
  if (!resp.ok) {
    return {
      thread_id: threadId ?? "",
      text: `Request failed (${resp.status}).`,
      manual_citations: [],
      issue_citations: [],
      assistant_message_id: "",
      error: `http_${resp.status}`,
    };
  }
  const body = (await resp.json()) as ChatResponse;
  return { ...body, error: null };
}

export async function listThreads(): Promise<ThreadSummary[]> {
  const resp = await fetch("/api/threads", { credentials: "include" });
  if (!resp.ok) return [];
  const { threads } = (await resp.json()) as { threads: ThreadSummary[] };
  return threads;
}

export async function getThread(
  threadId: string,
): Promise<{ messages: ThreadMessage[] }> {
  const resp = await fetch(`/api/threads/${encodeURIComponent(threadId)}`, {
    credentials: "include",
  });
  if (!resp.ok) return { messages: [] };
  return (await resp.json()) as { messages: ThreadMessage[] };
}

export async function postFeedback(
  message_id: string,
  rating: "up" | "down",
  comment?: string,
): Promise<boolean> {
  const resp = await fetch("/api/feedback", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message_id, rating, comment }),
  });
  return resp.ok;
}
