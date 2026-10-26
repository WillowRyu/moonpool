/** SPEC §8.1 — host-owned stable mapping, also used by response CSP selection. */
export const HOST_ORIGIN = 'http://localhost:5173';
export const MINI_APP_ORIGINS = new Map([
  ['com.example.hello', 'http://localhost:5174'],
  ['com.example.second', 'http://localhost:5175'],
]);
