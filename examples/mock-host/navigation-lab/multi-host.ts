import { isJsonObject, isJsonValue, type JsonValue } from '../../../packages/protocol/src/index';

const HOST = 'http://127.0.0.1:5373';
type Slot = 'A' | 'B';
type WrapperApi = {
  command(name: string): void;
  dispose(reason: string): void;
  notify(changes: unknown): Promise<void>;
};
type RecordState = {
  slot: Slot;
  frame: HTMLIFrameElement;
  expectedURL: string;
  generation: number;
  document: Document | null;
  api: WrapperApi | null;
  storageAllowed: boolean;
  snapshot: Record<string, JsonValue>;
};
const root = document.querySelector<HTMLElement>('#app');
if (root === null) {
  throw new Error('missing coordinator root');
}
root.innerHTML = `
  <h1>Multi-Portal wrapper observations</h1><p>Manual candidate only. SDK and SPEC are unchanged.</p>
  <p id="browser"></p><div class="controls">
  <button id="reset">Reset both</button><button id="footprint">Inspect frame footprint</button>
  <button id="a-profile">A profile</button><button id="b-profile">B profile</button>
  <button id="a-reload">A inner reload</button><button id="a-storage">A read storage</button><button id="b-storage">B read storage</button>
  <button id="a-to-b">A navigate to B</button><button id="a-foreign">A navigate foreign</button>
  <button id="hold-b">Hold next B profile</button><button id="release-b">Release B profile</button>
  <button id="hold-a">Hold next A profile</button><button id="release-a">Release A after revocation</button>
  <button id="a-bootstrap">A attempt host API access</button><button id="switch-a">Switch A wrapper URL to B</button>
  <button id="restart-a">Restart A</button><button id="stale-a">Try stale A bootstrap</button><button id="restricted-b">Restart B profile-only</button>
  <button id="cross-realm">B notification from outer object</button><button id="local-realm">B notification inside wrapper</button>
  <button id="forge-b">Forge B reply from outer host</button>
  <button id="reload-wrapper-a">Reload A wrapper at same URL</button>
  </div><div class="portals"><section><h2>Portal A</h2><p id="a-state"></p><div id="a-frame"></div></section>
  <section><h2>Portal B</h2><p id="b-state"></p><div id="b-frame"></div></section></div>
  <pre id="summary"></pre><pre id="log"></pre>`;
const output = root.querySelector<HTMLElement>('#log');
const summary = root.querySelector<HTMLElement>('#summary');
const browser = root.querySelector<HTMLElement>('#browser');
if (output === null || summary === null || browser === null) {
  throw new Error('missing output');
}
browser.textContent = `UA: ${navigator.userAgent}`;
const records = new Map<Slot, RecordState>();
const events: Array<Record<string, unknown>> = [];
let generation = 0;
let staleA: RecordState | undefined;
const log = (kind: string, fields: Record<string, unknown> = {}) => {
  events.push({ n: events.length + 1, kind, ...fields });
  output.textContent = events.map((event) => JSON.stringify(event)).join('\n');
};
const isApi = (value: unknown): value is WrapperApi =>
  typeof value === 'object' &&
  value !== null &&
  'command' in value &&
  typeof value.command === 'function' &&
  'dispose' in value &&
  typeof value.dispose === 'function' &&
  'notify' in value &&
  typeof value.notify === 'function';
const find = (source: unknown) =>
  [...records.values()].find((entry) => entry.frame.contentWindow === source);
const currentDocument = (entry: RecordState): Document | null => {
  try {
    // Unlike the untrusted guest, the served wrapper is same-origin with its coordinator.
    if (entry.frame.contentWindow?.location.href !== entry.expectedURL) {
      return null;
    }
    return entry.frame.contentDocument;
  } catch {
    return null;
  }
};
const update = () => {
  for (const entry of records.values()) {
    const label = root.querySelector(`#${entry.slot.toLowerCase()}-state`);
    if (label !== null) {
      label.textContent = JSON.stringify(entry.snapshot);
    }
  }
  let innerFrames = 0;
  for (const entry of records.values()) {
    if (entry.frame.isConnected) {
      innerFrames += entry.frame.contentDocument?.querySelectorAll('iframe').length ?? 0;
    }
  }
  summary.textContent = `wrappers=${[...records.values()].filter((entry) => entry.frame.isConnected).length} | live guest frames=${innerFrames}`;
};

// Lab-only host APIs: callers must match the actual host-owned frame AND its bound Document.
Reflect.set(
  window,
  'multiLabBootstrap',
  (source: unknown, document: unknown, api: unknown): string | undefined => {
    const entry = find(source);
    if (entry === undefined || !entry.frame.isConnected || !isApi(api)) {
      log('bootstrap-rejected', { reason: 'unknown source/API' });
      return;
    }
    const actual = currentDocument(entry);
    if (
      actual === null ||
      actual !== document ||
      (entry.document !== null && entry.document !== actual)
    ) {
      log('bootstrap-rejected', {
        slot: entry.slot,
        reason: 'URL/Document mismatch',
        sameURL: actual !== null,
        sameDocument: entry.document === actual,
      });
      entry.api?.dispose('wrapper binding rejected');
      entry.snapshot = { status: 'wrapper rejected' };
      entry.frame.remove();
      update();
      return;
    }
    if (entry.api !== null) {
      log('bootstrap-rejected', { slot: entry.slot, reason: 'already bound' });
      return;
    }
    entry.document = actual;
    entry.api = api;
    log('bootstrap-bound', { slot: entry.slot, generation: entry.generation });
    // Identity and grants come from this registry, never from guest IDs or wrapper query claims.
    return JSON.stringify({
      slot: entry.slot,
      origin: entry.slot === 'A' ? 'http://127.0.0.1:5374' : 'http://127.0.0.1:5375',
      storageAllowed: entry.storageAllowed,
    });
  },
);
Reflect.set(window, 'multiLabReport', (source: unknown, document: unknown, text: unknown) => {
  const entry = find(source);
  if (
    entry === undefined ||
    entry.document !== document ||
    currentDocument(entry) !== document ||
    typeof text !== 'string'
  ) {
    return;
  }
  const value: unknown = JSON.parse(text);
  if (!isJsonValue(value) || !isJsonObject(value)) {
    return;
  }
  entry.snapshot = value;
  update();
});

