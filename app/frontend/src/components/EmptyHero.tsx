import { Box, Paper, Stack, Typography, useTheme } from "@mui/material";
import FlightTakeoffIcon from "@mui/icons-material/FlightTakeoff";
import { FS_NAVY, FS_SKY } from "../theme";

interface Props {
  examples: string[];
  onPickExample: (q: string) => void;
}

export default function EmptyHero({ examples, onPickExample }: Props) {
  const theme = useTheme();
  const isDark = theme.palette.mode === "dark";

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
            boxShadow: isDark ? "0 4px 16px rgba(0,0,0,0.5)" : "0 4px 16px rgba(0,0,34,0.18)",
            border: isDark ? `1px solid ${theme.palette.divider}` : "none",
          }}
        >
          <FlightTakeoffIcon sx={{ color: FS_SKY, fontSize: 28 }} />
        </Box>
        <Stack sx={{ alignItems: "center", gap: 0.5 }}>
          <Typography variant="h1" sx={{ textAlign: "center", color: theme.palette.text.primary }}>
            FSISIM Issue Resolution
          </Typography>
          <Typography sx={{ color: theme.palette.text.secondary, textAlign: "center", maxWidth: 520 }}>
            Search past G001 simulator issues, resolve acronyms against technical manuals, and surface
            prior resolutions in seconds.
          </Typography>
        </Stack>
      </Stack>

      <Stack spacing={1.5} sx={{ width: "100%", maxWidth: 640, mx: "auto" }}>
        <Typography
          variant="overline"
          sx={{ textAlign: "left", mb: 0.5, color: theme.palette.text.secondary }}
        >
          Try one of these
        </Typography>
        {examples.map((q, i) => (
          <Paper
            key={i}
            onClick={() => onPickExample(q)}
            elevation={0}
            sx={{
              p: 1.75,
              bgcolor: theme.palette.background.paper,
              border: `1px solid ${theme.palette.divider}`,
              borderRadius: 2,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 1.5,
              transition: "all 0.15s",
              "&:hover": {
                borderColor: isDark ? FS_SKY : FS_NAVY,
                bgcolor: isDark ? "rgba(42,111,181,0.10)" : "#FFFFFF",
                boxShadow: isDark
                  ? "0 4px 12px rgba(0,0,0,0.4)"
                  : "0 4px 12px rgba(0,0,34,0.06)",
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
            <Typography
              sx={{
                fontSize: 14,
                color: theme.palette.text.primary,
                fontWeight: 500,
              }}
            >
              {q}
            </Typography>
          </Paper>
        ))}
      </Stack>
    </Box>
  );
}
