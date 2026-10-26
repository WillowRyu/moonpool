/** Manual T17 experiment server; not a browser test runner or shipped example. */
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';

const root = fileURLToPath(new URL('.', import.meta.url));
const workspace = fileURLToPath(new URL('../../../', import.meta.url));
const requests = [];
const servers = [];
const multi = process.argv.includes('--multi');
const ports = multi ? [5373, 5374, 5375, 5376] : [5273, 5274, 5275];
for (const port of ports) {
  const server = await createServer({
    configFile: false,
    root,
    logLevel: 'warn',
    optimizeDeps: { noDiscovery: true, include: [] },
    server: {
      host: '127.0.0.1',
      port,
      strictPort: true,
      hmr: false,
      watch: null,
      fs: { allow: [workspace] },
    },
    plugins: [
      {
        name: 'navigation-observations',
        configureServer(instance) {
          instance.middlewares.use((req, res, next) => {
            const url = new URL(req.url ?? '/', `http://127.0.0.1:${port}`);
            if (
              ['/probe.html', '/foreign.html', '/bounce.html', '/slow.svg', '/redirect'].includes(
                url.pathname,
              )
            ) {
              requests.push({
                sequence: requests.length + 1,
                port,
                path: url.pathname,
                run: url.searchParams.get('run'),
              });
            }
            res.setHeader('Cache-Control', 'no-store');
            if (multi && port === 5373) {
              // Each served wrapper gets its own policy; srcdoc inheritance is not used.
              const frameOrigins = new Map([
                ['/multi-host.html', 'http://127.0.0.1:5373'],
                ['/multi-wrapper-a.html', 'http://127.0.0.1:5374'],
                ['/multi-wrapper-b.html', 'http://127.0.0.1:5375'],
              ]);
              const origin = frameOrigins.get(url.pathname);
              if (origin !== undefined) {
                res.setHeader('Content-Security-Policy', `frame-src ${origin}`);
              }
            }
            if (url.pathname === '/redirect') {
              res.writeHead(302, {
                Location: `http://127.0.0.1:${multi ? 5376 : 5275}/foreign.html?run=${url.searchParams.get('run')}`,
              });
              res.end();
              return;
            }
            if (url.pathname === '/observations') {
              res.setHeader('Content-Type', 'application/json');
              res.end(
                JSON.stringify(
                  requests.filter((entry) => entry.run === url.searchParams.get('run')),
                ),
              );
              return;
            }
            if (url.pathname === '/slow.svg') {
              res.setHeader('Content-Type', 'image/svg+xml');
              setTimeout(() => {
                if (!res.destroyed) {
                  res.end('<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>');
                }
              }, 5000);
              return;
            }
            next();
          });
        },
      },
    ],
  });
  await server.listen();
  servers.push(server);
}
if (multi) {
  console.log('Multi-Portal follow-up: http://127.0.0.1:5373/multi-host.html');
} else {
  console.log('T17 manual lab: http://127.0.0.1:5273/host.html');
  console.log('CSP comparison: http://127.0.0.1:5273/host-csp.html');
}
process.on('SIGINT', async () => {
  await Promise.all(servers.map((server) => server.close()));
  process.exit(0);
});
