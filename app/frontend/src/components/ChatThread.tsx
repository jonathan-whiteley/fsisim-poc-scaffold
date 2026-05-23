import { useEffect, useRef, useState } from "react";
import { Box, TextField, IconButton, Stack, Typography, Paper, Container } from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import FlightTakeoffIcon from "@mui/icons-material/FlightTakeoff";
import MessageBubble from "./MessageBubble";
import type { Citation } from "./CitationPill";
import CitationSlideOver from "./CitationSlideOver";
import { streamChat } from "../api/chat";
import { FS_NAVY, FS_SKY, FS_SKY_LIGHT, FS_BORDER, FS_MUTED, FS_SURFACE } from "../theme";

interface Message {
  role: "user" | "assistant";
  text: string;
  citations?: Citation[];
}

interface Props {
  examples: string[];
  pendingExample: string | null;
  onConsumeExample: () => void;
  onPickExample: (q: string) => void;
}

function parseCitations(toolCallContent: { name: string; args: string }, toolResult: unknown): Citation[] {
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

export default function ChatThread({ examples, pendingExample, onConsumeExample, onPickExample }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [openCitation, setOpenCitation] = useState<Citation | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (pendingExample) {
      setInput(pendingExample);
      onConsumeExample();
    }
  }, [pendingExample, onConsumeExample]);

  async function send(textOverride?: string) {
    const content = (textOverride ?? input).trim();
    if (!content || busy) return;
    const userMsg: Message = { role: "user", text: content };
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
          const ev = ch as { content: { name: string; args: string } };
          collected.push(...parseCitations(ev.content, ev.content.args));
        }
      }
      if (!acc) {
        // Stream closed with no text events; surface a friendly fallback
        setMessages(m => {
          const copy = [...m];
          copy[copy.length - 1] = {
            ...copy[copy.length - 1],
            text: "The agent returned an empty response. Try again in a moment or rephrase the question.",
          };
          return copy;
        });
      }
      setMessages(m => {
        const copy = [...m];
        copy[copy.length - 1] = { ...copy[copy.length - 1], citations: collected };
        return copy;
      });
    } catch (err) {
      setMessages(m => {
        const copy = [...m];
        copy[copy.length - 1] = {
          ...copy[copy.length - 1],
          text: `Network error: ${err instanceof Error ? err.message : String(err)}`,
        };
        return copy;
      });
    } finally {
      setBusy(false);
    }
  }

  const hasMessages = messages.length > 0;

  return (
    <>
      <Box
        sx={{
          flex: 1,
          overflowY: "auto",
          bgcolor: FS_SURFACE,
          display: "flex",
          flexDirection: "column",
        }}
      >
        <Container maxWidth="md" sx={{ flex: 1, display: "flex", flexDirection: "column", py: hasMessages ? 3 : 0 }}>
          {!hasMessages && <EmptyHero examples={examples} onPickExample={(q) => { onPickExample(q); send(q); }} />}
          {hasMessages && (
            <Stack sx={{ flex: 1, width: "100%" }}>
              {messages.map((m, i) => {
                const isLast = i === messages.length - 1;
                return (
                  <MessageBubble
                    key={i}
                    role={m.role}
                    text={m.text}
                    citations={m.citations}
                    streaming={busy && isLast && m.role === "assistant"}
                    onCitationClick={setOpenCitation}
                  />
                );
              })}
              <div ref={endRef} />
            </Stack>
          )}
        </Container>
      </Box>

      <Box
        sx={{
          borderTop: `1px solid ${FS_BORDER}`,
          bgcolor: "#FFFFFF",
          px: 2,
          py: 1.5,
        }}
      >
        <Container maxWidth="md" sx={{ px: { xs: 0, sm: 2 } }}>
          <Paper
            elevation={0}
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1,
              p: 0.5,
              pl: 1.5,
              border: `1px solid ${FS_BORDER}`,
              borderRadius: 3,
              transition: "border-color 0.15s, box-shadow 0.15s",
              "&:focus-within": {
                borderColor: FS_SKY,
                boxShadow: `0 0 0 3px ${FS_SKY_LIGHT}`,
              },
            }}
          >
            <TextField
              fullWidth
              multiline
              maxRows={5}
              variant="standard"
              placeholder="Describe a simulator issue, ask about jargon, or paste a fault code..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
              disabled={busy}
              slotProps={{ input: { disableUnderline: true, sx: { fontSize: 14.5, py: 0.5 } } }}
            />
            <IconButton
              onClick={() => send()}
              disabled={busy || !input.trim()}
              sx={{
                bgcolor: input.trim() && !busy ? FS_NAVY : "#E5E7EB",
                color: "#FFFFFF",
                width: 40,
                height: 40,
                transition: "all 0.15s",
                "&:hover": { bgcolor: input.trim() && !busy ? "#000010" : "#E5E7EB" },
                "&.Mui-disabled": { color: "#FFFFFF", opacity: 0.5 },
              }}
            >
              <SendIcon sx={{ fontSize: 18 }} />
            </IconButton>
          </Paper>
          <Typography
            variant="caption"
            sx={{ display: "block", textAlign: "center", color: FS_MUTED, mt: 1, fontSize: 11 }}
          >
            Press <strong>Enter</strong> to send · <strong>Shift+Enter</strong> for newline. Responses may contain
            errors; verify against source citations.
          </Typography>
        </Container>
      </Box>

      <CitationSlideOver open={!!openCitation} citation={openCitation} onClose={() => setOpenCitation(null)} />
    </>
  );
}

function EmptyHero({ examples, onPickExample }: { examples: string[]; onPickExample: (q: string) => void }) {
  return (
    <Box sx={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", py: 6 }}>
      <Stack sx={{ alignItems: "center", mb: 5, gap: 2.5 }}>
        <Box
          sx={{
            width: 56,
            height: 56,
            borderRadius: "50%",
            bgcolor: FS_NAVY,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 4px 16px rgba(0,0,34,0.18)",
          }}
        >
          <FlightTakeoffIcon sx={{ color: FS_SKY, fontSize: 28 }} />
        </Box>
        <Stack sx={{ alignItems: "center", gap: 0.5 }}>
          <Typography variant="h1" sx={{ textAlign: "center" }}>
            FSISIM Issue Resolution
          </Typography>
          <Typography sx={{ color: FS_MUTED, textAlign: "center", maxWidth: 520 }}>
            Search past G001 simulator issues, resolve acronyms against technical manuals, and surface
            prior resolutions in seconds.
          </Typography>
        </Stack>
      </Stack>

      <Stack spacing={1.5} sx={{ width: "100%", maxWidth: 640, mx: "auto" }}>
        <Typography variant="overline" sx={{ textAlign: "left", mb: 0.5 }}>
          Try one of these
        </Typography>
        {examples.map((q, i) => (
          <Paper
            key={i}
            onClick={() => onPickExample(q)}
            elevation={0}
            sx={{
              p: 1.75,
              border: `1px solid ${FS_BORDER}`,
              borderRadius: 2,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 1.5,
              transition: "all 0.15s",
              "&:hover": {
                borderColor: FS_NAVY,
                bgcolor: "#FFFFFF",
                boxShadow: "0 4px 12px rgba(0,0,34,0.06)",
                transform: "translateY(-1px)",
              },
            }}
          >
            <Box
              sx={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                bgcolor: FS_SKY,
                flexShrink: 0,
              }}
            />
            <Typography sx={{ fontSize: 14, color: FS_NAVY, fontWeight: 500 }}>{q}</Typography>
          </Paper>
        ))}
      </Stack>
    </Box>
  );
}
