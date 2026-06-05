import { Box, Paper, Stack, Typography } from "@mui/material";
import FlightTakeoffIcon from "@mui/icons-material/FlightTakeoff";
import { FS_BORDER, FS_MUTED, FS_NAVY, FS_SKY } from "../theme";

interface Props {
  examples: string[];
  onPickExample: (q: string) => void;
}

export default function EmptyHero({ examples, onPickExample }: Props) {
  return (
    <Box sx={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", py: 6 }}>
      <Stack sx={{ alignItems: "center", mb: 5, gap: 2.5 }}>
        <Box
          sx={{
            width: 56,
            height: 56,
            borderRadius: "50%",
            bgcolor: FS_NAVY,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 4px 16px rgba(0,0,34,0.18)",
          }}
        >
          <FlightTakeoffIcon sx={{ color: FS_SKY, fontSize: 28 }} />
        </Box>
        <Stack sx={{ alignItems: "center", gap: 0.5 }}>
          <Typography variant="h1" sx={{ textAlign: "center" }}>
            FSISIM Issue Resolution
          </Typography>
          <Typography sx={{ color: FS_MUTED, textAlign: "center", maxWidth: 520 }}>
            Search past G001 simulator issues, resolve acronyms against technical manuals, and surface
            prior resolutions in seconds.
          </Typography>
        </Stack>
      </Stack>

      <Stack spacing={1.5} sx={{ width: "100%", maxWidth: 640, mx: "auto" }}>
        <Typography variant="overline" sx={{ textAlign: "left", mb: 0.5 }}>
          Try one of these
        </Typography>
        {examples.map((q, i) => (
          <Paper
            key={i}
            onClick={() => onPickExample(q)}
            elevation={0}
            sx={{
              p: 1.75,
              border: `1px solid ${FS_BORDER}`,
              borderRadius: 2,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 1.5,
              transition: "all 0.15s",
              "&:hover": {
                borderColor: FS_NAVY,
                bgcolor: "#FFFFFF",
                boxShadow: "0 4px 12px rgba(0,0,34,0.06)",
                transform: "translateY(-1px)",
              },
            }}
          >
            <Box
              sx={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                bgcolor: FS_SKY,
                flexShrink: 0,
              }}
            />
            <Typography sx={{ fontSize: 14, color: FS_NAVY, fontWeight: 500 }}>{q}</Typography>
          </Paper>
        ))}
      </Stack>
    </Box>
  );
}
