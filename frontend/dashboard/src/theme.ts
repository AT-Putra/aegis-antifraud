// Tema brand Aegis: primer indigo + radius lembut + heading tegas.
// Warna semantik keputusan dipusatkan di lib/decision.ts (teal=allow, red=block, amber=warning).
import { createTheme } from "@mantine/core";

export const theme = createTheme({
  primaryColor: "indigo",
  defaultRadius: "md",
  fontFamily:
    "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
  headings: { fontWeight: "700" },
  cursorType: "pointer",
});
