import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Proxy removed since we're using production API directly
    // The API service is configured to use https://dosapi.attendance.dishaonliesolution.workspa.in/api
  }
})
