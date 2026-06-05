import { useEffect, useRef, useState } from "react";
import { Box, Container, IconButton, Stack, TextField } from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import MessageBubble from "./MessageBubble";
import CitationSlideOver from "./CitationSlideOver";
import EmptyHero from "./EmptyHero";
import { getThread, sendChat, type ThreadMessage } from "../api/chat";
import type { Citation } from "./CitationPill";
import { FS_NAVY, FS_BORDER } from "../theme";

interface Message {
  role: "user" | "assistant";
  text: string;
  citations?: Citation[];
  assistantMessageId?: string;
  initialRating?: "up" | "down" | null;
}

interface Props {
  examples: string[];
  threadId: string | null;
  onThreadChange: (threadId: string) => void;
}

export default function ChatThread({ examples, threadId, onThreadChange }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [slideOver, setSlideOver] = useState<Citation | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);
  // Threads minted locally by send() so we can suppress the history fetch
  // (history doesn't carry citations; reloading would wipe what we just got).
  const locallyCreatedThreads = useRef<Set<string>>(new Set());

  // Load history when the parent switches threads.
  useEffect(() => {
    if (!threadId) {
      setMessages([]);
      return;
    }
    if (locallyCreatedThreads.current.has(threadId)) {
      // We just created this thread via send(); state already has the full
      // response (with citations). Don't refetch.
      return;
    }
    let cancelled = false;
    (async () => {
      const { messages: hist } = await getThread(threadId);
      if (cancelled) return;
      const mapped: Message[] = hist
        .filter((m: ThreadMessage) => m.role !== "system")
        .map((m: ThreadMessage) => ({
          role: m.role as "user" | "assistant",
          text: m.content,
          assistantMessageId: m.role === "assistant" ? m.id : undefined,
        }));
      setMessages(mapped);
    })();
    return () => {
      cancelled = true;
    };
  }, [threadId]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send(textOverride?: string) {
    const content = (textOverride ?? input).trim();
    if (!content || busy) return;
    const next: Message[] = [
      ...messages,
      { role: "user", text: content },
      { role: "assistant", text: "…" },
    ];
    setMessages(next);
    setInput("");
    setBusy(true);

    const resp = await sendChat(content, threadId ?? undefined);

    if (!threadId && resp.thread_id) {
      locallyCreatedThreads.current.add(resp.thread_id);
      onThreadChange(resp.thread_id);
    }

    const citations: Citation[] = [
      ...resp.manual_citations.map((m) => ({
        kind: "manual" as const,
        sourcePdf: m.source_pdf,
        filename: m.filename,
        title: m.title,
        pageFirst: m.page_first,
        pageLast: m.page_last,
        preview: m.preview,
      })),
      ...resp.issue_citations.map((i) => ({
        kind: "issue" as const,
        issueId: i.issue_id,
        issueType: i.issue_type,
        simName: i.sim_name,
        noteType: i.note_type,
        preview: i.preview,
      })),
    ];

    setMessages((m) => {
      const copy = [...m];
      copy[copy.length - 1] = {
        role: "assistant",
        text: resp.text || "(no response)",
        citations,
        assistantMessageId: resp.assistant_message_id,
      };
      return copy;
    });
    setBusy(false);
  }

  const hasMessages = messages.length > 0;

  return (
    <Box sx={{ display: "flex", flex: 1, overflow: "hidden", position: "relative" }}>
      <Box sx={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        <Container maxWidth="md" sx={{ flex: 1, display: "flex", flexDirection: "column", py: hasMessages ? 3 : 0 }}>
          {!hasMessages && <EmptyHero examples={examples} onPickExample={(q) => send(q)} />}
          {hasMessages && (
            <Stack sx={{ flex: 1, width: "100%" }}>
              {messages.map((m, i) => (
                <MessageBubble
                  key={i}
                  role={m.role}
                  text={m.text}
                  citations={m.citations}
                  assistantMessageId={m.assistantMessageId}
                  initialRating={m.initialRating ?? null}
                  onCitationClick={setSlideOver}
                />
              ))}
              <div ref={endRef} />
            </Stack>
          )}
        </Container>
        <Box sx={{ borderTop: `1px solid ${FS_BORDER}`, p: 1.5 }}>
          <Container maxWidth="md" sx={{ display: "flex", gap: 1 }}>
            <TextField
              fullWidth
              size="small"
              placeholder="Ask about an issue, a fault code, or a manual…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
              disabled={busy}
            />
            <IconButton
              onClick={() => send()}
              disabled={busy || !input.trim()}
              sx={{ color: FS_NAVY }}
              aria-label="send"
            >
              <SendIcon />
            </IconButton>
          </Container>
        </Box>
      </Box>
      <CitationSlideOver
        open={slideOver !== null}
        citation={slideOver}
        onClose={() => setSlideOver(null)}
      />
    </Box>
  );
}
