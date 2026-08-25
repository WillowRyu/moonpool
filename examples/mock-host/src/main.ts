/**
 * mock-host — a browser stand-in for a native host application.
 *
 * At this step it only proves the plumbing: the page loads a mini app in an
 * iframe on a different origin (SPEC §8.1) and reports both. Nothing crosses
 * the bridge yet — createHost needs a transport, which is the next step.
 */
import { PROTOCOL_VERSION } from '@moonpool/protocol';

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
