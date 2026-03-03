import { defineConfig } from 'vite';

export default defineConfig({
  build: {
    lib: {
      entry: 'src/components/app-shell.ts',
      formats: ['es'],
      fileName: () => 'device-manager.js',
    },
    outDir: 'dist',
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
      },
    },
    minify: 'terser',
    sourcemap: false,
  },
});
