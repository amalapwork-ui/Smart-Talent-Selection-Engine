import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],

  // Resolve .jsx before .js so JSX-containing files are found correctly
  resolve: {
    extensions: [".mjs", ".jsx", ".js", ".ts", ".tsx", ".json"],
  },

  // Dev server config
  server: {
    port: 3000,
    open: true,
    // Proxy all /api requests to the Django backend — avoids CORS in development
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        secure: false,
      },
      "/media": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        secure: false,
      },
    },
  },

  // Production preview server
  preview: {
    port: 3000,
  },

  // Build output
  build: {
    outDir: "dist",
    sourcemap: false,
    rollupOptions: {
      output: {
        // Separate vendor chunk for better caching
        manualChunks: {
          vendor: ["react", "react-dom", "react-router-dom"],
          charts: ["recharts"],
          http: ["axios"],
        },
      },
    },
  },

  // CSS — PostCSS (Tailwind) is picked up automatically from postcss.config.js
  css: {
    devSourcemap: true,
  },
});
