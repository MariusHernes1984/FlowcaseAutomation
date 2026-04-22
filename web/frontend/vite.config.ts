import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      // In prod the frontend is served from the same Container App as the
      // backend, and /api/* lives on the backend. Keep the path intact in
      // dev so code paths work identically.
      "/api": {
        target: "http://localhost:8001",
        changeOrigin: true,
      },
    },
  },
});
