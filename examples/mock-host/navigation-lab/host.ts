import { createHost } from '../../../packages/host/src/index';
import {
  isJsonObject,
  isJsonValue,
  type JsonValue,
  type Transport,
} from '../../../packages/protocol/src/index';
import { createIframeTransport, isFromPeer } from '../../../packages/transport-iframe/src/index';

const ALLOWED = 'http://127.0.0.1:5274';
const FOREIGN = 'http://127.0.0.1:5275';
const root = document.querySelector<HTMLElement>('#app');
if (root === null) {
  throw new Error('missing lab root');
}
root.innerHTML = `
  <h1>T17 navigation observations</h1>
  <p>Deliberately uncontained transport lab. The normal example uses the approved per-Portal wrapper profile.</p>
  <p id="browser"></p>
  <label>Experimental policy <select id="policy"><option value="baseline">Existing bridge only</option><option value="load">Close on every load after first</option></select></label>
  <div class="controls">
    <button id="start">Start fresh Portal</button><button id="inspect">Inspect parent view</button>
    <button id="same">Child same-origin navigation</button><button id="reload">Child reload</button>
    <button id="hash">Child hash change</button><button id="foreign">Child foreign navigation</button>
    <button id="return">Foreign return without initialize</button><button id="bounce">Silent foreign bounce before load</button>
    <button id="target">Send targetOrigin marker</button><button id="proof">Read fixture server observations</button>
    <button id="form">Child foreign form submission</button><button id="redirect">Allowed URL redirects to foreign</button>
    <button id="intruder">Other allowed-origin frame calls profile</button><button id="profile">Bound peer profile positive control</button>
    <button id="foreign-marker">Foreign targetOrigin marker positive control</button>
  </div>
  <p id="summary"></p><div id="portal"></div><div id="other-frame"></div><pre id="log"></pre><pre id="server"></pre>
`;
const portal = root.querySelector<HTMLElement>('#portal');
const log = root.querySelector<HTMLElement>('#log');
const summary = root.querySelector<HTMLElement>('#summary');
const browser = root.querySelector<HTMLElement>('#browser');
const serverOutput = root.querySelector<HTMLElement>('#server');
const policy = root.querySelector<HTMLSelectElement>('#policy');
if (
  portal === null ||
  log === null ||
  summary === null ||
  browser === null ||
  serverOutput === null ||
  policy === null
) {
  throw new Error('missing lab controls');
}
browser.textContent = `UA: ${navigator.userAgent} | frame-src restriction: ${location.pathname.includes('csp')}`;
let frame: HTMLIFrameElement | undefined;
let intruder: HTMLIFrameElement | undefined;
let peer: Window | null = null;
let transport: Transport | undefined;
let run = '';
let loads = 0;
let calls = 0;
let closed = false;
let startedAt = performance.now();
let rows: Array<Record<string, unknown>> = [];

const record = (event: string, data: Record<string, unknown> = {}) => {
  rows.push({ n: rows.length + 1, ms: Math.round(performance.now() - startedAt), event, ...data });
  log.textContent = rows.map((row) => JSON.stringify(row)).join('\n');
  summary.textContent = `run=${run} | loads=${loads} | profile calls=${calls} | bridge closed=${closed}`;
};
const inspect = () => {
  let href = 'no frame';
  let documentAccess = 'no frame';
  let navigationAccess = 'no frame';
  try {
    href = frame?.contentWindow?.location.href ?? 'none';
  } catch (error) {
    href = error instanceof DOMException ? error.name : 'threw';
  }
  try {
    documentAccess = frame?.contentDocument === null ? 'null' : 'readable';
  } catch {
    documentAccess = 'threw';
  }
  try {
    navigationAccess =
      Reflect.get(frame?.contentWindow ?? {}, 'navigation') === undefined
        ? 'unavailable'
        : 'readable';
  } catch (error) {
    navigationAccess = error instanceof DOMException ? error.name : 'threw';
  }
  record('parent-inspection', {
    src: frame?.getAttribute('src'),
    sameWindowProxy: frame?.contentWindow === peer,
    href,
    documentAccess,
    navigationAccess,
  });
};
window.addEventListener('message', (event: MessageEvent<unknown>) => {
  const fromPeer = event.source === peer;
  const fromOther = intruder !== undefined && event.source === intruder.contentWindow;
  if ((!fromPeer && !fromOther) || !isJsonValue(event.data) || !isJsonObject(event.data)) {
    return;
  }
  record('message', {
    origin: event.origin,
    role: fromPeer ? 'bound-peer' : 'other-frame',
    sameWindowProxy: event.source === peer,
    passesOriginAndSource: isFromPeer(event, { origin: ALLOWED, window: peer }),
    data: event.data,
  });
});
document.addEventListener('securitypolicyviolation', (event) => {
  record('csp-violation', { directive: event.effectiveDirective, blockedURI: event.blockedURI });
});

