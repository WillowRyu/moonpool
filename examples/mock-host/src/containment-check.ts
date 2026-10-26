/** Manual integration fixture using the shipped wrapper/registry/provider adapters. */
import { parseManifest } from '@moonpool/host';
import aText from '../../hello-miniapp/moonpool.json?raw';
import bText from '../../hello-miniapp/moonpool-second.json?raw';
import { reportHostError } from './browser-contract';
import { type BrowserPortal, createBrowserHost } from './browser-portal';
import { MINI_APP_ORIGINS } from './development-origins';
import { createMemoryStorageProvider } from './memory-storage';

const root = document.querySelector<HTMLElement>('#app');
if (root === null) {
  throw new Error('missing fixture root');
}
root.innerHTML = `<h1>T18 integrated containment checks</h1><p id="browser"></p>
<p>Uses the actual browser host, served wrappers, strict JSON boundary, and retained provider.</p>
<div><button id="restart-a">Create fresh A</button><button id="restart-b">Create fresh B</button><button id="a2">Create another A</button>
<button id="close-a">Close A</button><button id="close-a2">Close extra A</button><button id="restricted-b">Recreate B profile-only</button><button id="notify-b">Notify B dark/ko-KR</button>
<button id="hold">Hold next profile</button><button id="release">Release held profile</button>
<button id="wrapper-reload">Reload A wrapper at same URL</button><button id="wrapper-switch">Switch A wrapper to B policy</button>
<button id="retired">Try retired A control</button><button id="footprint">Inspect frame footprint</button>
<label>Pending B id <input id="reply-id" type="number" value="2"></label><button id="forge">Forge B reply from outer host</button></div>
<div id="probe-controls" role="group" aria-label="Guest verification commands"></div>
<div class="portals"><section><h2>A</h2><p id="state-a"></p><div id="slot-a"></div></section>
<section><h2>B</h2><p id="state-b"></p><div id="slot-b"></div></section>
<section><h2>Another instance of A</h2><p id="state-a2">Not started</p><div id="slot-a2"></div></section></div>
<p id="frames"></p><pre id="events"></pre>`;
const events: string[] = [];
const log = (text: string) => {
  events.push(text);
  const target = root.querySelector('#events');
  if (target !== null) {
    target.textContent = events.join('\n');
  }
};
const browser = root.querySelector('#browser');
if (browser !== null) {
  browser.textContent = navigator.userAgent;
}
let held: (() => void) | undefined;
let holdNext = false;
let calls = 0;
const host = createBrowserHost({
  origins: MINI_APP_ORIGINS,
  hostInfo: { name: 'T18 integration host', version: '0.1.0', platform: 'browser' },
  environment: { locale: 'en', colorScheme: 'light' },
  capabilities: {
    storage: createMemoryStorageProvider(),
    profile: {
      async get() {
        const number = ++calls;
        if (holdNext) {
          holdNext = false;
          await new Promise<void>((resolve) => {
            held = resolve;
            log(`profile ${number} held`);
          });
        }
        log(`profile ${number} provider completed`);
        return { displayName: 'Contained public user' };
      },
    },
  },
});
const portals = new Map<string, BrowserPortal>();
let retired: BrowserPortal | undefined;
const footprint = () => {
  const frames = [...document.querySelectorAll('iframe')];
  let guests = 0;
  for (const frame of frames) {
    try {
      guests += frame.contentDocument?.querySelectorAll('iframe').length ?? 0;
    } catch {
      /* Replaced wrapper is being revoked. */
    }
  }
  const target = root.querySelector('#frames');
  if (target !== null) {
    target.textContent = `wrappers=${frames.length} guests=${guests}`;
  }
};
const create = (slot: string, storageAllowed = true) => {
  const previous = portals.get(slot);
  if (previous !== undefined) {
    if (slot === 'a') {
      retired = previous;
    }
    void previous.close('Host recreation').catch(reportHostError);
  }
  const container = root.querySelector<HTMLElement>(`#slot-${slot}`);
  const state = root.querySelector(`#state-${slot}`);
  if (container === null || state === null) {
    throw new Error('missing slot');
  }
  const manifest = parseManifest(slot === 'b' ? bText : aText);
  const portal = host.open({
    container,
    manifest: { ...manifest, entry: 'containment-probe.html' },
    grantedScopes: storageAllowed ? ['profile', 'storage'] : ['profile'],
    onClosed(reason) {
      if (portals.get(slot) !== portal) {
        return;
      }
      if (slot === 'a') {
        retired = portal;
      }
      portals.delete(slot);
      state.textContent = `revoked: ${reason}`;
      log(`${slot} revoked: ${reason}`);
      footprint();
    },
  });
  portals.set(slot, portal);
  state.textContent = `active: ${manifest.id}`;
  log(`${slot} host-created`);
};
const bind = (id: string, action: () => void) =>
  root.querySelector(`#${id}`)?.addEventListener('click', action);
