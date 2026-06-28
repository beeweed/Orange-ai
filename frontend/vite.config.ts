import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Vite configuration.
// `host: true` + `allowedHosts: true` allow access via any tunnel/sandbox host.
// `cors: true` enables CORS on the dev server.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 3000,
    strictPort: true,
    allowedHosts: true,
    cors: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  preview: {
    host: true,
    port: 3000,
    strictPort: true,
    allowedHosts: true,
    cors: true,
  },
})
