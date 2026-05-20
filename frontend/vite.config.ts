import { defineConfig } from 'vite'
import { resolve } from 'node:path'

export default defineConfig({
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        betaDashboard: resolve(__dirname, 'beta-dashboard.html'),
        sensorDashboard: resolve(__dirname, 'sensor-dashboard.html'),
        sttTest: resolve(__dirname, 'stt-test.html'),
      },
    },
  },
  server: {
    proxy: {
      '/agent': {
        target: 'http://localhost:9003',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/agent/, ''),
      },
      '/api': {
        target: 'http://localhost:9000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      '/voice': {
        target: 'http://localhost:9002',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/voice/, ''),
      },
      '/llm': {
        target: 'http://localhost:8104',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/llm/, ''),
      },
    },
  },
})
