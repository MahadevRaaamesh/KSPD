import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    // maplibre-gl spawns its tile-parsing web worker from a URL relative to
    // its own module. Pre-bundling it into .vite/deps breaks that URL and the
    // worker 404s, leaving a blank map canvas. Serve it unbundled in dev.
    exclude: ['maplibre-gl'],
  },
})
