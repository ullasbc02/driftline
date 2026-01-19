import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  // Point Vite to the dashboard folder as the project root
  root: __dirname,
  plugins: [react()],
  server: { port: 5173 },
});