import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  base: './', // ✅ CLAVE PARA PRODUCCIÓN EN ELECTRON
  root: ".",
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  build: {
    outDir: "dist",
    rollupOptions: {
      input: "public/index.html"
    }
  },
  server: {
    port: 5173,
    strictPort: true
  }
});
