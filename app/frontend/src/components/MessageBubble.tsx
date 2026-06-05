import { useState } from "react";
import { Box, IconButton, Typography } from "@mui/material";
import ThumbUpAltOutlinedIcon from "@mui/icons-material/ThumbUpAltOutlined";
import ThumbUpAltIcon from "@mui/icons-material/ThumbUpAlt";
import ThumbDownAltOutlinedIcon from "@mui/icons-material/ThumbDownAltOutlined";
import ThumbDownAltIcon from "@mui/icons-material/ThumbDownAlt";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { postFeedback } from "../api/chat";
import type { Citation } from "./CitationPill";
import CitationPill from "./CitationPill";
import { FS_NAVY, FS_BORDER, FS_MUTED, FS_SKY } from "../theme";

interface Props {
  role: "user" | "assistant";
  text: string;
  citations?: Citation[];
  assistantMessageId?: string;
  initialRating?: "up" | "down" | null;
  onCitationClick?: (c: Citation) => void;
}

export default function MessageBubble({
  role,
  text,
  citations,
  assistantMessageId,
  initialRating = null,
  onCitationClick,
}: Props) {
  const [rating, setRating] = useState<"up" | "down" | null>(initialRating);
  const [submitting, setSubmitting] = useState(false);

  const submit = async (next: "up" | "down") => {
    if (!assistantMessageId || submitting) return;
    const prev = rating;
    setRating(next);
    setSubmitting(true);
    const ok = await postFeedback(assistantMessageId, next);
    setSubmitting(false);
    if (!ok) setRating(prev); // roll back on failure
  };

  if (role === "user") {
    return (
      <Box sx={{ alignSelf: "flex-end", maxWidth: "78%", my: 0.5 }}>
        <Box
          sx={{
            bgcolor: FS_NAVY,
            color: "#FFFFFF",
            px: 2,
            py: 1.25,
            borderRadius: 2,
            fontSize: 14,
            whiteSpace: "pre-wrap",
          }}
        >
          {text}
        </Box>
      </Box>
    );
  }

  return (
    <Box sx={{ alignSelf: "flex-start", maxWidth: "92%", my: 0.5 }}>
      <Box
        sx={{
          bgcolor: "#FFFFFF",
          color: FS_NAVY,
          border: `1px solid ${FS_BORDER}`,
          px: 2,
          py: 1.25,
          borderRadius: 2,
          fontSize: 14,
          lineHeight: 1.55,
          "& p": { my: 0.75 },
          "& p:first-of-type": { mt: 0 },
          "& p:last-of-type": { mb: 0 },
          "& strong": { fontWeight: 700 },
          "& em": { fontStyle: "italic" },
          "& ul, & ol": { pl: 3, my: 0.75 },
          "& li": { my: 0.25 },
          "& code": {
            bgcolor: "#F4F5F8",
            px: 0.5,
            py: 0.125,
            borderRadius: 0.5,
            fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
            fontSize: 13,
          },
          "& pre": {
            bgcolor: "#F4F5F8",
            p: 1.25,
            borderRadius: 1,
            overflowX: "auto",
            my: 1,
            "& code": { bgcolor: "transparent", p: 0 },
          },
          "& h1, & h2, & h3, & h4": {
            fontWeight: 700,
            mt: 1.25,
            mb: 0.5,
            "&:first-of-type": { mt: 0 },
          },
          "& h1": { fontSize: 18 },
          "& h2": { fontSize: 16 },
          "& h3, & h4": { fontSize: 15 },
          "& blockquote": {
            borderLeft: `3px solid ${FS_SKY}`,
            pl: 1.5,
            ml: 0,
            my: 0.75,
            color: FS_MUTED,
          },
          "& a": { color: FS_SKY, textDecoration: "underline" },
          "& table": {
            borderCollapse: "collapse",
            my: 1,
            fontSize: 13,
          },
          "& th, & td": {
            border: `1px solid ${FS_BORDER}`,
            px: 1,
            py: 0.5,
            textAlign: "left",
          },
          "& th": { bgcolor: "#FAFBFC", fontWeight: 600 },
        }}
      >
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
      </Box>
      {citations && citations.length > 0 && (
        <Box sx={{ mt: 0.75, display: "flex", flexWrap: "wrap" }}>
          {citations.map((c, i) => (
            <CitationPill key={i} c={c} onClick={() => onCitationClick?.(c)} />
          ))}
        </Box>
      )}
      {assistantMessageId && (
        <Box sx={{ mt: 0.5, display: "flex", alignItems: "center", gap: 0.5 }}>
          <IconButton
            size="small"
            onClick={() => submit("up")}
            disabled={submitting}
            sx={{ color: rating === "up" ? FS_NAVY : FS_MUTED, padding: 0.25 }}
            aria-label="thumbs up"
          >
            {rating === "up" ? <ThumbUpAltIcon fontSize="inherit" /> : <ThumbUpAltOutlinedIcon fontSize="inherit" />}
          </IconButton>
          <IconButton
            size="small"
            onClick={() => submit("down")}
            disabled={submitting}
            sx={{ color: rating === "down" ? FS_NAVY : FS_MUTED, padding: 0.25 }}
            aria-label="thumbs down"
          >
            {rating === "down" ? <ThumbDownAltIcon fontSize="inherit" /> : <ThumbDownAltOutlinedIcon fontSize="inherit" />}
          </IconButton>
          <Typography sx={{ fontSize: 10, color: FS_MUTED, ml: 1 }}>
            {rating ? "Thanks for the feedback" : "Was this helpful?"}
          </Typography>
        </Box>
      )}
    </Box>
  );
}