const start = () => {
  transport?.close();
  intruder?.remove();
  intruder = undefined;
  rows = [];
  loads = 0;
  calls = 0;
  closed = false;
  startedAt = performance.now();
  run = String(Date.now());
  serverOutput.textContent = '';
  const current = document.createElement('iframe');
  current.title = 'Navigation probe';
  current.src = `${ALLOWED}/probe.html?run=${run}`;
  frame = current;
  current.addEventListener('load', () => {
    if (frame !== current) {
      return;
    }
    loads += 1;
    record('iframe-load');
    inspect();
    if (policy.value === 'load' && loads > 1) {
      transport?.close();
    }
  });
  new MutationObserver((mutations) => {
    if (frame === current) {
      record('iframe-attribute-change', {
        attributes: mutations.map((mutation) => mutation.attributeName),
      });
    }
  }).observe(current, { attributes: true, attributeFilter: ['src', 'srcdoc'] });
  portal.replaceChildren(current);
  peer = current.contentWindow;
  if (peer === null) {
    throw new Error('missing probe window');
  }
  const base = createIframeTransport({ peerWindow: peer, peerOrigin: ALLOWED });
  transport = {
    onMessage: base.onMessage,
    send(message: JsonValue) {
      record('bridge-send', { data: message });
      base.send(message);
    },
    close() {
      if (!closed) {
        closed = true;
        record('bridge-close');
      }
      base.close();
    },
  };
  createHost({
    hostInfo: { name: 'navigation-lab', version: '0.1.0', platform: 'browser' },
    manifest: {
      manifestVersion: 1,
      id: 'com.example.navigation',
      name: 'Navigation probe',
      version: '1.0.0',
      entry: 'probe.html',
      protocolVersion: '0.1',
      permissions: ['profile'],
    },
    grantedScopes: ['profile'],
    environment: { locale: 'en', colorScheme: 'light' },
    capabilities: {
      profile: {
        async get() {
          calls += 1;
          record('profile-provider');
          return { displayName: 'Lab user' };
        },
      },
    },
  }).connect(transport);
  record('start', { policy: policy.value, allowedOrigin: ALLOWED, foreignOrigin: FOREIGN });
};
const command = (name: string, targetOrigin = ALLOWED) => {
  record('command', { name, targetOrigin });
  peer?.postMessage({ lab: 'navigation', command: name, run }, targetOrigin);
};
for (const name of ['same', 'reload', 'hash', 'foreign', 'bounce', 'form', 'redirect']) {
  root.querySelector(`#${name}`)?.addEventListener('click', () => command(name));
}
root.querySelector('#return')?.addEventListener('click', () => command('return', FOREIGN));
root.querySelector('#target')?.addEventListener('click', () => {
  record('marker-attempt');
  transport?.send({ lab: 'marker' });
});
root.querySelector('#foreign-marker')?.addEventListener('click', () => {
  record('foreign-marker-positive-control');
  peer?.postMessage({ lab: 'marker' }, FOREIGN);
});
root.querySelector('#profile')?.addEventListener('click', () => command('profile'));
root.querySelector('#intruder')?.addEventListener('click', () => {
  intruder?.remove();
  const current = document.createElement('iframe');
  current.title = 'Other allowed-origin sender';
  current.src = `${ALLOWED}/probe.html?run=${run}&mode=intruder`;
  intruder = current;
  root.querySelector('#other-frame')?.replaceChildren(current);
  record('other-frame-created', { origin: ALLOWED });
});
root.querySelector('#start')?.addEventListener('click', start);
root.querySelector('#inspect')?.addEventListener('click', inspect);
root.querySelector('#proof')?.addEventListener('click', async () => {
  const response = await fetch(`/observations?run=${run}`);
  serverOutput.textContent = `Fixture-only server evidence (not available to a production embedder):\n${await response.text()}`;
});
start();
