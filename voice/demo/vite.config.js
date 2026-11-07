// Test page for the voice components in frontend/src/voice, without needing P4's app.
import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const repoRoot = path.resolve(__dirname, "../..");

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@voice": path.join(repoRoot, "frontend/src/voice") },
    dedupe: ["react", "react-dom"], // components live outside this folder; use this folder's React
  },
  server: { port: 5173, fs: { allow: [repoRoot] } },
});
