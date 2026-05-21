import { Box, Typography } from "@mui/material";
import { FS_NAVY } from "../theme";
import CitationPill, { type Citation } from "./CitationPill";

interface Props {
  role: "user" | "assistant";
  text: string;
  citations?: Citation[];
  onCitationClick?: (c: Citation) => void;
}

export default function MessageBubble({ role, text, citations, onCitationClick }: Props) {
  const isUser = role === "user";
  return (
    <Box sx={{
      alignSelf: isUser ? "flex-end" : "flex-start",
      maxWidth: "75%", my: 1,
      bgcolor: isUser ? FS_NAVY : "#FFF",
      color: isUser ? "#FFF" : "#222",
      border: isUser ? "none" : "1px solid #E0E0E0",
      borderRadius: 2, p: 1.5,
    }}>
      <Typography sx={{ whiteSpace: "pre-wrap" }}>{text}</Typography>
      {citations && citations.length > 0 && (
        <Box sx={{ mt: 1, display: "flex", flexWrap: "wrap" }}>
          {citations.map((c, i) => (
            <CitationPill key={i} c={c} onClick={() => onCitationClick?.(c)} />
          ))}
        </Box>
      )}
    </Box>
  );
}
