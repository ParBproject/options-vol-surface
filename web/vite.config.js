import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Served from https://parbproject.github.io/options-vol-surface/
export default defineConfig({
  base: "/options-vol-surface/",
  plugins: [react()],
  build: { target: "es2022", outDir: "dist", emptyOutDir: true },
});
