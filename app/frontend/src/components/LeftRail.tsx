import { useEffect, useState } from "react";
import {
  Box,
  Divider,
  IconButton,
  List,
  ListItemButton,
  ListItemText,
  Tooltip,
  Typography,
  useTheme,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import ViewSidebarOutlinedIcon from "@mui/icons-material/ViewSidebarOutlined";
import DarkModeOutlinedIcon from "@mui/icons-material/DarkModeOutlined";
import LightModeOutlinedIcon from "@mui/icons-material/LightModeOutlined";
import { listThreads, type ThreadSummary } from "../api/chat";
import { useThemeMode } from "../themeMode";

interface Props {
  currentThreadId: string | null;
  onSelectThread: (threadId: string | null) => void;
  refreshTrigger: number;
  onCollapse: () => void;
}

export default function LeftRail({
  currentThreadId,
  onSelectThread,
  refreshTrigger,
  onCollapse,
}: Props) {
  const theme = useTheme();
  const { mode, toggle: toggleMode } = useThemeMode();
  const [threads, setThreads] = useState<ThreadSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      const data = await listThreads();
      if (!cancelled) {
        setThreads(data);
        setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refreshTrigger]);

  const accentText = theme.palette.text.primary;
  const mutedText = theme.palette.text.secondary;
  const selectedBg = mode === "dark" ? "rgba(42,111,181,0.18)" : "#E8EEF7";

  return (
    <Box
      sx={{
        width: 260,
        bgcolor: theme.palette.background.paper,
        borderRight: `1px solid ${theme.palette.divider}`,
        display: "flex",
        flexDirection: "column",
        height: "100%",
        color: accentText,
      }}
    >
      <Box
        sx={{
          px: 1.5,
          pt: 1.5,
          pb: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 0.5,
        }}
      >
        <Tooltip title="Collapse sidebar" placement="bottom">
          <IconButton
            size="small"
            onClick={onCollapse}
            sx={{ color: mutedText, "&:hover": { color: accentText } }}
            aria-label="collapse sidebar"
          >
            <ViewSidebarOutlinedIcon fontSize="small" />
          </IconButton>
        </Tooltip>
        <Tooltip title="New chat" placement="bottom">
          <IconButton
            size="small"
            onClick={() => onSelectThread(null)}
            sx={{ color: mutedText, "&:hover": { color: accentText } }}
            aria-label="new chat"
          >
            <AddIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>
      <Typography
        variant="overline"
        sx={{ px: 2, color: mutedText, fontSize: 10, mt: 1 }}
      >
        Recent threads
      </Typography>
      <Box sx={{ flex: 1, overflowY: "auto" }}>
        {loading && (
          <Typography sx={{ px: 2, py: 1, fontSize: 12, color: mutedText }}>
            Loading…
          </Typography>
        )}
        {!loading && threads.length === 0 && (
          <Typography sx={{ px: 2, py: 1, fontSize: 12, color: mutedText }}>
            No threads yet.
          </Typography>
        )}
        <List dense disablePadding>
          {threads.map((t) => (
            <ListItemButton
              key={t.thread_id}
              selected={t.thread_id === currentThreadId}
              onClick={() => onSelectThread(t.thread_id)}
              sx={{
                px: 2,
                "&.Mui-selected": { bgcolor: selectedBg },
                "&.Mui-selected:hover": { bgcolor: selectedBg },
              }}
            >
              <ListItemText
                primary={t.title}
                slotProps={{
                  primary: {
                    sx: {
                      fontSize: 13,
                      color: accentText,
                      fontWeight: t.thread_id === currentThreadId ? 600 : 400,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    },
                  },
                  secondary: { sx: { fontSize: 10, color: mutedText } },
                }}
                secondary={new Date(t.updated_at).toLocaleDateString()}
              />
            </ListItemButton>
          ))}
        </List>
      </Box>
      <Divider sx={{ borderColor: theme.palette.divider }} />
      <Box sx={{ p: 1, display: "flex", justifyContent: "flex-end" }}>
        <Tooltip
          title={mode === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          placement="top"
        >
          <IconButton
            size="small"
            onClick={toggleMode}
            sx={{ color: mutedText, "&:hover": { color: accentText } }}
            aria-label="toggle color mode"
          >
            {mode === "dark" ? (
              <LightModeOutlinedIcon fontSize="small" />
            ) : (
              <DarkModeOutlinedIcon fontSize="small" />
            )}
          </IconButton>
        </Tooltip>
      </Box>
    </Box>
  );
}
