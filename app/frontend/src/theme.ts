import { createTheme } from "@mui/material/styles";

// FlightSafety brand. Primary is the exact color from their official logo SVG
// (https://www.flightsafety.com/wp-content/themes/Sky/assets/img/logo/FlightSafety-Logo-Color.svg).
// Accents derived from their site (cool grays, sky-blue hover, muted red highlight).
export const FS_NAVY = "#000022";
export const FS_NAVY_SOFT = "#0F1535";
export const FS_SKY = "#2A6FB5";
export const FS_SKY_LIGHT = "#E8F1FB";
export const FS_INK = "#1A1A2E";
export const FS_BORDER = "#E5E7EB";
export const FS_SURFACE = "#FAFBFD";
export const FS_TEXT = "#1A1A2E";
export const FS_MUTED = "#5C6378";

export const fsTheme = createTheme({
  palette: {
    primary: { main: FS_NAVY, dark: "#000010", light: FS_NAVY_SOFT, contrastText: "#FFFFFF" },
    secondary: { main: FS_SKY, light: FS_SKY_LIGHT, contrastText: "#FFFFFF" },
    background: { default: FS_SURFACE, paper: "#FFFFFF" },
    text: { primary: FS_TEXT, secondary: FS_MUTED },
    divider: FS_BORDER,
  },
  typography: {
    fontFamily: "'Inter', 'Helvetica Neue', Arial, sans-serif",
    h1: { fontSize: 28, fontWeight: 700, letterSpacing: "-0.02em", color: FS_NAVY },
    h2: { fontSize: 20, fontWeight: 700, letterSpacing: "-0.01em", color: FS_NAVY },
    h3: { fontSize: 16, fontWeight: 600, color: FS_NAVY },
    subtitle1: { fontSize: 14, fontWeight: 600, color: FS_NAVY },
    body1: { fontSize: 14.5, lineHeight: 1.6, color: FS_TEXT },
    body2: { fontSize: 13, lineHeight: 1.55, color: FS_MUTED },
    caption: { fontSize: 11.5, color: FS_MUTED, letterSpacing: "0.03em" },
    overline: { fontSize: 11, fontWeight: 700, letterSpacing: "0.12em", color: FS_MUTED },
  },
  shape: { borderRadius: 10 },
  shadows: [
    "none",
    "0 1px 2px rgba(0,0,34,0.04)",
    "0 1px 3px rgba(0,0,34,0.06), 0 1px 2px rgba(0,0,34,0.04)",
    "0 4px 12px rgba(0,0,34,0.06), 0 2px 4px rgba(0,0,34,0.04)",
    "0 8px 24px rgba(0,0,34,0.08), 0 3px 8px rgba(0,0,34,0.05)",
    ...Array(20).fill("0 12px 32px rgba(0,0,34,0.1)"),
  ] as any,
  components: {
    MuiButton: {
      styleOverrides: {
        root: { textTransform: "none", fontWeight: 600, borderRadius: 8 },
        contained: { boxShadow: "none", "&:hover": { boxShadow: "0 4px 12px rgba(0,0,34,0.12)" } },
      },
    },
    MuiPaper: { styleOverrides: { root: { backgroundImage: "none" } } },
    MuiChip: { styleOverrides: { root: { fontWeight: 600 } } },
  },
});
