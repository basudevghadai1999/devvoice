import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/ws': { target: 'ws://localhost:8000', ws: true },
      '/voice': { target: 'http://localhost:8000' },
      '/status': { target: 'http://localhost:8000' },
      '/api': { target: 'http://localhost:8000' },
    }
  }
})
