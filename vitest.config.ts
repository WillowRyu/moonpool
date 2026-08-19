import { defineConfig } from 'vitest/config';

// No aliases needed: `@moonpool/*` imports resolve through npm workspaces —
// each package's `exports` points at its TypeScript source, so tests run
// without a build step.
export default defineConfig({
  test: {
    include: ['packages/*/test/**/*.test.ts'],
  },
});
