import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import type { UserConfig } from 'vite'
import path from 'path'

export default defineConfig({
  plugins: [svelte()],
  resolve: {
    alias: {
      $lib: path.resolve('./src/lib'),
      'src': '/src',
      '@': path.resolve('./src'),
      '@components': path.resolve('./src/lib/components')
    }
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5002',
        changeOrigin: true
      },
      '/socket.io': {
        target: 'http://localhost:5002',
        ws: true,
        changeOrigin: true,
        secure: false
      },
      '/sensor_status': {
        target: 'http://localhost:5002/sensor_status',
        ws: true,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/sensor_status/, '/socket.io')
      },
      '/sensor_data': {
        target: 'http://localhost:5002/sensor_data',
        ws: true,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/sensor_data/, '/socket.io')
      }
    }
  }
} as UserConfig)
