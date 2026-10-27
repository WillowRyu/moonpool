/** SPEC §4.1 — reject the whole top-level array without dispatching its members. */
import { createHost, type StorageProvider } from '@moonpool/host';
import { ERROR_CODES, type JsonValue, type MiniAppManifest } from '@moonpool/protocol';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { createLinkedTransports, flush } from '../../../test-support/memory-transport';

const MANIFEST: MiniAppManifest = {
  manifestVersion: 1,
  id: 'com.example.batch',
  name: 'Batch test',
  version: '1.0.0',
  entry: 'index.html',
  protocolVersion: '0.1',
  permissions: ['profile', 'storage'],
};

const INITIALIZE = {
  jsonrpc: '2.0',
  id: 1,
  method: 'portal.initialize',
  params: { protocolVersion: '0.1' },
};

const BATCHES: Array<{ label: string; frame: JsonValue[] }> = [
  { label: 'an empty array', frame: [] },
  { label: 'one request', frame: [{ jsonrpc: '2.0', id: 42, method: 'portal.ping' }] },
  {
    label: 'multiple capability requests, including writes',
    frame: [
      { jsonrpc: '2.0', id: 2, method: 'profile.get' },
      { jsonrpc: '2.0', id: 3, method: 'storage.get', params: { key: 'settings' } },
      { jsonrpc: '2.0', id: 4, method: 'storage.set', params: { key: 'settings', value: 'bad' } },
      { jsonrpc: '2.0', id: 5, method: 'storage.delete', params: { key: 'settings' } },
    ],
  },
  {
    label: 'only notifications',
    frame: [
      { jsonrpc: '2.0', method: 'portal.ping' },
      { jsonrpc: '2.0', method: 'profile.get' },
    ],
  },
  { label: 'invalid members', frame: [null, false, 0, 'request', {}] },
  { label: 'a nested array', frame: [[{ jsonrpc: '2.0', id: 2, method: 'profile.get' }]] },
  { label: 'an initialization request', frame: [INITIALIZE] },
  {
    label: 'an unsupported-version repeat handshake',
    frame: [{ ...INITIALIZE, params: { protocolVersion: 'unsupported' } }],
  },
];

const connections: Array<ReturnType<typeof createLinkedTransports>> = [];

afterEach(() => {
  for (const bridge of connections.splice(0)) {
    bridge.a.close();
    bridge.b.close();
  }
});

function setup() {
  const bridge = createLinkedTransports();
  connections.push(bridge);
  const profile = { get: vi.fn(async () => ({ displayName: 'Batch test user' })) };
  const storage = {
    get: vi.fn<StorageProvider['get']>(async () => null),
    set: vi.fn<StorageProvider['set']>(async () => {}),
    delete: vi.fn<StorageProvider['delete']>(async () => {}),
  };
  const received: JsonValue[] = [];
  bridge.a.onMessage((message) => received.push(message));
  createHost({
    hostInfo: { name: 'batch-test-host', version: '0.1.0', platform: 'browser' },
    manifest: MANIFEST,
    grantedScopes: ['profile', 'storage'],
    environment: { locale: 'en', colorScheme: 'light' },
    capabilities: { profile, storage },
  }).connect(bridge.b);
  return { send: bridge.a.send, received, profile, storage };
}

async function initialize(bridge: ReturnType<typeof setup>) {
  bridge.send(INITIALIZE);
  await flush();
  expect(bridge.received).toEqual([
    expect.objectContaining({
      result: expect.objectContaining({ grantedScopes: ['profile', 'storage'] }),
    }),
  ]);
  bridge.received.length = 0;
}

describe.each([
  { state: 'before initialization', initialized: false },
  { state: 'after initialization', initialized: true },
])('SPEC §4.1 — batches $state', ({ initialized }) => {
  it.each(BATCHES)('rejects $label with one uncorrelated error', async ({ frame }) => {
    const bridge = setup();
    if (initialized) {
      await initialize(bridge);
    }

    bridge.send(frame);
    await flush();

    expect(bridge.received).toEqual([
      {
        jsonrpc: '2.0',
        id: null,
        error: { code: ERROR_CODES.INVALID_REQUEST, message: expect.any(String) },
      },
    ]);
    expect(bridge.profile.get).not.toHaveBeenCalled();
    expect(bridge.storage.get).not.toHaveBeenCalled();
    expect(bridge.storage.set).not.toHaveBeenCalled();
    expect(bridge.storage.delete).not.toHaveBeenCalled();
  });
});

describe('SPEC §4.1 — rejecting a batch leaves the connection state intact', () => {
  it('does not initialize from a member of a rejected batch', async () => {
    const bridge = setup();

    bridge.send([INITIALIZE]);
    bridge.send({ jsonrpc: '2.0', id: 9, method: 'portal.ping' });
    await flush();

    expect(bridge.received).toEqual([
      expect.objectContaining({
        id: null,
        error: expect.objectContaining({ code: ERROR_CODES.INVALID_REQUEST }),
      }),
      expect.objectContaining({
        id: 9,
        error: expect.objectContaining({ code: ERROR_CODES.NOT_INITIALIZED }),
      }),
    ]);
  });

  it('does not reset an initialized connection from a batch member', async () => {
    const bridge = setup();
    await initialize(bridge);

    bridge.send([{ ...INITIALIZE, params: { protocolVersion: 'unsupported' } }]);
    bridge.send({ jsonrpc: '2.0', id: 3, method: 'profile.get' });
    await flush();

    expect(bridge.received).toEqual([
      expect.objectContaining({
        id: null,
        error: expect.objectContaining({ code: ERROR_CODES.INVALID_REQUEST }),
      }),
      { jsonrpc: '2.0', id: 3, result: { displayName: 'Batch test user' } },
    ]);
    expect(bridge.profile.get).toHaveBeenCalledOnce();
  });

  it('still leaves a standalone notification unanswered', async () => {
    const bridge = setup();
    bridge.send({ jsonrpc: '2.0', method: 'portal.ping' });
    await flush();
    expect(bridge.received).toEqual([]);
  });

  it('still accepts an array inside a normal storage.set value', async () => {
    const bridge = setup();
    await initialize(bridge);
    const value = [null, false, 0, ''];

    bridge.send({ jsonrpc: '2.0', id: 2, method: 'storage.set', params: { key: 'array', value } });
    await flush();

    expect(bridge.received).toEqual([{ jsonrpc: '2.0', id: 2, result: {} }]);
    expect(bridge.storage.set).toHaveBeenCalledExactlyOnceWith(MANIFEST.id, 'array', value);
  });
});
