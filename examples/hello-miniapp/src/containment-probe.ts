/** Manual guest controls; all capability calls still use the actual SDK/transport. */
import { createClient, MoonpoolError } from '@moonpool/client';
import { isJsonObject, isJsonValue, type JsonValue } from '@moonpool/protocol';
import { createIframeTransport } from '@moonpool/transport-iframe';
import { createCloseDemo } from './close-demo';
import { createStorageDemo } from './storage-demo';

const root = document.querySelector<HTMLElement>('#app');
if (root === null) {
  throw new Error('missing probe root');
}
root.innerHTML = `<h1>Guest ${location.origin}</h1><p id="state">initializing</p>
<button id="profile">Profile</button><button id="get">Read shared-key</button><button id="set">Save shared-key</button>
<textarea id="value" aria-label="Stored JSON value">{"flags":[null,false,0]}</textarea>
<p id="profile-state"></p><p id="storage-state"></p>
<button id="reload">Inner reload</button><button id="internal">Internal page</button><button id="hash">Hash only</button>
<button id="other">Navigate to other app</button><button id="foreign">Navigate foreign</button>
<button id="redirect">Redirect foreign</button><button id="bounce">Silent foreign bounce</button>
<form action="http://127.0.0.1:5174/navigation-foreign.html" method="get"><button>Submit foreign form</button></form>
<button id="access">Attempt host API access</button>
<section id="actual-storage" aria-label="Actual storage component"></section>
<section id="actual-close" aria-label="Actual close component"></section>
<pre id="events"></pre>`;
const status = root.querySelector('#state');
const profileState = root.querySelector('#profile-state');
const storageState = root.querySelector('#storage-state');
const input = root.querySelector<HTMLTextAreaElement>('#value');
const output = root.querySelector('#events');
const storageView = root.querySelector<HTMLElement>('#actual-storage');
const closeView = root.querySelector<HTMLElement>('#actual-close');
if (
  status === null ||
  profileState === null ||
  storageState === null ||
  input === null ||
  output === null ||
  storageView === null ||
  closeView === null
) {
  throw new Error('missing probe controls');
}
const log = (message: string) => {
  output.textContent += `${message}\n`;
};
const client = createClient({
  transport: createIframeTransport({ peerWindow: parent, peerOrigin: 'http://localhost:5173' }),
});
const unsubscribeNotifications = client.onNotification((notification) => {
  log(`notification ${notification.method}: ${JSON.stringify(notification.params)}`);
});
let nextId = 2;
const call = async (method: string, params?: { [key: string]: JsonValue }) => {
  const id = nextId++;
  log(`call ${id} ${method}`);
  return params === undefined ? client.call(method) : client.call(method, params);
};
// These are the same UI components used by the normal mini-app entry.
const viewClient = { call };
const storageDemo = createStorageDemo(storageView, viewClient);
const closeDemo = createCloseDemo(closeView, viewClient);
const errorText = (error: unknown) =>
  error instanceof MoonpoolError ? `${error.code} ${error.message}` : 'local error';
