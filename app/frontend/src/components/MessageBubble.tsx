import { useState } from "react";
import { Box, IconButton, Typography, useTheme } from "@mui/material";
import ThumbUpAltOutlinedIcon from "@mui/icons-material/ThumbUpAltOutlined";
import ThumbUpAltIcon from "@mui/icons-material/ThumbUpAlt";
import ThumbDownAltOutlinedIcon from "@mui/icons-material/ThumbDownAltOutlined";
import ThumbDownAltIcon from "@mui/icons-material/ThumbDownAlt";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { postFeedback } from "../api/chat";
import type { Citation } from "./CitationPill";
import CitationPill from "./CitationPill";
import { FS_NAVY, FS_SKY } from "../theme";

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
  const theme = useTheme();
  const [rating, setRating] = useState<"up" | "down" | null>(initialRating);
  const [submitting, setSubmitting] = useState(false);
  const codeBg = theme.palette.mode === "dark" ? "rgba(255,255,255,0.06)" : "#F4F5F8";

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
          bgcolor: theme.palette.background.paper,
          color: theme.palette.text.primary,
          border: `1px solid ${theme.palette.divider}`,
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
            bgcolor: codeBg,
            px: 0.5,
            py: 0.125,
            borderRadius: 0.5,
            fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
            fontSize: 13,
          },
          "& pre": {
            bgcolor: codeBg,
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
            color: theme.palette.text.secondary,
          },
          "& a": { color: FS_SKY, textDecoration: "underline" },
          "& table": {
            borderCollapse: "collapse",
            my: 1,
            fontSize: 13,
          },
          "& th, & td": {
            border: `1px solid ${theme.palette.divider}`,
            px: 1,
            py: 0.5,
            textAlign: "left",
          },
          "& th": { bgcolor: codeBg, fontWeight: 600 },
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
            sx={{
              color: rating === "up" ? theme.palette.text.primary : theme.palette.text.secondary,
              padding: 0.25,
            }}
            aria-label="thumbs up"
          >
            {rating === "up" ? <ThumbUpAltIcon fontSize="inherit" /> : <ThumbUpAltOutlinedIcon fontSize="inherit" />}
          </IconButton>
          <IconButton
            size="small"
            onClick={() => submit("down")}
            disabled={submitting}
            sx={{
              color: rating === "down" ? theme.palette.text.primary : theme.palette.text.secondary,
              padding: 0.25,
            }}
            aria-label="thumbs down"
          >
            {rating === "down" ? <ThumbDownAltIcon fontSize="inherit" /> : <ThumbDownAltOutlinedIcon fontSize="inherit" />}
          </IconButton>
          <Typography sx={{ fontSize: 10, color: theme.palette.text.secondary, ml: 1 }}>
            {rating ? "Thanks for the feedback" : "Was this helpful?"}
          </Typography>
        </Box>
      )}
    </Box>
  );
}
