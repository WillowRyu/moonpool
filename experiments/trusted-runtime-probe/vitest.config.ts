import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: { include: ['experiments/trusted-runtime-probe/**/*.test.mjs'] },
});
