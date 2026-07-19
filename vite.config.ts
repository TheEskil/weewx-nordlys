import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

// Built assets ship inside the weewx skin and are referenced from Cheetah
// templates, so filenames must be stable (no content hashes). Cache busting
// is handled with a ?v=<skin version> query in the templates.
export default defineConfig({
  plugins: [svelte()],
  build: {
    outDir: 'skins/Nordlys/dist',
    emptyOutDir: true,
    lib: undefined,
    rollupOptions: {
      input: 'src/main.ts',
      output: {
        entryFileNames: 'nordlys.js',
        chunkFileNames: 'nordlys.[name].js',
        assetFileNames: (info) =>
          info.names?.[0]?.endsWith('.css') ? 'nordlys.css' : 'assets/[name][extname]',
      },
    },
  },
})
