/** Manual T17 experiment server; not a browser test runner or shipped example. */
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';

const root = fileURLToPath(new URL('.', import.meta.url));
const workspace = fileURLToPath(new URL('../../../', import.meta.url));
const requests = [];
const servers = [];
for (const port of [5273, 5274, 5275]) {
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
            if (url.pathname === '/redirect') {
              res.writeHead(302, {
                Location: `http://127.0.0.1:5275/foreign.html?run=${url.searchParams.get('run')}`,
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
console.log('T17 manual lab: http://127.0.0.1:5273/host.html');
console.log('CSP comparison: http://127.0.0.1:5273/host-csp.html');
process.on('SIGINT', async () => {
  await Promise.all(servers.map((server) => server.close()));
  process.exit(0);
});
