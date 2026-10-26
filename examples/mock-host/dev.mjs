/** One host plus two app origins, all pinned. No dependency or native port added. */
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';

const servers = [];
try {
  for (const [root, port] of [
    ['.', 5173],
    ['../hello-miniapp', 5174],
    ['../hello-miniapp', 5175],
  ]) {
    const directory = fileURLToPath(new URL(`${root}/`, import.meta.url));
    const server = await createServer({
      root: directory,
      cacheDir: fileURLToPath(
        new URL(`../../node_modules/.vite-moonpool-${port}`, import.meta.url),
      ),
      server: { port, strictPort: true },
    });
    servers.push(server);
    await server.listen();
    server.printUrls();
  }
} catch (error) {
  await Promise.allSettled(servers.map((server) => server.close()));
  throw error;
}
for (const signal of ['SIGINT', 'SIGTERM']) {
  process.once(signal, async () => {
    await Promise.allSettled(servers.map((server) => server.close()));
    process.exit(0);
  });
}
