import { defineConfig } from 'vite';

/**
 * SPEC §8.1 — the host page and every Portal MUST be served from distinct
 * origins, so each gets its own pinned port. `strictPort` is the point of
 * this file: Vite's default is to hop to the next free port, and an origin
 * that drifts silently re-keys everything the browser stores under it.
 */
export default defineConfig({
  server: { port: 5173, strictPort: true },
});
