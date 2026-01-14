import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    // 允许手机/局域网设备访问 Vite dev server
    host: true,
    port: 5173,
    proxy: {
      '/api': {
        // 后端开发端口按仓库约定是 8000
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist'
  }
})
