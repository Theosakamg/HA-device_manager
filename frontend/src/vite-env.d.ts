/// <reference types="vite/client" />

// Allow importing Markdown files as raw strings via `?raw` Vite suffix.
declare module "*.md?raw" {
  const content: string;
  export default content;
}

// Allow importing raw CSS files as Lit CSSResult objects via the `?lit` suffix.
// Handled by the litCssPlugin in vite.config.ts.
declare module "*.css?lit" {
  import { CSSResult } from "lit";
  const styles: CSSResult;
  export default styles;
}
