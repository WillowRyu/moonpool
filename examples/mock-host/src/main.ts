/**
 * mock-host — a browser stand-in for a native host application.
 *
 * Embeds one mini app in an iframe on a pinned, distinct origin (SPEC §8.1)
 * and serves its bridge: an iframe transport wired to the pure host kernel.
 * The default grant is deliberately narrower than the manifest asks for.
 * Host controls start a new Portal to demonstrate storage denial and success.
 */

import { createHost, parseManifest } from '@moonpool/host';
import { PROTOCOL_VERSION, type Transport } from '@moonpool/protocol';
import { createIframeTransport } from '@moonpool/transport-iframe';
import manifestText from '../../hello-miniapp/moonpool.json?raw';
import { createMemoryStorageProvider } from './memory-storage';

/** SPEC §8.1 — pinned per mini app id, never derived at runtime. */
const MINI_APP_ORIGINS = new Map([['com.example.hello', 'http://localhost:5174']]);

// SPEC §7: bundle host-owned file text and validate it before any Portal exists.
// The mini app does not supply its own identity or permissions over the bridge.
const MANIFEST = parseManifest(manifestText);
const portalOrigin = MINI_APP_ORIGINS.get(MANIFEST.id);
if (portalOrigin === undefined) {
  throw new Error(`mock-host: no development origin pinned for ${MANIFEST.id}`);
}
// ADR 0011: resolve the validated relative entry from this app's pinned root.
const portalUrl = new URL(MANIFEST.entry, `${portalOrigin}/`).href;

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
  <div class="actions" role="group" aria-label="Portal configuration">
    <button type="button" id="profile-only">Start profile-only Portal</button>
    <button type="button" id="with-storage">Start Portal with storage</button>
  </div>
  <p id="configuration" role="status"></p>
  <p class="hint">Each selection starts a new Portal. Host reload clears memory storage.</p>
  <div id="portal"></div>
`;

const portal = root.querySelector<HTMLElement>('#portal');
const profileOnly = root.querySelector<HTMLButtonElement>('#profile-only');
const withStorage = root.querySelector<HTMLButtonElement>('#with-storage');
const configuration = root.querySelector<HTMLElement>('#configuration');
if (portal === null || profileOnly === null || withStorage === null || configuration === null) {
  throw new Error('mock-host: Portal configuration controls are missing');
}

// Storage belongs to this host page, not to one Portal's document or grants.
const storage = createMemoryStorageProvider();
let activeTransport: Transport | undefined;

const startPortal = (storageAllowed: boolean): void => {
  // SPEC §9.3: grants are fixed for one connection. Dispose the old receiver
  // and replace its iframe instead of changing permission inside a live bridge.
  activeTransport?.close();
  const iframe = document.createElement('iframe');
  iframe.title = MANIFEST.id;
  iframe.src = portalUrl;
  portal.replaceChildren(iframe);
  if (iframe.contentWindow === null) {
    throw new Error('mock-host: the Portal iframe has no content window');
  }

  // Attach synchronously in the same task as frame creation so its first
  // portal.initialize cannot run before this receiver is ready (SPEC §5).
  const transport = createIframeTransport({
    peerWindow: iframe.contentWindow,
    peerOrigin: portalOrigin,
  });
  activeTransport = transport;
  createHost({
    hostInfo: { name: 'moonpool-mock-host', version: '0.1.0', platform: 'browser' },
    manifest: MANIFEST,
    // Only these host buttons select grants; no mini-app params or URL do so.
    grantedScopes: storageAllowed ? ['profile', 'storage'] : ['profile'],
    environment: { locale: 'ko-KR', colorScheme: 'light' },
    capabilities: {
      // SPEC §6.3 / §9.4 / §9.5 — fixed public data, supplied asynchronously.
      // Installing a provider does not bypass the kernel's profile scope check.
      profile: {
        async get() {
          return { displayName: 'Moonpool Explorer' };
        },
      },
      storage,
    },
  }).connect(transport, {
    async onCloseRequested(reason) {
      // A stale handler must never close a Portal created by a later selection.
      if (activeTransport !== transport || iframe.parentElement !== portal) {
        return;
      }
      activeTransport = undefined;
      transport.close();
      iframe.remove();
      profileOnly.setAttribute('aria-pressed', 'false');
      withStorage.setAttribute('aria-pressed', 'false');
      // Caller-provided reason is text, never executable markup (§9.6).
      configuration.textContent =
        reason === undefined
          ? 'Portal dismissed. Choose a configuration to start again.'
          : `Portal dismissed: ${reason}. Choose a configuration to start again.`;
    },
  });
  profileOnly.setAttribute('aria-pressed', String(!storageAllowed));
  withStorage.setAttribute('aria-pressed', String(storageAllowed));
  configuration.textContent = storageAllowed
    ? 'Configuration: profile + storage'
    : 'Configuration: profile only (storage denied)';
};

profileOnly.addEventListener('click', () => startPortal(false));
withStorage.addEventListener('click', () => startPortal(true));
startPortal(false);
