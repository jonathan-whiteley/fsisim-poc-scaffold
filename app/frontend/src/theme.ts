import { createTheme, type Theme } from "@mui/material/styles";

// FlightSafety brand tokens. Used as accents in both light and dark modes.
export const FS_NAVY = "#000022";
export const FS_NAVY_SOFT = "#0F1535";
export const FS_SKY = "#2A6FB5";
export const FS_SKY_LIGHT = "#E8F1FB";
export const FS_SKY_LIGHT_DARK = "#1F3955"; // sky-light tinted for dark mode chips
export const FS_INK = "#1A1A2E";

// Light-mode neutrals (current behavior).
export const FS_BORDER = "#E5E7EB";
export const FS_SURFACE = "#FAFBFD";
export const FS_TEXT = "#1A1A2E";
export const FS_MUTED = "#5C6378";

// Dark-mode neutrals.
export const FS_BORDER_DARK = "#2A2A45";
export const FS_SURFACE_DARK = "#0B0B1C";
export const FS_PAPER_DARK = "#14142B";
export const FS_TEXT_DARK = "#E5E7EB";
export const FS_MUTED_DARK = "#94A3B8";

export type ColorMode = "light" | "dark";

export function makeFsTheme(mode: ColorMode): Theme {
  const isDark = mode === "dark";
  return createTheme({
    palette: {
      mode,
      primary: { main: FS_NAVY, dark: "#000010", light: FS_NAVY_SOFT, contrastText: "#FFFFFF" },
      secondary: { main: FS_SKY, light: FS_SKY_LIGHT, contrastText: "#FFFFFF" },
      background: {
        default: isDark ? FS_SURFACE_DARK : FS_SURFACE,
        paper: isDark ? FS_PAPER_DARK : "#FFFFFF",
      },
      text: {
        primary: isDark ? FS_TEXT_DARK : FS_TEXT,
        secondary: isDark ? FS_MUTED_DARK : FS_MUTED,
      },
      divider: isDark ? FS_BORDER_DARK : FS_BORDER,
    },
    typography: {
      fontFamily: "'Inter', 'Helvetica Neue', Arial, sans-serif",
      h1: { fontSize: 28, fontWeight: 700, letterSpacing: "-0.02em" },
      h2: { fontSize: 20, fontWeight: 700, letterSpacing: "-0.01em" },
      h3: { fontSize: 16, fontWeight: 600 },
      subtitle1: { fontSize: 14, fontWeight: 600 },
      body1: { fontSize: 14.5, lineHeight: 1.6 },
      body2: { fontSize: 13, lineHeight: 1.55 },
      caption: { fontSize: 11.5, letterSpacing: "0.03em" },
      overline: { fontSize: 11, fontWeight: 700, letterSpacing: "0.12em" },
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
}

// Backward-compat: legacy modules import `fsTheme`. Default to light.
export const fsTheme = makeFsTheme("light");
