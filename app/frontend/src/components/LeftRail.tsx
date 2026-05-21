import { Box, Typography, ListItemButton, Divider } from "@mui/material";
import { FS_NAVY } from "../theme";

interface Props {
  examples: string[];
  onPick: (q: string) => void;
}

export default function LeftRail({ examples, onPick }: Props) {
  return (
    <Box sx={{
      width: 280, borderRight: "1px solid #E0E0E0", bgcolor: "#FAFAFA",
      p: 2, overflowY: "auto",
    }}>
      <Typography variant="overline" sx={{ color: FS_NAVY, fontWeight: 700 }}>
        Example questions
      </Typography>
      <Divider sx={{ my: 1 }} />
      {examples.map((q, i) => (
        <ListItemButton
          key={i}
          onClick={() => onPick(q)}
          sx={{ borderRadius: 1, mb: 0.5, fontSize: 13, color: "#333", lineHeight: 1.4 }}
        >
          {q}
        </ListItemButton>
      ))}
    </Box>
  );
}
