import { defineConfig } from 'vitest/config';

// This intentionally red contract probe is separate from the current 0.1 suite.
export default defineConfig({
  test: {
    include: ['experiments/document-generation-contract/**/*.test.ts'],
  },
});
