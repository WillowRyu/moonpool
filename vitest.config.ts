import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vitest/config';

// Aliases point at package sources so tests run without a build step.
export default defineConfig({
  resolve: {
    alias: {
      '@moonpool/protocol': fileURLToPath(
        new URL('./packages/protocol/src/index.ts', import.meta.url),
      ),
      '@moonpool/client': fileURLToPath(new URL('./packages/client/src/index.ts', import.meta.url)),
      '@moonpool/host': fileURLToPath(new URL('./packages/host/src/index.ts', import.meta.url)),
      '@moonpool/transport-iframe': fileURLToPath(
        new URL('./packages/transport-iframe/src/index.ts', import.meta.url),
      ),
    },
  },
  test: {
    include: ['packages/*/test/**/*.test.ts'],
  },
});
