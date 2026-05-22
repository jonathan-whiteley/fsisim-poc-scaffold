import { Box, Typography, Avatar, Stack } from "@mui/material";
import FlightTakeoffIcon from "@mui/icons-material/FlightTakeoff";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { FS_NAVY, FS_SKY, FS_BORDER, FS_TEXT, FS_MUTED } from "../theme";
import CitationPill, { type Citation } from "./CitationPill";

interface Props {
  role: "user" | "assistant";
  text: string;
  citations?: Citation[];
  streaming?: boolean;
  onCitationClick?: (c: Citation) => void;
}

export default function MessageBubble({ role, text, citations, streaming, onCitationClick }: Props) {
  const isUser = role === "user";

  return (
    <Stack
      direction="row"
      sx={{
        alignSelf: "stretch",
        justifyContent: isUser ? "flex-end" : "flex-start",
        my: 1.5,
        gap: 1.5,
      }}
    >
      {!isUser && (
        <Avatar
          sx={{ width: 32, height: 32, bgcolor: FS_NAVY, color: "#fff", mt: 0.25, flexShrink: 0 }}
        >
          <FlightTakeoffIcon sx={{ fontSize: 16, color: FS_SKY }} />
        </Avatar>
      )}
      <Box sx={{ maxWidth: { xs: "85%", md: "72%" }, minWidth: 0 }}>
        <Box
          sx={{
            bgcolor: isUser ? FS_NAVY : "#FFFFFF",
            color: isUser ? "#FFFFFF" : FS_TEXT,
            border: isUser ? "none" : `1px solid ${FS_BORDER}`,
            borderRadius: 2.5,
            px: 2,
            py: 1.5,
            boxShadow: isUser ? "none" : "0 1px 2px rgba(0,0,34,0.04)",
            "& p": { my: 0.5 },
            "& p:first-of-type": { mt: 0 },
            "& p:last-of-type": { mb: 0 },
            "& strong": { fontWeight: 700, color: isUser ? "#fff" : FS_NAVY },
            "& ul, & ol": { my: 0.75, pl: 2.5 },
            "& li": { mb: 0.25 },
            "& code": {
              bgcolor: isUser ? "rgba(255,255,255,0.12)" : "#F4F5F8",
              px: 0.6,
              py: 0.15,
              borderRadius: 0.75,
              fontSize: "0.88em",
              fontFamily: "'JetBrains Mono', ui-monospace, Menlo, monospace",
            },
            "& hr": {
              border: 0,
              borderTop: `1px solid ${isUser ? "rgba(255,255,255,0.2)" : FS_BORDER}`,
              my: 1.25,
            },
            "& a": { color: isUser ? "#9FC5FF" : FS_SKY, textDecoration: "none" },
            "& a:hover": { textDecoration: "underline" },
            "& table": { borderCollapse: "collapse", my: 0.75, fontSize: 13 },
            "& th, & td": {
              border: `1px solid ${isUser ? "rgba(255,255,255,0.2)" : FS_BORDER}`,
              padding: "4px 8px",
            },
          }}
        >
          {isUser ? (
            <Typography sx={{ whiteSpace: "pre-wrap" }}>{text}</Typography>
          ) : text ? (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
          ) : streaming ? (
            <TypingDots />
          ) : null}
        </Box>
        {citations && citations.length > 0 && (
          <Box sx={{ mt: 0.75, display: "flex", flexWrap: "wrap" }}>
            {citations.map((c, i) => (
              <CitationPill key={i} c={c} onClick={() => onCitationClick?.(c)} />
            ))}
          </Box>
        )}
        {!isUser && streaming && text && (
          <Typography variant="caption" sx={{ color: FS_MUTED, ml: 0.5, mt: 0.5, display: "block" }}>
            Searching past issues and manuals...
          </Typography>
        )}
      </Box>
      {isUser && (
        <Avatar sx={{ width: 32, height: 32, bgcolor: FS_SKY, color: "#fff", fontSize: 13, fontWeight: 700, mt: 0.25, flexShrink: 0 }}>
          JW
        </Avatar>
      )}
    </Stack>
  );
}

function TypingDots() {
  return (
    <Box sx={{ display: "inline-flex", alignItems: "center", gap: 0.6, py: 0.5 }}>
      {[0, 1, 2].map(i => (
        <Box
          key={i}
          sx={{
            width: 7,
            height: 7,
            borderRadius: "50%",
            bgcolor: FS_NAVY,
            opacity: 0.4,
            animation: `bounce 1.2s ease-in-out ${i * 0.18}s infinite`,
            "@keyframes bounce": {
              "0%, 80%, 100%": { transform: "translateY(0)", opacity: 0.4 },
              "40%": { transform: "translateY(-4px)", opacity: 0.9 },
            },
          }}
        />
      ))}
    </Box>
  );
}
