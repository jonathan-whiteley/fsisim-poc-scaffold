import { Drawer, Box, Typography, IconButton, Button, Chip, Stack } from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import BugReportOutlinedIcon from "@mui/icons-material/BugReportOutlined";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import type { Citation } from "./CitationPill";
import { FS_NAVY, FS_BORDER, FS_MUTED, FS_SKY_LIGHT } from "../theme";

interface Props {
  open: boolean;
  citation: Citation | null;
  onClose: () => void;
}

function pageLabel(first: number, last: number): string {
  if (!first && !last) return "";
  if (!last || first === last) return `p.${first}`;
  return `p.${first}-${last}`;
}

export default function CitationSlideOver({ open, citation, onClose }: Props) {
  if (!citation) return <Drawer anchor="right" open={open} onClose={onClose} />;

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      slotProps={{ paper: { sx: { width: { xs: "100%", sm: 520 } } } }}
    >
      <Box sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
        <Box
          sx={{
            px: 3,
            py: 2,
            borderBottom: `1px solid ${FS_BORDER}`,
            display: "flex",
            alignItems: "center",
            gap: 1.5,
            bgcolor: "#FFFFFF",
          }}
        >
          <Box
            sx={{
              width: 36,
              height: 36,
              borderRadius: 1,
              bgcolor: citation.kind === "issue" ? FS_SKY_LIGHT : "#F4F5F8",
              color: FS_NAVY,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {citation.kind === "issue" ? <BugReportOutlinedIcon /> : <DescriptionOutlinedIcon />}
          </Box>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography variant="overline" sx={{ color: FS_MUTED, fontSize: 10 }}>
              {citation.kind === "issue" ? "Past issue" : "Technical manual"}
            </Typography>
            <Typography
              variant="h2"
              sx={{ fontSize: 18, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}
            >
              {citation.kind === "issue" ? `Issue #${citation.issueId}` : citation.title}
            </Typography>
          </Box>
          <IconButton onClick={onClose} size="small"><CloseIcon /></IconButton>
        </Box>

        <Box sx={{ flex: 1, overflowY: "auto", p: 3 }}>
          {citation.kind === "issue" && (
            <Stack sx={{ gap: 2 }}>
              <Stack direction="row" sx={{ gap: 1, flexWrap: "wrap" }}>
                <Chip size="small" label={citation.issueType} sx={{ bgcolor: FS_SKY_LIGHT, color: FS_NAVY, fontWeight: 600 }} />
                <Chip size="small" label={citation.simName} sx={{ bgcolor: "#F4F5F8", color: FS_NAVY, fontWeight: 600 }} />
                <Chip
                  size="small"
                  label={citation.noteType}
                  sx={{ bgcolor: "#FFFFFF", color: FS_MUTED, border: `1px solid ${FS_BORDER}`, fontWeight: 600 }}
                />
              </Stack>
              <Box>
                <Typography variant="overline" sx={{ color: FS_MUTED, display: "block", mb: 0.5 }}>
                  Composite record
                </Typography>
                <Typography sx={{ whiteSpace: "pre-wrap", fontSize: 13.5, lineHeight: 1.6, color: FS_NAVY }}>
                  {citation.preview}
                </Typography>
              </Box>
            </Stack>
          )}

          {citation.kind === "manual" && (
            <Stack sx={{ gap: 2 }}>
              <Stack direction="row" sx={{ gap: 1, flexWrap: "wrap" }}>
                <Chip size="small" label={citation.filename} sx={{ bgcolor: "#F4F5F8", color: FS_NAVY, fontWeight: 600 }} />
                {pageLabel(citation.pageFirst, citation.pageLast) && (
                  <Chip
                    size="small"
                    label={pageLabel(citation.pageFirst, citation.pageLast)}
                    sx={{ bgcolor: FS_SKY_LIGHT, color: FS_NAVY, fontWeight: 600 }}
                  />
                )}
              </Stack>
              <Box>
                <Typography variant="overline" sx={{ color: FS_MUTED, display: "block", mb: 0.5 }}>
                  Excerpt
                </Typography>
                <Typography sx={{ whiteSpace: "pre-wrap", fontSize: 13.5, lineHeight: 1.6, color: FS_NAVY }}>
                  {citation.preview}
                </Typography>
              </Box>
              <Button
                href={`/api/manuals/${encodeURIComponent(citation.filename)}#page=${citation.pageFirst || 1}`}
                target="_blank"
                rel="noopener noreferrer"
                variant="contained"
                startIcon={<OpenInNewIcon />}
                sx={{ bgcolor: FS_NAVY, "&:hover": { bgcolor: "#000010" }, alignSelf: "flex-start", px: 2, py: 1 }}
              >
                Open PDF{citation.pageFirst ? ` at p.${citation.pageFirst}` : ""}
              </Button>
              <Typography variant="caption" sx={{ color: FS_MUTED }}>
                The PDF opens in a new tab. The page anchor only works in browsers whose built-in PDF viewer honors{" "}
                <code>#page=</code> fragments (Chrome and Firefox do).
              </Typography>
            </Stack>
          )}
        </Box>
      </Box>
    </Drawer>
  );
}
