import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// In dev, proxy /api to the FastAPI server so the app uses the same relative URLs as production.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { '/api': process.env.VITE_PROXY_TARGET || 'http://localhost:8000' } },
});
