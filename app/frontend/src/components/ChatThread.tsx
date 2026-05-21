import { useEffect, useRef, useState } from "react";
import { Box, TextField, IconButton, CircularProgress } from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import MessageBubble from "./MessageBubble";
import type { Citation } from "./CitationPill";
import CitationSlideOver from "./CitationSlideOver";
import { streamChat } from "../api/chat";

interface Message {
  role: "user" | "assistant";
  text: string;
  citations?: Citation[];
}

interface Props {
  pendingExample: string | null;
  onConsumeExample: () => void;
}

function parseCitations(toolCallContent: { name: string; args: string }, toolResult: unknown): Citation[] {
  // The exact shape of tool_call SSE events depends on the deployed agent's
  // streaming format. This decoder is a starting point that we will refine
  // against real SSE payloads during Task 20 verification.
  try {
    const parsed = typeof toolResult === "string" ? JSON.parse(toolResult) : toolResult;
    const rows = (parsed as { data_array?: unknown[]; rows?: unknown[] })?.data_array
      ?? (parsed as { data_array?: unknown[]; rows?: unknown[] })?.rows
      ?? [];
    if (toolCallContent.name.endsWith("search_past_issues")) {
      return (rows as unknown[][]).map((r) => ({
        kind: "issue" as const,
        issueId: r[0] as number,
        noteType: r[4] as string,
        preview: r[5] as string,
      }));
    }
    if (toolCallContent.name.endsWith("search_technical_manuals")) {
      return (rows as unknown[][]).map((r) => ({
        kind: "manual" as const,
        sourcePdf: r[0] as string,
        pageFirst: r[1] as number,
        pageLast: r[2] as number,
        preview: r[3] as string,
      }));
    }
  } catch {}
  return [];
}

export default function ChatThread({ pendingExample, onConsumeExample }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [openCitation, setOpenCitation] = useState<Citation | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  useEffect(() => {
    if (pendingExample) {
      setInput(pendingExample);
      onConsumeExample();
    }
  }, [pendingExample, onConsumeExample]);

  async function send() {
    if (!input.trim() || busy) return;
    const userMsg: Message = { role: "user", text: input };
    const next = [...messages, userMsg];
    setMessages(next);
    setInput("");
    setBusy(true);

    const assistantMsg: Message = { role: "assistant", text: "", citations: [] };
    setMessages(m => [...m, assistantMsg]);

    let acc = "";
    const collected: Citation[] = [];
    try {
      for await (const ch of streamChat(next.map(m => ({ role: m.role, content: m.text })))) {
        if (ch.type === "text") {
          acc += ch.content;
          setMessages(m => {
            const copy = [...m];
            copy[copy.length - 1] = { ...copy[copy.length - 1], text: acc };
            return copy;
          });
        } else if (ch.type === "tool_call") {
          collected.push(...parseCitations(ch.content, ch.content.args));
        }
      }
      setMessages(m => {
        const copy = [...m];
        copy[copy.length - 1] = { ...copy[copy.length - 1], citations: collected };
        return copy;
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Box sx={{ flex: 1, overflowY: "auto", p: 2, display: "flex", flexDirection: "column" }}>
        {messages.map((m, i) => (
          <MessageBubble
            key={i}
            role={m.role}
            text={m.text}
            citations={m.citations}
            onCitationClick={setOpenCitation}
          />
        ))}
        <div ref={endRef} />
      </Box>
      <Box sx={{ p: 2, borderTop: "1px solid #E0E0E0", display: "flex", gap: 1, bgcolor: "#FFF" }}>
        <TextField
          fullWidth size="small" placeholder="Describe an issue..."
          value={input} onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
          disabled={busy}
        />
        <IconButton onClick={send} disabled={busy || !input.trim()} color="primary">
          {busy ? <CircularProgress size={20} /> : <SendIcon />}
        </IconButton>
      </Box>
      <CitationSlideOver open={!!openCitation} citation={openCitation} onClose={() => setOpenCitation(null)} />
    </>
  );
}
