import { defineConfig } from "vite";
import { resolve } from "node:path";

// Separate build from vite.config.ts: MV3 content scripts must be a single
// file at a fixed path (manifest.json references "content.js"), so this
// runs as a second `vite build` pass into the same dist/ without emptying
// it (the popup build already did that).
export default defineConfig({
  build: {
    outDir: "dist",
    emptyOutDir: false,
    lib: {
      entry: resolve(__dirname, "src/content/content.ts"),
      name: "ContextPackerContentScript",
      formats: ["iife"],
      fileName: () => "content.js",
    },
  },
});