const actions = new Map<string, () => void>();
const bind = (id: string, action: () => void) => {
  actions.set(id, action);
  root.querySelector(`#${id}`)?.addEventListener('click', action);
};
bind('profile', () => {
  profileState.textContent = `profile pending id=${nextId}`;
  void call('profile.get')
    .then((result) => {
      profileState.textContent = `profile result ${JSON.stringify(result)}`;
    })
    .catch((error: unknown) => {
      profileState.textContent = errorText(error);
    });
});
bind('get', () => {
  storageState.textContent = 'storage pending';
  void call('storage.get', { key: 'shared-key' })
    .then((result) => {
      storageState.textContent = `stored ${JSON.stringify(result)}`;
    })
    .catch((error: unknown) => {
      storageState.textContent = errorText(error);
    });
});
bind('set', () => {
  let value: unknown;
  try {
    value = JSON.parse(input.value);
  } catch {
    storageState.textContent = 'invalid JSON text';
    return;
  }
  if (!isJsonValue(value)) {
    storageState.textContent = 'invalid JSON value';
    return;
  }
  void call('storage.set', { key: 'shared-key', value })
    .then(() => {
      storageState.textContent = 'saved';
    })
    .catch((error: unknown) => {
      storageState.textContent = errorText(error);
    });
});
bind('reload', () => location.reload());
bind('internal', () => {
  location.href = '/containment-probe.html?internal=1';
});
bind('hash', () => {
  location.hash = 'same-document';
  log('hash changed');
});
bind('other', () => {
  location.href = `http://localhost:${location.port === '5174' ? '5175' : '5174'}/containment-probe.html`;
});
bind('foreign', () => {
  location.href = 'http://127.0.0.1:5174/navigation-foreign.html';
});
bind('redirect', () => {
  location.href = '/navigation-redirect';
});
bind('bounce', () => {
  location.href = 'http://127.0.0.1:5174/navigation-bounce.html';
});
bind('access', () => {
  try {
    Reflect.get(top ?? parent, 'moonpoolBootstrap');
    log('ERROR: host API reached');
  } catch {
    log('host API blocked by SOP');
  }
  parent.postMessage(
    { bootstrap: true, app: 'com.example.second', grantedScopes: ['storage'] },
    'http://localhost:5173',
  );
});
actions.set('form', () => root.querySelector('form')?.requestSubmit());
for (const [command, selector] of [
  ['demo-set', '#storage-set'],
  ['demo-get', '#storage-get'],
  ['demo-delete', '#storage-delete'],
  ['demo-close', '#portal-close'],
]) {
  if (command !== undefined && selector !== undefined) {
    actions.set(command, () => root.querySelector<HTMLButtonElement>(selector)?.click());
  }
}
actions.set('unsubscribe', () => {
  unsubscribeNotifications();
  log('notification subscription removed');
});
actions.set('client-close', () => {
  client.close();
  log('local client closed');
});
actions.set('bad-write', () => {
  const id = nextId++;
  log(`call ${id} storage.set with Date`);
  // Deliberately cross the native structured-clone boundary without repairing input.
  const pending: Promise<unknown> = Reflect.apply(client.call, client, [
    'storage.set',
    { key: 'shared-key', value: new Date('2026-01-01T00:00:00Z') },
  ]);
  void pending
    .then(() => {
      storageState.textContent = 'ERROR: Date accepted';
    })
    .catch((error: unknown) => {
      storageState.textContent = errorText(error);
    });
});
actions.set('bad-version', () => {
  void call('portal.initialize', { protocolVersion: '9.9' })
    .then(() => {
      status.textContent = 'ERROR: unsupported version accepted';
    })
    .catch((error: unknown) => {
      status.textContent = errorText(error);
    });
});
actions.set('good-version', () => {
  void call('portal.initialize', { protocolVersion: '0.1' })
    .then(() => {
      status.textContent = 'explicit initialization 0.1 succeeded';
    })
    .catch((error: unknown) => {
      status.textContent = errorText(error);
    });
});
// Fixture-only controls let an outer UI drive nested frames. The SDK transport
// still rejects outer-host replies: only the immediate wrapper is its peer.
window.addEventListener('message', (event: MessageEvent<unknown>) => {
  if (
    event.origin !== 'http://localhost:5173' ||
    event.source !== top ||
    !isJsonValue(event.data) ||
    !isJsonObject(event.data) ||
    event.data.probe !== 'moonpool-t18' ||
    typeof event.data.command !== 'string'
  ) {
    return;
  }
  if (event.data.command === 'set' && typeof event.data.text === 'string') {
    input.value = event.data.text;
  }
  if (event.data.command === 'demo-set' && typeof event.data.text === 'string') {
    const valueField = storageView.querySelector<HTMLInputElement>('#storage-value');
    if (valueField !== null) {
      valueField.value = event.data.text;
    }
  }
  actions.get(event.data.command)?.();
});
try {
  const result = await client.initialize();
  status.textContent = `initialized ${result.miniApp.id}; grants ${result.grantedScopes.join(',')}`;
  storageDemo.ready(result.grantedScopes);
  closeDemo.ready();
} catch (error) {
  status.textContent = errorText(error);
  storageDemo.unavailable('initialization failed');
  closeDemo.unavailable('initialization failed');
}
