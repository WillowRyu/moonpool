/**
 * hello-miniapp — the smallest thing that proves a mini app can run.
 *
 * Speaks to its host over the iframe transport: opens the bridge to
 * `window.parent`, performs the SPEC §5 handshake — which the mini app always
 * initiates — then reads and displays the host's public profile (§6.3).
 */

import { createClient, MoonpoolError } from '@moonpool/client';
import { PROFILE_METHODS, PROTOCOL_VERSION } from '@moonpool/protocol';
import { createIframeTransport } from '@moonpool/transport-iframe';
import { createStorageDemo } from './storage-demo';

/** SPEC §8.1 — pinned, never derived from the environment. */
const HOST_ORIGIN = 'http://localhost:5173';

const root = document.querySelector<HTMLElement>('#app');
if (root === null) {
  throw new Error('hello-miniapp: #app is missing from index.html');
}

root.innerHTML = `
  <h1>Hello mini app</h1>
  <dl>
    <dt>origin</dt><dd><code>${window.location.origin}</code></dd>
    <dt>protocol</dt><dd><code>${PROTOCOL_VERSION}</code></dd>
    <dt>bridge</dt><dd id="bridge">connecting...</dd>
    <dt>profile</dt><dd id="profile" aria-live="polite">waiting for handshake...</dd>
  </dl>
  <section id="storage" aria-label="Storage demo"></section>
`;

const bridge = root.querySelector<HTMLElement>('#bridge');
if (bridge === null) {
  throw new Error('hello-miniapp: #bridge is missing from the rendered markup');
}

const profile = root.querySelector<HTMLElement>('#profile');
if (profile === null) {
  throw new Error('hello-miniapp: #profile is missing from the rendered markup');
}

const storageRoot = root.querySelector<HTMLElement>('#storage');
if (storageRoot === null) {
  throw new Error('hello-miniapp: #storage is missing from the rendered markup');
}

/** Preserve bridge error codes so the example explains why a call failed. */
function describeError(error: unknown): string {
  return error instanceof MoonpoolError ? `${error.code} - ${error.message}` : String(error);
}

// A Portal opened directly in a tab is its own parent. Say so, rather than
// posting into our own window and waiting out the §4.5 timeout in silence.
if (window.parent === window) {
  bridge.textContent = `not embedded — open the mock host at ${HOST_ORIGIN}`;
  profile.textContent = 'not requested: not embedded';
  throw new Error('hello-miniapp: not running inside a host Portal');
}

const client = createClient({
  transport: createIframeTransport({
    peerWindow: window.parent,
    peerOrigin: HOST_ORIGIN,
  }),
});
const storageDemo = createStorageDemo(storageRoot, client);

try {
  // SPEC §5 — the mini app initiates, and this MUST be the first request.
  const result = await client.initialize();
  // Treat returned strings as text; they must not become executable markup.
  bridge.textContent = `connected to ${result.host.name} · granted ${result.grantedScopes.join(', ') || '(nothing)'}`;
  storageDemo.ready(result.grantedScopes);

  profile.textContent = 'loading...';
  try {
    // SPEC §6.3 — ask only after initialization. The host enforces the scope.
    const profileResult = await client.call(PROFILE_METHODS.GET);
    // Check the field this view consumes before rendering; call() returns unknown.
    // Reject invalid data instead of coercing it or asserting a result type.
    if (
      typeof profileResult !== 'object' ||
      profileResult === null ||
      Array.isArray(profileResult) ||
      !('displayName' in profileResult) ||
      typeof profileResult.displayName !== 'string'
    ) {
      throw new Error('profile.get returned an invalid displayName');
    }

    profile.textContent = profileResult.displayName;
  } catch (error) {
    // A capability failure does not undo a successful handshake.
    profile.textContent = `profile.get failed: ${describeError(error)}`;
  }
} catch (error) {
  bridge.textContent = `handshake failed: ${describeError(error)}`;
  profile.textContent = 'not requested: handshake failed';
  storageDemo.unavailable('not requested: handshake failed');
}
