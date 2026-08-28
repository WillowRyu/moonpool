/**
 * hello-miniapp — the smallest thing that proves a mini app can run.
 *
 * Speaks to its host over the iframe transport: opens the bridge to
 * `window.parent`, performs the SPEC §5 handshake — which the mini app always
 * initiates — and renders what the host granted it.
 */

import { createClient, MoonpoolError } from '@moonpool/client';
import { PROTOCOL_VERSION } from '@moonpool/protocol';
import { createIframeTransport } from '@moonpool/transport-iframe';

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
  </dl>
`;

const bridge = root.querySelector<HTMLElement>('#bridge');
if (bridge === null) {
  throw new Error('hello-miniapp: #bridge is missing from the rendered markup');
}

// A Portal opened directly in a tab is its own parent. Say so, rather than
// posting into our own window and waiting out the §4.5 timeout in silence.
if (window.parent === window) {
  bridge.textContent = `not embedded — open the mock host at ${HOST_ORIGIN}`;
  throw new Error('hello-miniapp: not running inside a host Portal');
}

const client = createClient({
  transport: createIframeTransport({
    peerWindow: window.parent,
    peerOrigin: HOST_ORIGIN,
  }),
});

try {
  // SPEC §5 — the mini app initiates, and this MUST be the first request.
  const result = await client.initialize();
  bridge.innerHTML = `
    connected to <code>${result.host.name}</code>
    · granted <code>${result.grantedScopes.join(', ') || '(nothing)'}</code>
  `;
} catch (error) {
  const detail =
    error instanceof MoonpoolError ? `${error.code} - ${error.message}` : String(error);
  bridge.textContent = `handshake failed: ${detail}`;
}
