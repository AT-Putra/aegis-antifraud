import { defineConfig } from "vite";

// Bundel statis portabel (T-10). Dev-server proxy /v1 → API Aegis lokal.
export default defineConfig({
  base: "./", // path-relative → bundel bisa di-host di subdir/origin mana pun
  build: { outDir: "dist", emptyOutDir: true },
  server: {
    proxy: {
      "/v1": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["tests/setup.ts"],
  },
});
