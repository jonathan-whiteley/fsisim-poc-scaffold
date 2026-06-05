import { useState } from "react";
import { Box, IconButton, Typography } from "@mui/material";
import ThumbUpAltOutlinedIcon from "@mui/icons-material/ThumbUpAltOutlined";
import ThumbUpAltIcon from "@mui/icons-material/ThumbUpAlt";
import ThumbDownAltOutlinedIcon from "@mui/icons-material/ThumbDownAltOutlined";
import ThumbDownAltIcon from "@mui/icons-material/ThumbDownAlt";
import { postFeedback } from "../api/chat";
import type { Citation } from "./CitationPill";
import CitationPill from "./CitationPill";
import { FS_NAVY, FS_BORDER, FS_MUTED } from "../theme";

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
          whiteSpace: "pre-wrap",
        }}
      >
        {text}
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
