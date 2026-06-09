import { Chip, useTheme } from "@mui/material";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import BugReportOutlinedIcon from "@mui/icons-material/BugReportOutlined";
import { FS_NAVY, FS_SKY, FS_SKY_LIGHT, FS_SKY_LIGHT_DARK } from "../theme";

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
  const theme = useTheme();
  const isDark = theme.palette.mode === "dark";
  const isIssue = c.kind === "issue";
  const label = isIssue
    ? `Issue #${c.issueId} · ${c.simName}`
    : `${c.title} · ${pageLabel(c.pageFirst, c.pageLast)}`;

  const issueBg = isDark ? FS_SKY_LIGHT_DARK : FS_SKY_LIGHT;
  const manualBg = theme.palette.background.paper;
  const textColor = theme.palette.text.primary;
  const mutedColor = theme.palette.text.secondary;
  const iconColor = isIssue ? FS_SKY : textColor;
  const hoverBg = isIssue
    ? (isDark ? "#264166" : "#D6E4F6")
    : (isDark ? "rgba(255,255,255,0.06)" : "#F4F5F8");

  return (
    <Chip
      icon={isIssue ? <BugReportOutlinedIcon /> : <DescriptionOutlinedIcon />}
      label={label}
      onClick={onClick}
      size="small"
      sx={{
        bgcolor: isIssue ? issueBg : manualBg,
        color: isIssue ? textColor : mutedColor,
        border: `1px solid ${isIssue ? FS_SKY : theme.palette.divider}`,
        fontWeight: 600,
        fontSize: 11.5,
        height: 24,
        mr: 0.5,
        mb: 0.5,
        cursor: "pointer",
        "& .MuiChip-icon": {
          color: iconColor,
          fontSize: 14,
          ml: 0.5,
          mr: -0.25,
        },
        "& .MuiChip-label": { px: 0.875, letterSpacing: "0.005em" },
        transition: "all 0.12s",
        "&:hover": {
          bgcolor: hoverBg,
          borderColor: isDark ? FS_SKY : FS_NAVY,
          color: textColor,
        },
      }}
    />
  );
}
