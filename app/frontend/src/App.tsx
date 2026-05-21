import { Box, AppBar, Toolbar, Typography, Avatar } from "@mui/material";
import { FS_NAVY, FS_GOLD } from "./theme";
import LeftRail from "./components/LeftRail";
import ChatThread from "./components/ChatThread";
import { useState } from "react";

const EXAMPLES = [
  "G001-SIM-01 hydraulic pressure drop on takeoff. Anything similar?",
  "What does FMS VNAV stand for?",
  "Motion platform fault code 47B on G001-SIM-03",
  "Visual database corruption at KJFK approach",
  "How was the connector reseating procedure handled last time?",
];

export default function App() {
  const [pendingExample, setPendingExample] = useState<string | null>(null);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <AppBar position="static" elevation={0} sx={{ borderBottom: `3px solid ${FS_GOLD}` }}>
        <Toolbar sx={{ gap: 2 }}>
          <Box sx={{
            width: 36, height: 36, bgcolor: FS_GOLD, color: FS_NAVY,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontWeight: 700, borderRadius: 1,
          }}>FS</Box>
          <Typography variant="h6" sx={{ fontWeight: 700, color: "#fff" }}>
            FlightSafety
          </Typography>
          <Box sx={{ flex: 1 }} />
          <Typography variant="body2" sx={{ color: "#fff", opacity: 0.85 }}>
            FSISIM Issue Resolution Agent (Scaffold)
          </Typography>
          <Box sx={{ flex: 1 }} />
          <Avatar sx={{ bgcolor: FS_GOLD, color: FS_NAVY, width: 32, height: 32, fontSize: 14 }}>JW</Avatar>
        </Toolbar>
      </AppBar>

      <Box sx={{ display: "flex", flex: 1, overflow: "hidden" }}>
        <LeftRail examples={EXAMPLES} onPick={setPendingExample} />
        <Box sx={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <ChatThread pendingExample={pendingExample} onConsumeExample={() => setPendingExample(null)} />
          <Box sx={{ p: 1, textAlign: "center", color: "#888", fontSize: 11, bgcolor: "#F5F5F5" }}>
            Scaffold build / mock data / not for customer use
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
