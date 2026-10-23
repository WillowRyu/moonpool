/** T09 / SPEC §4.2, §6.1 — name syntax precedes params, session, and permissions. */
import { createHost, type StorageProvider } from '@moonpool/host';
import { ERROR_CODES, type JsonValue } from '@moonpool/protocol';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { createLinkedTransports, flush } from './helpers/memory-transport';

const UNKNOWN_VALID = [
  { method: 'profile.readDisplayName', grants: ['profile'], code: ERROR_CODES.METHOD_NOT_FOUND },
  { method: 'storage.readValue', grants: ['storage'], code: ERROR_CODES.METHOD_NOT_FOUND },
  { method: 'profile.readDisplayName', grants: [], code: ERROR_CODES.PERMISSION_DENIED },
  { method: 'storage.readValue', grants: ['profile'], code: ERROR_CODES.PERMISSION_DENIED },
  { method: 'portal.unknown', grants: [], code: ERROR_CODES.METHOD_NOT_FOUND },
  { method: 'portalX.ping', grants: [], code: ERROR_CODES.PERMISSION_DENIED },
];

const connections: Array<ReturnType<typeof createLinkedTransports>> = [];

afterEach(() => {
  for (const bridge of connections.splice(0)) {
    bridge.a.close();
    bridge.b.close();
  }
});

function setup(grants: string[] = ['profile', 'storage']) {
  const bridge = createLinkedTransports();
  connections.push(bridge);
  const received: JsonValue[] = [];
  bridge.a.onMessage((message) => received.push(message));
  const profile = { get: vi.fn(async () => ({ displayName: 'Method test user' })) };
  const storage = {
    get: vi.fn<StorageProvider['get']>(async () => null),
    set: vi.fn<StorageProvider['set']>(async () => {}),
    delete: vi.fn<StorageProvider['delete']>(async () => {}),
  };
  createHost({
    hostInfo: { name: 'method-test-host', version: '0.1.0', platform: 'browser' },
    manifest: {
      manifestVersion: 1,
      id: 'com.example.methods',
      name: 'Method test',
      version: '1.0.0',
      entry: 'index.html',
      protocolVersion: '0.1',
      permissions: ['profile', 'storage'],
    },
    grantedScopes: grants,
    environment: { locale: 'en', colorScheme: 'light' },
    capabilities: { profile, storage },
  }).connect(bridge.b);
  return { send: bridge.a.send, received, profile, storage };
}

async function initialize(bridge: ReturnType<typeof setup>) {
  bridge.send({
    jsonrpc: '2.0',
    id: 1,
    method: 'portal.initialize',
    params: { protocolVersion: '0.1' },
  });
  await flush();
  expect(bridge.received).toEqual([expect.objectContaining({ result: expect.any(Object) })]);
  bridge.received.length = 0;
}

describe('SPEC §5 / §9.3 — valid method names keep their existing dispatch behavior', () => {
  it.each(UNKNOWN_VALID)('keeps $method behind initialization', async ({ method, grants }) => {
    const bridge = setup(grants);
    bridge.send({ jsonrpc: '2.0', id: 2, method, params: {} });
    await flush();

    expect(bridge.received).toEqual([
      expect.objectContaining({
        id: 2,
        error: expect.objectContaining({ code: ERROR_CODES.NOT_INITIALIZED }),
      }),
    ]);
    expect(bridge.profile.get).not.toHaveBeenCalled();
  });

  it.each(UNKNOWN_VALID)(
    'retains code $code for $method with grants $grants',
    async ({ method, grants, code }) => {
      const bridge = setup(grants);
      await initialize(bridge);

      bridge.send({ jsonrpc: '2.0', id: 2, method, params: { unused: true } });
      await flush();

      expect(bridge.received).toEqual([
        expect.objectContaining({ id: 2, error: expect.objectContaining({ code }) }),
      ]);
      expect(bridge.profile.get).not.toHaveBeenCalled();
    },
  );

  it('continues to invoke a known granted method', async () => {
    const bridge = setup(['profile']);
    await initialize(bridge);
    bridge.send({ jsonrpc: '2.0', id: 2, method: 'profile.get', params: {} });
    await flush();

    expect(bridge.received).toEqual([
      { jsonrpc: '2.0', id: 2, result: { displayName: 'Method test user' } },
    ]);
    expect(bridge.profile.get).toHaveBeenCalledOnce();
  });

  it('does not treat a longer valid action as a repeat handshake', async () => {
    const bridge = setup(['profile']);
    await initialize(bridge);
    bridge.send({ jsonrpc: '2.0', id: 2, method: 'portal.initializeAgain', params: {} });
    bridge.send({ jsonrpc: '2.0', id: 3, method: 'profile.get', params: {} });
    await flush();

    expect(bridge.received).toEqual([
      expect.objectContaining({
        id: 2,
        error: expect.objectContaining({ code: ERROR_CODES.METHOD_NOT_FOUND }),
      }),
      { jsonrpc: '2.0', id: 3, result: { displayName: 'Method test user' } },
    ]);
  });
});

