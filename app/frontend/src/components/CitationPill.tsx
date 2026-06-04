import { Chip } from "@mui/material";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import BugReportOutlinedIcon from "@mui/icons-material/BugReportOutlined";
import { FS_NAVY, FS_SKY, FS_SKY_LIGHT, FS_BORDER, FS_MUTED } from "../theme";

export type Citation =
  | { kind: "issue"; issueId: number; issueType: string; simName: string; noteType: string; preview: string }
  | { kind: "manual"; sourcePdf: string; filename: string; title: string; pageFirst: number; pageLast: number; preview: string };

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
  const isIssue = c.kind === "issue";
  const label = isIssue
    ? `Issue #${c.issueId} · ${c.simName}`
    : `${c.title} · ${pageLabel(c.pageFirst, c.pageLast)}`;

  return (
    <Chip
      icon={isIssue ? <BugReportOutlinedIcon /> : <DescriptionOutlinedIcon />}
      label={label}
      onClick={onClick}
      size="small"
      sx={{
        bgcolor: isIssue ? FS_SKY_LIGHT : "#FFFFFF",
        color: isIssue ? FS_NAVY : FS_MUTED,
        border: `1px solid ${isIssue ? FS_SKY : FS_BORDER}`,
        fontWeight: 600,
        fontSize: 11.5,
        height: 24,
        mr: 0.5,
        mb: 0.5,
        cursor: "pointer",
        "& .MuiChip-icon": {
          color: isIssue ? FS_SKY : FS_NAVY,
          fontSize: 14,
          ml: 0.5,
          mr: -0.25,
        },
        "& .MuiChip-label": { px: 0.875, letterSpacing: "0.005em" },
        transition: "all 0.12s",
        "&:hover": {
          bgcolor: isIssue ? "#D6E4F6" : "#F4F5F8",
          borderColor: FS_NAVY,
          color: FS_NAVY,
        },
      }}
    />
  );
}
