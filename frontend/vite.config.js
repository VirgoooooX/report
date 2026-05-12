import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath } from 'url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:5050'
    }
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    chunkSizeWarningLimit: 500,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/vue') || id.includes('node_modules/vue-router') || id.includes('node_modules/pinia')) {
            return 'vue'
          }
          if (id.includes('node_modules/chart.js') || id.includes('node_modules/vue-chartjs') || id.includes('node_modules/chartjs-plugin-datalabels')) {
            return 'charts'
          }
          if (id.includes('node_modules/@ant-design/icons-vue') || id.includes('node_modules/ant-design-vue')) {
            return 'antd'
          }
          if (id.includes('node_modules/@rc-component') || id.includes('node_modules/rc-')) {
            return 'antd'
          }
          return undefined
        }
      }
    }
  }
})