bind('restart-a', () => create('a'));
bind('restart-b', () => create('b'));
bind('a2', () => create('a2'));
bind('restricted-b', () => create('b', false));
bind('close-a2', () => {
  void portals.get('a2')?.close('Extra A closed').catch(reportHostError);
});
bind('close-a', () => {
  void portals.get('a')?.close('Host close').catch(reportHostError);
});
bind('hold', () => {
  holdNext = true;
  log('next profile will wait');
});
bind('release', () => {
  const finish = held;
  held = undefined;
  finish?.();
  log('held provider released');
});
bind('notify-b', () => {
  void portals
    .get('b')
    ?.notifyEnvironmentChanged({ colorScheme: 'dark', locale: 'ko-KR' })
    .then(() => log('B notification submitted across realms'))
    .catch(reportHostError);
});
bind('wrapper-reload', () => {
  portals.get('a')?.frame.contentWindow?.location.reload();
});
bind('wrapper-switch', () => {
  const frame = portals.get('a')?.frame;
  if (frame !== undefined) {
    frame.src = new URL('/portal-wrapper.html?app=com.example.second', location.origin).href;
  }
});
bind('retired', () => {
  void retired
    ?.notifyLifecycle('paused')
    .then(() => log('ERROR: retired control accepted'))
    .catch(() => log('retired A control rejected'));
});
bind('footprint', footprint);
bind('forge', () => {
  const input = root.querySelector<HTMLInputElement>('#reply-id');
  const guest = portals.get('b')?.frame.contentDocument?.querySelector('iframe');
  if (input !== null && guest?.contentWindow !== null && guest?.contentWindow !== undefined) {
    const id = Number(input.value);
    guest.contentWindow.postMessage(
      { jsonrpc: '2.0', id, result: { displayName: 'FORGED OUTER REPLY' } },
      'http://localhost:5175',
    );
    log(`outer forged B response id=${id}; source must be rejected`);
  }
});
const commandRoot = root.querySelector('#probe-controls');
const commands = [
  ['a', 'profile', 'A profile'],
  ['b', 'profile', 'B profile'],
  ['a', 'set', 'A save'],
  ['b', 'set', 'B save'],
  ['a', 'get', 'A read'],
  ['b', 'get', 'B read'],
  ['a2', 'get', 'Extra A read'],
  ['a', 'reload', 'A inner reload'],
  ['a', 'internal', 'A internal page'],
  ['a', 'hash', 'A hash'],
  ['a', 'other', 'A to B'],
  ['a', 'foreign', 'A foreign'],
  ['a', 'form', 'A foreign form'],
  ['a', 'redirect', 'A redirect'],
  ['a', 'bounce', 'A silent bounce'],
  ['a', 'access', 'A host API attempt'],
];
for (const [slot, command, label] of commands) {
  if (slot === undefined || command === undefined || label === undefined) {
    continue;
  }
  const button = document.createElement('button');
  button.textContent = label;
  button.addEventListener('click', () => {
    const guest = portals.get(slot)?.frame.contentDocument?.querySelector('iframe');
    const origin = MINI_APP_ORIGINS.get(slot === 'b' ? 'com.example.second' : 'com.example.hello');
    if (
      guest?.contentWindow !== null &&
      guest?.contentWindow !== undefined &&
      origin !== undefined
    ) {
      // Instrumentation only: not an additional SDK method or a transport bypass.
      guest.contentWindow.postMessage(
        {
          probe: 'moonpool-t18',
          command,
          text: JSON.stringify({ owner: slot, flags: [null, false, 0] }),
        },
        origin,
      );
      log(`${slot} fixture command ${command}`);
    }
  });
  commandRoot?.appendChild(button);
}
create('a');
create('b');
