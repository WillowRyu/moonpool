import { fileURLToPath } from 'node:url';

export default {
  build: {
    target: 'es2022',
    outDir: fileURLToPath(new URL('./build', import.meta.url)),
    emptyOutDir: true,
    minify: false,
    sourcemap: false,
    lib: {
      entry: fileURLToPath(new URL('./kernel-probe.ts', import.meta.url)),
      name: 'MoonpoolRuntimeProbe',
      formats: ['iife'],
      fileName: () => 'kernel-probe.js',
    },
  },
};
