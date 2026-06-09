import { useEffect, useState } from "react";
import {
  Box,
  AppBar,
  Toolbar,
  Avatar,
  IconButton,
  Stack,
  Tooltip,
  Typography,
  useTheme,
} from "@mui/material";
import FlightTakeoffIcon from "@mui/icons-material/FlightTakeoff";
import ViewSidebarOutlinedIcon from "@mui/icons-material/ViewSidebarOutlined";
import { FS_NAVY, FS_SKY } from "./theme";
import ChatThread from "./components/ChatThread";
import LeftRail from "./components/LeftRail";

export const EXAMPLES = [
  "G001-SIM-01 hydraulic pressure drop on takeoff. Anything similar?",
  "What does FMS VNAV stand for and how is it used in our sims?",
  "Motion platform fault code 47B on G001-SIM-03",
  "Visual database corruption at KJFK approach",
  "How was the connector reseating procedure handled last time?",
];

const SIDEBAR_STATE_KEY = "fsisim.sidebar";

export default function App() {
  const theme = useTheme();
  const [threadId, setThreadId] = useState<string | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(() => {
    if (typeof window === "undefined") return true;
    return window.localStorage.getItem(SIDEBAR_STATE_KEY) !== "closed";
  });

  useEffect(() => {
    window.localStorage.setItem(SIDEBAR_STATE_KEY, sidebarOpen ? "open" : "closed");
  }, [sidebarOpen]);

  const onThreadChange = (newId: string) => {
    setThreadId(newId);
    setRefreshTrigger((n) => n + 1);
  };

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
              sx={{ height: 28, filter: "brightness(0) invert(1)", opacity: 0.96 }}
            />
            <Box sx={{ width: "1px", height: 22, bgcolor: "rgba(255,255,255,0.18)", mx: 1.5, flexShrink: 0 }} />
            <Stack direction="row" sx={{ alignItems: "center", gap: 1 }}>
              <FlightTakeoffIcon sx={{ color: FS_SKY, fontSize: 18 }} />
              <Typography
                sx={{ color: "rgba(255,255,255,0.95)", fontWeight: 600, fontSize: 14, letterSpacing: "-0.005em" }}
              >
                FSISIM Issue Resolution Agent
              </Typography>
            </Stack>
          </Stack>
          <Box sx={{ flex: 1 }} />
          <Stack direction="row" sx={{ alignItems: "center", gap: 2 }}>
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
        {sidebarOpen && (
          <LeftRail
            currentThreadId={threadId}
            onSelectThread={setThreadId}
            refreshTrigger={refreshTrigger}
            onCollapse={() => setSidebarOpen(false)}
          />
        )}
        <Box sx={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", position: "relative" }}>
          {!sidebarOpen && (
            <Box
              sx={{
                position: "absolute",
                top: 8,
                left: 8,
                zIndex: 10,
              }}
            >
              <Tooltip title="Open sidebar" placement="right">
                <IconButton
                  size="small"
                  onClick={() => setSidebarOpen(true)}
                  sx={{
                    color: theme.palette.text.secondary,
                    bgcolor: theme.palette.background.paper,
                    border: `1px solid ${theme.palette.divider}`,
                    "&:hover": {
                      color: theme.palette.text.primary,
                      bgcolor: theme.palette.background.paper,
                    },
                  }}
                  aria-label="open sidebar"
                >
                  <ViewSidebarOutlinedIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>
          )}
          <ChatThread examples={EXAMPLES} threadId={threadId} onThreadChange={onThreadChange} />
        </Box>
      </Box>
    </Box>
  );
}
