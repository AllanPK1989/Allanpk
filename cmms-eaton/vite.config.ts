import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

// The app is a static bundle: deploy the `dist/` folder at the root of any static
// host (AweShell gives every upload its own domain, so "/" is the right base).
export default defineConfig({
  base: "/",
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      injectRegister: "script-defer", // external script, so the CSP can stay without 'unsafe-inline' for scripts
      includeAssets: ["icon.svg"],
      manifest: {
        name: "CMMS_Eaton",
        short_name: "CMMS_Eaton",
        description: "Maintenance management: work orders, preventive maintenance, assets and spare parts",
        theme_color: "#0f2847",
        background_color: "#f4f6f9",
        display: "standalone",
        start_url: "/",
        scope: "/",
        icons: [
          { src: "icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "icon-512.png", sizes: "512x512", type: "image/png" },
          { src: "icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
      },
      workbox: {
        navigateFallback: "/index.html",
        globPatterns: ["**/*.{js,css,html,svg,png,woff2}"],
        maximumFileSizeToCacheInBytes: 4 * 1024 * 1024,
      },
    }),
  ],
  server: { port: 5173 },
  preview: { port: 4173 },
});