const STATES = [
  { label: 'before initialization', initialized: false, grants: [] },
  { label: 'initialized without scoped grants', initialized: true, grants: [] },
  { label: 'initialized with scoped grants', initialized: true, grants: ['profile', 'storage'] },
];

describe.each(STATES)('SPEC §4.2 / §6.1 — method syntax $label', ({ initialized, grants }) => {
  it.each([
    '',
    'profile',
    'Profile.get',
    'profile.Get',
    'profile..get',
    'profile.get.extra',
    'profile.get_name',
    'profile.get\n',
    'storage.set ',
    'storage.delete\r\n',
    'portal.initialize ',
    'portal.initialize.extra',
  ])('rejects %j before invoking any provider', async (method) => {
    const bridge = setup(grants);
    if (initialized) {
      await initialize(bridge);
    }

    bridge.send({ jsonrpc: '2.0', id: 2, method, params: {} });
    await flush();

    expect(bridge.received).toEqual([
      {
        jsonrpc: '2.0',
        id: 2,
        error: { code: ERROR_CODES.INVALID_REQUEST, message: expect.any(String) },
      },
    ]);
    expect(bridge.profile.get).not.toHaveBeenCalled();
    expect(bridge.storage.get).not.toHaveBeenCalled();
    expect(bridge.storage.set).not.toHaveBeenCalled();
    expect(bridge.storage.delete).not.toHaveBeenCalled();
  });

  const INVALID_PARAMS: Array<{ params: JsonValue }> = [
    { params: [] },
    { params: 0 },
    { params: null },
  ];
  it.each(INVALID_PARAMS)(
    'rejects the malformed name before params $params',
    async ({ params }) => {
      const bridge = setup(grants);
      if (initialized) {
        await initialize(bridge);
      }
      bridge.send({ jsonrpc: '2.0', id: 2, method: 'profile..get', params });
      await flush();
      expect(bridge.received).toEqual([
        expect.objectContaining({
          id: 2,
          error: expect.objectContaining({ code: ERROR_CODES.INVALID_REQUEST }),
        }),
      ]);
    },
  );
});

describe('SPEC §4.2 / §5.1 — rejected syntax leaves the connection usable', () => {
  it('does not reset a live connection for a malformed initialize spelling', async () => {
    const bridge = setup(['profile']);
    await initialize(bridge);

    bridge.send({
      jsonrpc: '2.0',
      id: 2,
      method: 'portal.initialize ',
      params: { protocolVersion: 'unsupported' },
    });
    bridge.send({ jsonrpc: '2.0', id: 3, method: 'profile.get', params: {} });
    await flush();

    expect(bridge.received).toEqual([
      expect.objectContaining({
        id: 2,
        error: expect.objectContaining({ code: ERROR_CODES.INVALID_REQUEST }),
      }),
      { jsonrpc: '2.0', id: 3, result: { displayName: 'Method test user' } },
    ]);
    expect(bridge.profile.get).toHaveBeenCalledOnce();
  });

  it('still permits a valid handshake after rejecting a malformed name', async () => {
    const bridge = setup();
    bridge.send({ jsonrpc: '2.0', id: 1, method: 'Portal.initialize', params: {} });
    await flush();
    expect(bridge.received).toEqual([
      expect.objectContaining({
        id: 1,
        error: expect.objectContaining({ code: ERROR_CODES.INVALID_REQUEST }),
      }),
    ]);
    bridge.received.length = 0;
    await initialize(bridge);
    bridge.send({ jsonrpc: '2.0', id: 2, method: 'portal.ping', params: {} });
    await flush();
    expect(bridge.received).toEqual([{ jsonrpc: '2.0', id: 2, result: { pong: true } }]);
  });

  it('does not reply to a standalone notification with a malformed name', async () => {
    const bridge = setup();
    bridge.send({ jsonrpc: '2.0', method: 'Profile..get', params: {} });
    await flush();
    expect(bridge.received).toEqual([]);
    expect(bridge.profile.get).not.toHaveBeenCalled();
  });

  it('keeps the batch-level null id when a member has a malformed name', async () => {
    const bridge = setup();
    bridge.send([{ jsonrpc: '2.0', id: 7, method: 'profile..get', params: {} }]);
    await flush();
    expect(bridge.received).toEqual([
      expect.objectContaining({
        id: null,
        error: expect.objectContaining({ code: ERROR_CODES.INVALID_REQUEST }),
      }),
    ]);
  });

  it('does not echo the untrusted method text in syntax errors', async () => {
    const bridge = setup(['profile']);
    await initialize(bridge);
    const marker = 'private-method-marker';
    bridge.send({ jsonrpc: '2.0', id: 2, method: `profile.${marker}`, params: {} });
    await flush();
    const response = bridge.received[0];
    expect(response).toEqual(
      expect.objectContaining({
        error: expect.objectContaining({ code: ERROR_CODES.INVALID_REQUEST }),
      }),
    );
    expect(JSON.stringify(response)).not.toContain(marker);
  });
});