const start = (slot: Slot, storageAllowed = true) => {
  const old = records.get(slot);
  if (old !== undefined) {
    old.api?.dispose('coordinator restart');
    if (slot === 'A') {
      staleA = old;
    }
    old.frame.remove();
  }
  const frame = document.createElement('iframe');
  frame.title = `Trusted wrapper ${slot}`;
  const expectedURL = `${HOST}/multi-wrapper-${slot.toLowerCase()}.html?generation=${++generation}`;
  const entry: RecordState = {
    slot,
    frame,
    expectedURL,
    generation,
    document: null,
    api: null,
    storageAllowed,
    snapshot: { status: 'starting' },
  };
  records.set(slot, entry);
  frame.src = expectedURL;
  frame.addEventListener('load', () => {
    if (records.get(slot) !== entry) {
      return;
    }
    const actual = currentDocument(entry);
    if (actual === null || (entry.document !== null && entry.document !== actual)) {
      log('wrapper-load-rejected', { slot });
      entry.snapshot = { status: 'wrapper rejected' };
      frame.remove();
      update();
    }
  });
  const container = root.querySelector(`#${slot.toLowerCase()}-frame`);
  if (container === null) {
    throw new Error('missing wrapper container');
  }
  container.replaceChildren(frame);
  log('wrapper-created', { slot, generation, storageAllowed });
  update();
};
const command = (slot: Slot, name: string) => {
  log('command', { slot, name });
  records.get(slot)?.api?.command(name);
};
const bind = (id: string, action: () => void) =>
  root.querySelector(`#${id}`)?.addEventListener('click', action);
bind('reset', () => {
  start('A');
  start('B');
});
bind('footprint', () => {
  update();
  log('footprint', { value: summary.textContent });
});
const slots: Slot[] = ['A', 'B'];
for (const slot of slots) {
  bind(`${slot.toLowerCase()}-profile`, () => command(slot, 'profile'));
  bind(`${slot.toLowerCase()}-storage`, () => command(slot, 'storage'));
}
bind('a-reload', () => command('A', 'reload'));
bind('a-to-b', () => command('A', 'to-b'));
bind('a-foreign', () => command('A', 'foreign'));
bind('hold-b', () => command('B', 'hold'));
bind('hold-a', () => command('A', 'hold'));
bind('release-b', () => command('B', 'release'));
bind('release-a', () => command('A', 'release'));
bind('a-bootstrap', () => command('A', 'bootstrap-access'));
bind('switch-a', () => {
  const entry = records.get('A');
  if (entry !== undefined) {
    entry.frame.src = `${HOST}/multi-wrapper-b.html?generation=${entry.generation}`;
  }
});
bind('restart-a', () => start('A'));
bind('stale-a', () => {
  const attempt = Reflect.get(window, 'multiLabBootstrap');
  if (typeof attempt === 'function' && staleA !== undefined) {
    const result: unknown = attempt(staleA.frame.contentWindow, staleA.document, staleA.api);
    log('stale-bootstrap-result', { returnedConfig: result !== undefined });
  }
});
bind('restricted-b', () => start('B', false));
bind('cross-realm', () => {
  const entry = records.get('B');
  if (entry?.api !== null && entry?.api !== undefined) {
    const changes = { colorScheme: 'dark', locale: 'ko-KR' };
    log('outer-notify-attempt', { changes });
    void entry.api.notify(changes).then(
      () => log('outer-notify-ok'),
      (error: unknown) =>
        log('outer-notify-failed', {
          error: error instanceof Error ? error.message : String(error),
        }),
    );
  }
});
bind('local-realm', () => command('B', 'notify-local'));
bind('forge-b', () => {
  const entry = records.get('B');
  const inner = entry?.frame.contentDocument?.querySelector('iframe');
  const id = entry?.snapshot.lastProfileId;
  if (
    inner?.contentWindow !== null &&
    inner?.contentWindow !== undefined &&
    typeof id === 'number'
  ) {
    // Same host origin, deliberately WRONG source window: the guest must still reject this.
    inner.contentWindow.postMessage(
      { jsonrpc: '2.0', id, result: { displayName: 'FORGED OUTER REPLY' } },
      'http://127.0.0.1:5375',
    );
    log('outer-forged-reply', { id });
  }
});
bind('reload-wrapper-a', () => {
  records.get('A')?.frame.contentWindow?.location.reload();
});
start('A');
start('B');
