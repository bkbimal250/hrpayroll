import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react({
      // Enable React Fast Refresh for better development experience
      fastRefresh: true,
      // Optimize JSX runtime
      jsxRuntime: 'automatic'
    })
  ],
  // Set base path for production deployment
  base: './',
  build: {
    // Optimize bundle size
    rollupOptions: {
      output: {
        manualChunks: {
          // Core React libraries
          vendor: ['react', 'react-dom', 'react-router-dom'],
          // UI components and icons
          ui: ['lucide-react', 'react-hot-toast'],
          // Utility libraries
          utils: ['axios'],
          // Separate chunk for each major page
          dashboard: ['./src/pages/Dashboard.jsx'],
          attendance: ['./src/pages/Attendance.jsx'],
          profile: ['./src/pages/Profile.jsx'],
          leaves: ['./src/pages/Leaves.jsx'],
          documents: ['./src/pages/Documents.jsx'],
          resignations: ['./src/pages/Resignations.jsx']
        },
        // Ensure assets are placed in the assets directory
        assetFileNames: 'assets/[name]-[hash][extname]',
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js'
      }
    },
    // Enable compression
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true,
        pure_funcs: ['console.log', 'console.info', 'console.debug', 'console.warn'],
        // Additional optimizations
        passes: 2,
        unsafe: true,
        unsafe_comps: true,
        unsafe_math: true
      },
      mangle: {
        // Mangle class names for smaller bundle
        keep_classnames: false,
        keep_fnames: false
      }
    },
    // Optimize chunk size
    chunkSizeWarningLimit: 1000,
    // Disable source maps for production
    sourcemap: false,
    // Enable CSS code splitting
    cssCodeSplit: true,
    // Target modern browsers for better optimization
    target: 'esnext',
    // Enable tree shaking
    treeshake: true
  },
  // Optimize dependencies
  optimizeDeps: {
    include: [
      'react', 
      'react-dom', 
      'react-router-dom',
      'lucide-react', 
      'react-hot-toast', 
      'axios'
    ],
    force: true,
    // Exclude from pre-bundling
    exclude: []
  },
  // Enable gzip compression
  server: {
    compress: true,
    // Enable HMR for faster development
    hmr: {
      overlay: false
    }
  },
  // CSS optimization
  css: {
    devSourcemap: false
  },
  // Performance optimizations
  esbuild: {
    // Enable tree shaking
    treeShaking: true,
    // Target modern browsers
    target: 'esnext',
    // Enable minification
    minify: true
  },
  // Define environment variables for optimization
  define: {
    'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV || 'production')
  }
})
