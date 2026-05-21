import { Chip } from "@mui/material";
import { FS_NAVY, FS_GOLD } from "../theme";

export type Citation =
  | { kind: "issue"; issueId: number; noteType: string; preview: string }
  | { kind: "manual"; sourcePdf: string; pageFirst: number; pageLast: number; preview: string };

interface Props {
  c: Citation;
  onClick: () => void;
}

function pageLabel(first: number, last: number): string {
  if (!first && !last) return "";
  if (!last || first === last) return `p.${first}`;
  return `p.${first}-${last}`;
}

export default function CitationPill({ c, onClick }: Props) {
  const label = c.kind === "issue"
    ? `Issue #${c.issueId} (${c.noteType})`
    : `${c.sourcePdf.split("/").pop()?.replace(".pdf", "")} · ${pageLabel(c.pageFirst, c.pageLast)}`;
  const color = c.kind === "issue" ? FS_NAVY : FS_GOLD;
  const text = c.kind === "issue" ? "#fff" : FS_NAVY;
  return (
    <Chip
      label={label}
      onClick={onClick}
      size="small"
      sx={{
        bgcolor: color, color: text, fontWeight: 600, mr: 0.5, mb: 0.5,
        "&:hover": { bgcolor: color, opacity: 0.85 },
      }}
    />
  );
}
