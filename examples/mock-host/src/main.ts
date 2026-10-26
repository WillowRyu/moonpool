/** Browser development host: independently contained Portals, retained providers. */
import { parseManifest } from '@moonpool/host';
import { PROTOCOL_VERSION } from '@moonpool/protocol';
import manifestText from '../../hello-miniapp/moonpool.json?raw';
import secondManifestText from '../../hello-miniapp/moonpool-second.json?raw';
import { reportHostError } from './browser-contract';
import { type BrowserPortal, createBrowserHost } from './browser-portal';
import { MINI_APP_ORIGINS } from './development-origins';
import { createMemoryStorageProvider } from './memory-storage';

const MANIFEST = parseManifest(manifestText);
const portalOrigin = MINI_APP_ORIGINS.get(MANIFEST.id);
if (portalOrigin === undefined) {
  throw new Error(`mock-host: no development origin pinned for ${MANIFEST.id}`);
}
const SECOND = parseManifest(secondManifestText);
const root = document.querySelector<HTMLElement>('#app');
if (root === null) {
  throw new Error('mock-host: #app is missing');
}
root.innerHTML = `
  <header><h1>Moonpool mock host</h1><dl>
    <dt>host origin</dt><dd><code>${window.location.origin}</code></dd>
    <dt>portal origin</dt><dd><code>${portalOrigin}</code></dd>
    <dt>protocol</dt><dd><code>${PROTOCOL_VERSION}</code></dd>
  </dl></header>
  <div class="actions" role="group" aria-label="Portal configuration">
    <button type="button" id="profile-only">Start profile-only Portal</button>
    <button type="button" id="with-storage">Start Portal with storage</button>
    <button type="button" id="second-app">Start second app</button>
  </div>
  <p><a href="/containment-check.html">Navigation containment checks</a></p>
  <p class="hint">Selections replace only their Portal. Host reload clears memory storage.</p>
  <div class="portals"><section><h2>Hello</h2><p id="configuration" role="status"></p><div id="portal"></div></section>
    <section><h2>Second app</h2><p id="secondary-status" role="status">Not started</p><div id="secondary"></div></section></div>
`;
const portal = root.querySelector<HTMLElement>('#portal');
const secondary = root.querySelector<HTMLElement>('#secondary');
const profileOnly = root.querySelector<HTMLButtonElement>('#profile-only');
const withStorage = root.querySelector<HTMLButtonElement>('#with-storage');
const secondButton = root.querySelector<HTMLButtonElement>('#second-app');
const configuration = root.querySelector<HTMLElement>('#configuration');
const secondaryStatus = root.querySelector<HTMLElement>('#secondary-status');
if (
  portal === null ||
  secondary === null ||
  profileOnly === null ||
  withStorage === null ||
  secondButton === null ||
  configuration === null ||
  secondaryStatus === null
) {
  throw new Error('mock-host: Portal controls are missing');
}

// This provider outlives every wrapper. ADR 0003 partitions its data by app id.
const storage = createMemoryStorageProvider();
export const browserHost = createBrowserHost({
  origins: MINI_APP_ORIGINS,
  hostInfo: { name: 'moonpool-mock-host', version: '0.1.0', platform: 'browser' },
  environment: { locale: 'ko-KR', colorScheme: 'light' },
  capabilities: {
    profile: {
      async get() {
        return { displayName: 'Moonpool Explorer' };
      },
    },
    storage,
  },
});
let activePortal: BrowserPortal | undefined;
let secondPortal: BrowserPortal | undefined;
const startPortal = (storageAllowed: boolean) => {
  void activePortal?.close('Configuration changed').catch(reportHostError);
  const instance = browserHost.open({
    container: portal,
    manifest: MANIFEST,
    grantedScopes: storageAllowed ? ['profile', 'storage'] : ['profile'],
    onClosed(reason) {
      if (activePortal !== instance) {
        return;
      }
      activePortal = undefined;
      profileOnly.setAttribute('aria-pressed', 'false');
      withStorage.setAttribute('aria-pressed', 'false');
      // Guest reason is displayed only as text. Retired callbacks cannot affect a replacement.
      configuration.textContent = `Portal dismissed: ${reason}. Choose a configuration to start again.`;
    },
  });
  activePortal = instance;
  profileOnly.setAttribute('aria-pressed', String(!storageAllowed));
  withStorage.setAttribute('aria-pressed', String(storageAllowed));
  configuration.textContent = storageAllowed
    ? 'Configuration: profile + storage'
    : 'Configuration: profile only (storage denied)';
};
profileOnly.addEventListener('click', () => startPortal(false));
withStorage.addEventListener('click', () => startPortal(true));
secondButton.addEventListener('click', () => {
  void secondPortal?.close('Second app replaced').catch(reportHostError);
  const instance = browserHost.open({
    container: secondary,
    manifest: SECOND,
    grantedScopes: ['profile', 'storage'],
    onClosed(reason) {
      if (secondPortal !== instance) {
        return;
      }
      secondPortal = undefined;
      secondaryStatus.textContent = `Portal dismissed: ${reason}`;
    },
  });
  secondPortal = instance;
  secondaryStatus.textContent = 'Configuration: profile + storage';
});
startPortal(false);
