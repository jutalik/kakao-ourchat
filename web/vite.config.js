import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

export default defineConfig({
  plugins: [svelte()],
  base: './',
  build: {
    target: 'es2020', outDir: 'dist',
    rollupOptions: {
      // stable filenames (no content hash) so an already-open tab never points
      // at a deleted bundle across iterative rebuilds — a plain refresh always works
      output: {
        entryFileNames: 'assets/app.js',
        chunkFileNames: 'assets/[name].js',
        assetFileNames: 'assets/app.[ext]',
      },
    },
  },
})
