import { useEffect, useState } from "react";
import {
  Box,
  Button,
  List,
  ListItemButton,
  ListItemText,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import { listThreads, type ThreadSummary } from "../api/chat";
import { FS_NAVY, FS_BORDER, FS_MUTED } from "../theme";

interface Props {
  currentThreadId: string | null;
  onSelectThread: (threadId: string | null) => void;
  refreshTrigger: number;
}

export default function LeftRail({ currentThreadId, onSelectThread, refreshTrigger }: Props) {
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

  return (
    <Box
      sx={{
        width: 260,
        bgcolor: "#FAFBFC",
        borderRight: `1px solid ${FS_BORDER}`,
        display: "flex",
        flexDirection: "column",
        height: "100%",
      }}
    >
      <Box sx={{ p: 1.5 }}>
        <Button
          fullWidth
          startIcon={<AddIcon />}
          variant="outlined"
          onClick={() => onSelectThread(null)}
          sx={{
            justifyContent: "flex-start",
            color: FS_NAVY,
            borderColor: FS_BORDER,
            textTransform: "none",
          }}
        >
          New chat
        </Button>
      </Box>
      <Typography
        variant="overline"
        sx={{ px: 2, color: FS_MUTED, fontSize: 10, mt: 1 }}
      >
        Recent threads
      </Typography>
      <Box sx={{ flex: 1, overflowY: "auto" }}>
        {loading && (
          <Typography sx={{ px: 2, py: 1, fontSize: 12, color: FS_MUTED }}>
            Loading…
          </Typography>
        )}
        {!loading && threads.length === 0 && (
          <Typography sx={{ px: 2, py: 1, fontSize: 12, color: FS_MUTED }}>
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
                "&.Mui-selected": { bgcolor: "#E8EEF7" },
              }}
            >
              <ListItemText
                primary={t.title}
                secondary={new Date(t.updated_at).toLocaleDateString()}
                slotProps={{
                  primary: {
                    sx: {
                      fontSize: 13,
                      color: FS_NAVY,
                      fontWeight: t.thread_id === currentThreadId ? 600 : 400,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    },
                  },
                  secondary: { sx: { fontSize: 10, color: FS_MUTED } },
                }}
              />
            </ListItemButton>
          ))}
        </List>
      </Box>
    </Box>
  );
}
