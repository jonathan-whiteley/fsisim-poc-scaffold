import { Drawer, Box, Typography, IconButton } from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import type { Citation } from "./CitationPill";
import { FS_NAVY } from "../theme";

interface Props {
  open: boolean;
  citation: Citation | null;
  onClose: () => void;
}

export default function CitationSlideOver({ open, citation, onClose }: Props) {
  return (
    <Drawer anchor="right" open={open} onClose={onClose} slotProps={{ paper: { sx: { width: 480 } } }}>
      <Box sx={{ p: 3 }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
          <Typography variant="h2" sx={{ color: FS_NAVY }}>
            {citation?.kind === "issue" ? `Issue #${citation.issueId}` : `Manual: ${citation?.kind === "manual" ? citation.sourcePdf.split("/").pop() : ""}`}
          </Typography>
          <IconButton onClick={onClose}><CloseIcon /></IconButton>
        </Box>
        {citation?.kind === "issue" && (
          <>
            <Typography variant="overline">Note type</Typography>
            <Typography sx={{ mb: 2 }}>{citation.noteType}</Typography>
            <Typography variant="overline">Composite text</Typography>
            <Typography sx={{ whiteSpace: "pre-wrap" }}>{citation.preview}</Typography>
          </>
        )}
        {citation?.kind === "manual" && (
          <>
            <Typography variant="overline">Pages</Typography>
            <Typography sx={{ mb: 2 }}>
              {citation.pageFirst === citation.pageLast || !citation.pageLast
                ? `p. ${citation.pageFirst}`
                : `p. ${citation.pageFirst}-${citation.pageLast}`}
            </Typography>
            <Typography variant="overline">Excerpt</Typography>
            <Typography sx={{ whiteSpace: "pre-wrap" }}>{citation.preview}</Typography>
          </>
        )}
      </Box>
    </Drawer>
  );
}
