import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          // Vendor chunks for better caching
          if (id.includes('node_modules')) {
            if (id.includes('react') || id.includes('react-dom') || id.includes('react-router')) {
              return 'react-vendor';
            }
            // Keep HTTP + charts separated to reduce the main vendor chunk
            if (id.includes('axios')) {
              return 'http-vendor';
            }
            if (id.includes('chart.js') || id.includes('react-chartjs-2')) {
              return 'chart-vendor';
            }
            if (id.includes('lucide-react')) {
              return 'ui-vendor';
            }
            if (id.includes('date-fns')) {
              return 'date-vendor';
            }
            if (id.includes('jspdf') || id.includes('html2canvas')) {
              return 'pdf-vendor';
            }
            if (id.includes('sonner') || id.includes('react-toastify')) {
              return 'notification-vendor';
            }
            // Group other large dependencies
            return 'vendor';
          }
          
          // Split large components into separate chunks
          if (id.includes('src/components/DocumentGenerator')) {
            return 'document-generator';
          }
          if (id.includes('src/components/salary')) {
            return 'salary-components';
          }
          if (id.includes('src/components/attendance')) {
            return 'attendance-components';
          }
          if (id.includes('src/components/Reports')) {
            return 'reports-components';
          }
        }
      }
    },
    // Keep warnings meaningful, but don't warn for PDF libs that are intentionally lazy-loaded
    chunkSizeWarningLimit: 650,
    target: 'es2015',
    minify: 'esbuild',
    sourcemap: false, // Disable sourcemaps for production
    cssCodeSplit: true, // Split CSS into separate files
  },
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      'lucide-react',
      'date-fns',
      'sonner',
      'react-toastify'
    ],
    exclude: ['@vite/client', '@vite/env']
  },
  server: {
    hmr: {
      overlay: false // Disable error overlay for better performance
    }
  }
})
