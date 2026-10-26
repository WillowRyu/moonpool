import { createClient } from '../../../packages/client/src/index';
import { createIframeTransport } from '../../../packages/transport-iframe/src/index';

const HOST = 'http://127.0.0.1:5273';
const ALLOWED = 'http://127.0.0.1:5274';
const FOREIGN = 'http://127.0.0.1:5275';
const params = new URLSearchParams(location.search);
const run = params.get('run') ?? '';
let nextProbeId = params.get('mode') === 'resume' ? 101 : 3;
const status = document.querySelector<HTMLElement>('#status');
const events = document.querySelector<HTMLElement>('#events');
if (status === null || events === null) {
  throw new Error('missing probe output');
}
const transport = createIframeTransport({ peerWindow: parent, peerOrigin: HOST });
transport.onMessage((message) => {
  events.textContent += `${JSON.stringify(message)}\n`;
});
window.addEventListener('hashchange', () => {
  parent.postMessage({ lab: 'hashchange', href: location.href }, HOST);
});
window.addEventListener('message', (event) => {
  if (event.origin !== HOST || event.source !== parent) {
    return;
  }
  if (event.data?.lab === 'marker') {
    parent.postMessage({ lab: 'marker-received', href: location.href }, HOST);
  }
  if (event.data?.lab !== 'navigation') {
    return;
  }
  switch (event.data.command) {
    case 'profile':
      transport.send({ jsonrpc: '2.0', id: nextProbeId++, method: 'profile.get' });
      break;
    case 'same':
      location.assign(`${ALLOWED}/probe.html?run=${run}&page=second`);
      break;
    case 'reload':
      location.reload();
      break;
    case 'hash':
      location.hash = `fragment-${Date.now()}`;
      break;
    case 'foreign':
      location.assign(`${FOREIGN}/foreign.html?run=${run}`);
      break;
    case 'bounce':
      location.assign(`${FOREIGN}/bounce.html?run=${run}`);
      break;
    case 'redirect':
      location.assign(`${ALLOWED}/redirect?run=${run}`);
      break;
    case 'form': {
      const form = document.createElement('form');
      form.action = `${FOREIGN}/foreign.html`;
      const field = document.createElement('input');
      field.name = 'run';
      field.value = run;
      form.append(field);
      document.body.append(form);
      form.submit();
      break;
    }
  }
});
if (params.get('mode') === 'intruder') {
  status.textContent = 'Other allowed-origin frame: raw profile.get id 900';
  transport.send({ jsonrpc: '2.0', id: 900, method: 'profile.get' });
} else if (params.get('mode') === 'resume') {
  status.textContent = 'Returned document: profile.get id 100 WITHOUT initialize';
  transport.send({ jsonrpc: '2.0', id: 100, method: 'profile.get' });
} else {
  const client = createClient({ transport, timeoutMs: 1000 });
  try {
    await client.initialize();
    const profile = await client.call('profile.get');
    status.textContent = `Initialized and read profile: ${JSON.stringify(profile)}`;
  } catch (error) {
    status.textContent = error instanceof Error ? error.message : 'request failed';
  }
}
