// Tema brand Aegis: primer indigo + radius lembut + heading tegas.
// Warna semantik keputusan dipusatkan di lib/decision.ts (teal=allow, red=block, amber=warning).
// Polish 2026-06-13: autoContrast + default komponen seragam (Card/Paper berbingkai,
// radius konsisten) tanpa mengubah primer/font (terkunci ADR-013 / TRD §2).
import { Card, Paper, createTheme } from "@mantine/core";

export const theme = createTheme({
  primaryColor: "indigo",
  defaultRadius: "md",
  autoContrast: true,
  fontFamily:
    "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
  headings: { fontWeight: "700" },
  cursorType: "pointer",
  defaultGradient: { from: "indigo", to: "violet", deg: 135 },
  components: {
    Card: Card.extend({ defaultProps: { withBorder: true, radius: "md", shadow: "xs" } }),
    Paper: Paper.extend({ defaultProps: { radius: "md" } }),
  },
});
