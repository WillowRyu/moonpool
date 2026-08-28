/**
 * mock-host — a browser stand-in for a native host application.
 *
 * Embeds one mini app in an iframe on a pinned, distinct origin (SPEC §8.1)
 * and serves its bridge: an iframe transport wired to the pure host kernel.
 * The grant is deliberately narrower than the manifest asks for, so the
 * handshake's scope intersection is visible on screen.
 */

import { createHost } from '@moonpool/host';
import { type MiniAppManifest, PROTOCOL_VERSION } from '@moonpool/protocol';
import { createIframeTransport } from '@moonpool/transport-iframe';

/** SPEC §8.1 — pinned per mini app id, never derived at runtime. */
const MINI_APP_ORIGINS: Record<string, string> = {
  'com.example.hello': 'http://localhost:5174',
};

const portalOrigin = MINI_APP_ORIGINS['com.example.hello'];
if (portalOrigin === undefined) {
  throw new Error('mock-host: no development origin pinned for com.example.hello');
}

const root = document.querySelector<HTMLElement>('#app');
if (root === null) {
  throw new Error('mock-host: #app is missing from index.html');
}

root.innerHTML = `
  <header>
    <h1>Moonpool mock host</h1>
    <dl>
      <dt>host origin</dt><dd><code>${window.location.origin}</code></dd>
      <dt>portal origin</dt><dd><code>${portalOrigin}</code></dd>
      <dt>protocol</dt><dd><code>${PROTOCOL_VERSION}</code></dd>
    </dl>
  </header>
  <iframe title="com.example.hello" src="${portalOrigin}/"></iframe>
`;

/**
 * A real host parses this out of the mini app bundle it downloaded, before
 * the web view exists — the Portal never serves its own manifest to the host.
 * Held as a typed literal until the host package grows a manifest parser.
 */
const MANIFEST: MiniAppManifest = {
  manifestVersion: 1,
  id: 'com.example.hello',
  name: 'Hello',
  version: '1.0.0',
  entry: 'index.html',
  protocolVersion: '0.1',
  permissions: ['profile', 'storage'],
};

const iframe = root.querySelector('iframe');
if (iframe === null || iframe.contentWindow === null) {
  throw new Error('mock-host: the Portal iframe has no content window');
}

// Attached in the SAME synchronous task that created the iframe. JavaScript is
// single threaded, so this script runs to completion before any script inside
// the iframe can run: the host is listening before the Portal exists. That is
// what makes the Portal-initiated handshake (SPEC §5) impossible to lose.
const transport = createIframeTransport({
  peerWindow: iframe.contentWindow,
  peerOrigin: portalOrigin,
});

createHost({
  hostInfo: { name: 'moonpool-mock-host', version: '0.1.0', platform: 'browser' },
  manifest: MANIFEST,
  // Deliberately narrower than the manifest asks for: the mini app declares
  // profile AND storage, this host grants only profile. The handshake result
  // reports the intersection, which is the permission model made visible.
  grantedScopes: ['profile'],
  environment: { locale: 'ko-KR', colorScheme: 'light' },
}).connect(transport);
