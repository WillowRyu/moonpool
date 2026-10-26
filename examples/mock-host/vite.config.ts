import { fileURLToPath } from 'node:url';
import { defineConfig, type Plugin } from 'vite';
import { browserPolicy } from './src/browser-policy';

/** Apply the same enforcing policy to development and built-preview responses. */
const containment: Plugin = {
  name: 'moonpool-browser-containment',
  configureServer(server) {
    server.middlewares.use((req, res, next) => {
      const policy = browserPolicy(req.url ?? '/');
      if (policy !== undefined) {
        res.setHeader('Content-Security-Policy', policy);
      }
      next();
    });
  },
  configurePreviewServer(server) {
    server.middlewares.use((req, res, next) => {
      const policy = browserPolicy(req.url ?? '/');
      if (policy !== undefined) {
        res.setHeader('Content-Security-Policy', policy);
      }
      next();
    });
  },
};

/**
 * SPEC §8.1 — the host page and every Portal MUST be served from distinct
 * origins, so each gets its own pinned port. `strictPort` is the point of
 * this file: Vite's default is to hop to the next free port, and an origin
 * that drifts silently re-keys everything the browser stores under it.
 */
export default defineConfig({
  plugins: [containment],
  server: { port: 5173, strictPort: true },
  preview: { port: 5173, strictPort: true },
  build: {
    rolldownOptions: {
      input: {
        host: fileURLToPath(new URL('index.html', import.meta.url)),
        wrapper: fileURLToPath(new URL('portal-wrapper.html', import.meta.url)),
        checks: fileURLToPath(new URL('containment-check.html', import.meta.url)),
      },
    },
  },
});
