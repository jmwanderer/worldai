import { defineConfig } from 'vite'
import { resolve } from 'path'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  base: '',
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:5000',
      '/images': 'http://127.0.0.1:5000',
      '/static': 'http://127.0.0.1:5000',	    
    }
  },
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        play: resolve(__dirname, 'play.html'),
        design: resolve(__dirname, 'design.html'),
      }
    }
  }
})
