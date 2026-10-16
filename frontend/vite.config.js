import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Backend chay o :8000. Goi /api/... tu frontend se duoc chuyen tiep, khong vuong CORS.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": "http://localhost:8000" } },
});
