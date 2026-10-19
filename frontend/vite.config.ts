import { defineConfig, loadEnv } from 'vite'
import { resolve } from 'node:path'

export default defineConfig(({ mode }) => {
  const demo = loadEnv(mode, process.cwd(), '').VITE_DEMO_MODE === 'true';
  return {
  base: demo ? './' : '/',
  publicDir: demo ? false : 'public',
  plugins: demo ? [{
    name: 'isolated-sample-entry',
    transformIndexHtml: {
      order: 'pre' as const,
      handler: (html: string) => html
        .replace('/src/main.tsx', '/src/demo/main.tsx')
        .replace('</head>', '<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 32 32%22%3E%3Ccircle cx=%2216%22 cy=%2216%22 r=%2214%22 fill=%22%23006b5f%22/%3E%3C/svg%3E" /></head>')
        .replace('<title>Super Marimo</title>', '<title>Super Marimo · 샘플 체험</title><meta name="description" content="공개 문서와 테스트의 고정 예시로 살펴보는 Super Marimo 체험 모드" />'),
    },
  }] : [],
  build: {
    outDir: demo ? 'dist-demo' : 'dist',
    rollupOptions: {
      input: demo ? resolve(__dirname, 'index.html') : {
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
        target: 'http://localhost:8003',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/agent/, ''),
      },
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      '/voice': {
        target: 'http://localhost:8002',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/voice/, ''),
      },
      '/llm': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/llm/, ''),
      },
    },
  },
  };
})
