import { createTheme } from "@mui/material/styles";

export const FS_NAVY = "#003865";
export const FS_GOLD = "#FFB81C";
export const FS_BG = "#FAFAFA";
export const FS_TEXT = "#1A1A1A";

export const fsTheme = createTheme({
  palette: {
    primary: { main: FS_NAVY, contrastText: "#FFFFFF" },
    secondary: { main: FS_GOLD, contrastText: FS_NAVY },
    background: { default: FS_BG, paper: "#FFFFFF" },
    text: { primary: FS_TEXT, secondary: "#555" },
  },
  typography: {
    fontFamily: "'Roboto', 'Helvetica', 'Arial', sans-serif",
    h1: { fontSize: "22px", fontWeight: 700, color: FS_NAVY },
    h2: { fontSize: "18px", fontWeight: 600, color: FS_NAVY },
    body1: { fontSize: "14px", lineHeight: 1.5 },
  },
  shape: { borderRadius: 6 },
  components: {
    MuiButton: { styleOverrides: { root: { textTransform: "none", fontWeight: 600 } } },
  },
});
