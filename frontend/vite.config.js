import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import http from 'node:http'

// Force IPv4 DNS lookup so Vite's proxy never silently falls back to ::1
// while the backend only listens on 127.0.0.1.
const ipv4Agent = new http.Agent({ family: 4 })

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
        secure: false,
        agent: ipv4Agent
      }
    }
  }
})
