import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import fs from 'fs';
import path from 'path';

let serverPort = 3000;
const portFile = path.resolve(__dirname, '..', '.port');
if (fs.existsSync(portFile)) {
  serverPort = parseInt(fs.readFileSync(portFile, 'utf-8').trim(), 10) || 3000;
} else if (process.env.VITE_SERVER_PORT) {
  serverPort = parseInt(process.env.VITE_SERVER_PORT, 10) || 3000;
}

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/socket.io': {
        target: `http://localhost:${serverPort}`,
        ws: true,
      },
    },
  },
});
