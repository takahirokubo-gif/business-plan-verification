import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // コベナンツ・モニタリング（8000）と共存できるよう、本プロジェクトのAPIは8010
    proxy: {
      '/api': 'http://localhost:8010',
    },
  },
})
