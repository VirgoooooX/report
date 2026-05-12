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
          if (id.includes('node_modules/@ant-design/icons-vue')) return 'antd-icons'
          if (id.includes('node_modules/ant-design-vue/es/table')) return 'antd-table'
          if (id.includes('node_modules/ant-design-vue/es/select')) return 'antd-select'
          if (id.includes('node_modules/ant-design-vue/es/modal')) return 'antd-modal'
          if (id.includes('node_modules/ant-design-vue/es/radio')) return 'antd-radio'
          if (
            id.includes('node_modules/ant-design-vue/es/card') ||
            id.includes('node_modules/ant-design-vue/es/grid') ||
            id.includes('node_modules/ant-design-vue/es/row') ||
            id.includes('node_modules/ant-design-vue/es/col') ||
            id.includes('node_modules/ant-design-vue/es/spin')
          ) {
            return 'antd-layout'
          }
          if (id.includes('node_modules/ant-design-vue/es/vc-')) return 'antd-vc'
          if (id.includes('node_modules/@rc-component') || id.includes('node_modules/rc-')) return 'antd-rc'
          if (
            id.includes('node_modules/ant-design-vue/es/_util') ||
            id.includes('node_modules/ant-design-vue/es/style') ||
            id.includes('node_modules/ant-design-vue/es/theme') ||
            id.includes('node_modules/ant-design-vue/es/config-provider')
          ) {
            return 'antd-core'
          }
          if (id.includes('node_modules/ant-design-vue')) return 'antd-core'
          return undefined
        }
      }
    }
  }
})
