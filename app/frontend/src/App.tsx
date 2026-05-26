import { useState } from "react";
import { Box, AppBar, Toolbar, Avatar, Stack, Typography, Chip } from "@mui/material";
import FlightTakeoffIcon from "@mui/icons-material/FlightTakeoff";
import { FS_NAVY, FS_SKY, FS_BORDER, FS_MUTED } from "./theme";
import ChatThread from "./components/ChatThread";

export const EXAMPLES = [
  "G001-SIM-01 hydraulic pressure drop on takeoff. Anything similar?",
  "What does FMS VNAV stand for and how is it used in our sims?",
  "Motion platform fault code 47B on G001-SIM-03",
  "Visual database corruption at KJFK approach",
  "How was the connector reseating procedure handled last time?",
];

export default function App() {
  const [pendingExample, setPendingExample] = useState<string | null>(null);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100vh", bgcolor: "background.default" }}>
      <AppBar
        position="static"
        elevation={0}
        sx={{
          bgcolor: FS_NAVY,
          backgroundImage: `linear-gradient(180deg, ${FS_NAVY} 0%, #050530 100%)`,
          borderBottom: "1px solid rgba(255,255,255,0.06)",
        }}
      >
        <Toolbar sx={{ minHeight: 64, px: { xs: 2, sm: 3 } }}>
          <Stack direction="row" sx={{ alignItems: "center", gap: 1.5 }}>
            <Box
              component="img"
              src="/fsi-logo.svg"
              alt="FlightSafety"
              sx={{
                height: 28,
                filter: "brightness(0) invert(1)",
                opacity: 0.96,
              }}
            />
            <Box sx={{ width: "1px", height: 22, bgcolor: "rgba(255,255,255,0.18)", mx: 1.5, flexShrink: 0 }} />
            <Stack direction="row" sx={{ alignItems: "center", gap: 1 }}>
              <FlightTakeoffIcon sx={{ color: FS_SKY, fontSize: 18 }} />
              <Typography
                sx={{
                  color: "rgba(255,255,255,0.95)",
                  fontWeight: 600,
                  fontSize: 14,
                  letterSpacing: "-0.005em",
                }}
              >
                FSISIM Issue Resolution Assistant
              </Typography>
              <Chip
                label="SCAFFOLD"
                size="small"
                sx={{
                  bgcolor: "rgba(255,255,255,0.08)",
                  color: "rgba(255,255,255,0.7)",
                  fontSize: 10,
                  fontWeight: 700,
                  letterSpacing: "0.08em",
                  height: 20,
                  border: "1px solid rgba(255,255,255,0.15)",
                  "& .MuiChip-label": { px: 1 },
                }}
              />
            </Stack>
          </Stack>
          <Box sx={{ flex: 1 }} />
          <Stack direction="row" sx={{ alignItems: "center", gap: 2 }}>
            <Typography sx={{ color: "rgba(255,255,255,0.55)", fontSize: 12, display: { xs: "none", md: "block" } }}>
              Mock data
            </Typography>
            <Avatar
              sx={{
                width: 32,
                height: 32,
                bgcolor: FS_SKY,
                fontSize: 13,
                fontWeight: 700,
                border: "2px solid rgba(255,255,255,0.15)",
              }}
            >
              JW
            </Avatar>
          </Stack>
        </Toolbar>
      </AppBar>

      <Box sx={{ display: "flex", flex: 1, overflow: "hidden" }}>
        <Box sx={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", position: "relative" }}>
          <ChatThread
            examples={EXAMPLES}
            pendingExample={pendingExample}
            onConsumeExample={() => setPendingExample(null)}
            onPickExample={setPendingExample}
          />
          <Box
            sx={{
              py: 0.75,
              px: 2,
              textAlign: "center",
              color: FS_MUTED,
              fontSize: 11,
              bgcolor: "#F4F5F8",
              borderTop: `1px solid ${FS_BORDER}`,
              letterSpacing: "0.03em",
            }}
          >
            Scaffold build · Synthetic data · Not for customer use
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
