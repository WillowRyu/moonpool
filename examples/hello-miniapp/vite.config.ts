import { defineConfig } from 'vite';

/**
 * SPEC §8.1 — this mini app's development origin. Pinned, and distinct from
 * the host's (5173), so the §9.1 origin check is exercised for real rather
 * than passing vacuously against a same-origin Portal.
 */
export default defineConfig({
  server: { port: 5174, strictPort: true },
});
