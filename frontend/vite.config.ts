import { defineConfig, Plugin } from 'vite';
import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';

/**
 * Vite plugin: import raw CSS files as Lit CSSResult objects.
 *
 * Usage in components:
 *   import myStyles from './my-component-styles.css?lit';
 *
 * The plugin intercepts any import ending with `?lit`, reads the raw CSS file,
 * and returns an ES module that exports a Lit `CSSResult` as the default export.
 * This keeps CSS in plain `.css` files while embedding them efficiently at build time.
 *
 * Using a `\0` virtual module prefix and `enforce: 'pre'` prevents Vite's built-in
 * CSS pipeline from interfering with these imports.
 */
function litCssPlugin(): Plugin {
  const VIRTUAL_PREFIX = '\0lit-css:';
  const SUFFIX = '?lit';
  return {
    name: 'vite-plugin-lit-css',
    enforce: 'pre',
    resolveId(source, importer) {
      if (source.endsWith(SUFFIX)) {
        const [path] = source.split('?');
        const base = importer ? dirname(importer.split('?')[0]) : process.cwd();
        // Append '.js' so the virtual ID does NOT end with '.css':
        // Vite's built-in CSS pipeline would otherwise intercept the module
        // after our load hook runs and strip the `export default`.
        return `${VIRTUAL_PREFIX}${resolve(base, path)}.js`;
      }
    },
    load(id) {
      if (!id.startsWith(VIRTUAL_PREFIX)) return null;
      // Strip prefix and the '.js' suffix we added above
      const cssPath = id.slice(VIRTUAL_PREFIX.length, -3);
      // JSON.stringify handles all escaping — bulletproof for any CSS content.
      const escaped = JSON.stringify(readFileSync(cssPath, 'utf-8'));
      return `import { unsafeCSS } from 'lit';\nexport default unsafeCSS(${escaped});\n`;
    },
  };
}

export default defineConfig({
  plugins: [litCssPlugin()],
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
