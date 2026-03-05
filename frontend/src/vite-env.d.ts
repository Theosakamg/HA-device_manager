/// <reference types="vite/client" />

// Allow importing Markdown files as raw strings via `?raw` Vite suffix.
declare module "*.md?raw" {
  const content: string;
  export default content;
}
