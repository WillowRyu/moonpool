import { createClient } from '../../../packages/client/src/index';
import { createIframeTransport } from '../../../packages/transport-iframe/src/index';

const HOST = 'http://127.0.0.1:5373';
const output = document.querySelector<HTMLElement>('#events');
const status = document.querySelector<HTMLElement>('#status');
if (output === null || status === null) {
  throw new Error('missing guest output');
}
const record = (event: string, data: unknown) => {
  output.textContent += `${event}: ${JSON.stringify(data)}\n`;
};
const client = createClient({
  transport: createIframeTransport({ peerWindow: parent, peerOrigin: HOST }),
});
client.onNotification((notification) => {
  record('notification', notification);
});
let identity = '';
const action = async (name: string) => {
  try {
    if (name === 'profile') {
      status.textContent = 'profile pending';
      const profile = await client.call('profile.get');
      record('profile', profile);
      status.textContent = 'profile completed';
    } else if (name === 'storage') {
      record('storage', await client.call('storage.get', { key: 'same-key' }));
    } else if (name === 'reload') {
      location.reload();
    } else if (name === 'to-b') {
      location.assign('http://127.0.0.1:5375/multi-probe.html?claimedApp=A');
    } else if (name === 'foreign') {
      location.assign('http://127.0.0.1:5376/multi-foreign.html');
    } else if (name === 'bootstrap-access') {
      try {
        Reflect.get(top ?? parent, 'multiLabBootstrap');
        record('bootstrap-access', 'unexpected access');
      } catch (error) {
        record('bootstrap-access', error instanceof DOMException ? error.name : 'threw');
      }
      // A child-supplied identity/config packet is not a host bootstrap API call.
      parent.postMessage({ lab: 'forged-bootstrap', slot: 'B', storageAllowed: true }, HOST);
    }
  } catch (error) {
    record('failure', {
      action: name,
      detail: error instanceof Error ? error.message : String(error),
    });
    status.textContent = `${name} failed`;
  }
};
window.addEventListener('message', (event) => {
  if (event.origin === HOST && event.source === parent && event.data?.lab === 'multi-command') {
    void action(event.data.name);
  }
});
try {
  const handshake = await client.initialize();
  identity = handshake.miniApp.id;
  record('initialized', { id: identity, grants: handshake.grantedScopes, origin: location.origin });
  record('profile', await client.call('profile.get'));
  if (handshake.grantedScopes.includes('storage')) {
    // Reuse the same key on both apps, but seed only a missing value so reload tests preserve state.
    const stored = await client.call('storage.get', { key: 'same-key' });
    if (
      typeof stored === 'object' &&
      stored !== null &&
      'value' in stored &&
      stored.value === null
    ) {
      await client.call('storage.set', { key: 'same-key', value: identity });
    }
    record('storage', await client.call('storage.get', { key: 'same-key' }));
  }
  status.textContent = `Ready: ${identity} at ${location.origin}`;
} catch (error) {
  record('startup failure', error instanceof Error ? error.message : String(error));
}
