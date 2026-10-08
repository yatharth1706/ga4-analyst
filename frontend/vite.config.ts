import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    // In development the FastAPI backend runs separately; in production both share one origin.
    proxy: { '/api': 'http://localhost:8000' },
  },
})
