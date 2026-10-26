import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';

/**
 * SPEC §8.1 — this mini app's development origin. Pinned, and distinct from
 * the host's (5173), so the §9.1 origin check is exercised for real rather
 * than passing vacuously against a same-origin Portal.
 */
export default defineConfig({
  plugins: [
    {
      name: 'moonpool-manual-navigation-redirect',
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          if (req.url === '/navigation-redirect') {
            res.writeHead(302, { Location: 'http://127.0.0.1:5174/navigation-foreign.html' });
            res.end();
            return;
          }
          next();
        });
      },
    },
  ],
  server: { port: 5174, strictPort: true },
  preview: { port: 5174, strictPort: true },
  build: {
    rolldownOptions: {
      input: {
        app: fileURLToPath(new URL('index.html', import.meta.url)),
        probe: fileURLToPath(new URL('containment-probe.html', import.meta.url)),
        foreign: fileURLToPath(new URL('navigation-foreign.html', import.meta.url)),
        bounce: fileURLToPath(new URL('navigation-bounce.html', import.meta.url)),
      },
    },
  },
});
