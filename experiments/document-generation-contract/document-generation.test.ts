/**
 * ADR 0024 / SPEC §11: real-kernel evidence before the versioned wire contract.
 * Three safety assertions must fail under current 0.1; controls must pass.
 * No new wire field or alternate dispatcher is invented by this fixture.
 */
import { describe, expect, it } from 'vitest';
import { createClient, type MoonpoolClient } from '../../packages/client/src/index';
import { createHost } from '../../packages/host/src/index';
import {
  ERROR_CODES,
  isJsonObject,
  type JsonValue,
  PROTOCOL_VERSION,
  type Transport,
} from '../../packages/protocol/src/index';
import { createLinkedTransports, flush } from '../../test-support/memory-transport';

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((settle) => {
    resolve = (value) => settle(value);
  });
  return { promise, resolve };
}

function setup({ holdInitializationReplies = false } = {}) {
  const link = createLinkedTransports();
  const oldRead = deferred<JsonValue>();
  const newRead = deferred<JsonValue>();
  const writeReady = deferred<void>();
  const clients: MoonpoolClient[] = [];
  const values = new Map<string, JsonValue>();
  const reads: string[] = [];
  const writes: string[] = [];
  const requests: JsonValue[][] = [];
  const initializationReplies: JsonValue[] = [];
  const environment = { locale: 'en', colorScheme: 'light' as const };
  const hostTransport: Transport = {
    ...link.b,
    send(message) {
      if (
        holdInitializationReplies &&
        isJsonObject(message) &&
        isJsonObject(message.result) &&
        typeof message.result.protocolVersion === 'string'
      ) {
        initializationReplies.push(message);
        return;
      }
      link.b.send(message);
    },
  };

  createHost({
    hostInfo: { name: 'document-probe', version: '0.0.0', platform: 'browser' },
    manifest: {
      manifestVersion: 1,
      id: 'com.example.document-probe',
      name: 'Document probe',
      version: '1.0.0',
      entry: 'index.html',
      protocolVersion: PROTOCOL_VERSION,
      permissions: ['storage'],
    },
    grantedScopes: ['storage'],
    environment,
    capabilities: {
      storage: {
        async get(app, key) {
          expect(app).toBe('com.example.document-probe');
          reads.push(key);
          switch (key) {
            case 'old':
              return oldRead.promise;
            case 'new':
              return newRead.promise;
            default:
              return values.get(key) ?? null;
          }
        },
        async set(app, key, value) {
          expect(app).toBe('com.example.document-probe');
          writes.push(key);
          await writeReady.promise;
          values.set(key, value);
        },
        async delete() {
          throw new Error('unexpected storage.delete');
        },
      },
    },
  }).connect(hostTransport);

  function openDocument() {
    let closed = false;
    const sent: JsonValue[] = [];
    requests.push(sent);
    // Each document owns a terminal facade. The physical transport remains open,
    // so a host result targets the receiver subscribed by the replacement page.
    const transport: Transport = {
      send(message) {
        if (!closed) {
          sent.push(message);
          link.a.send(message);
        }
      },
      onMessage(handler) {
        return link.a.onMessage((message) => {
          if (!closed) {
            handler(message);
          }
        });
      },
      close() {
        closed = true;
      },
    };
    const client = createClient({ transport });
    clients.push(client);
    return client;
  }

  async function dispose() {
    for (const client of clients) {
      client.close();
    }
    oldRead.resolve('old draft');
    newRead.resolve('new draft');
    writeReady.resolve();
    link.a.close();
    link.b.close();
    await flush();
  }

  function releaseInitialization(index: number) {
    const message = initializationReplies[index];
    if (message === undefined) {
      throw new Error('initialization reply was not captured');
    }
    link.b.send(message);
  }

  return {
    openDocument,
    oldRead,
    newRead,
    writeReady,
    reads,
    writes,
    requests,
    environment,
    initializationReplies,
    releaseInitialization,
    dispose,
  };
}

async function startOldRead(probe: ReturnType<typeof setup>) {
  const a = probe.openDocument();
  await a.initialize();
  const oldOutcome = a.call('storage.get', { key: 'old' }).catch((error: unknown) => error);
  await flush();
  expect(probe.reads).toEqual(['old']);
  expect(probe.requests[0]).toMatchObject([{ id: 1 }, { id: 2 }]);
  a.close();
  await expect(oldOutcome).resolves.toMatchObject({ code: ERROR_CODES.CONNECTION_CLOSED });
}

describe('document-lifetime controls on the current public kernel', () => {
  it('ignores the old response while the new document has no matching pending id', async () => {
    const probe = setup();
    try {
      await startOldRead(probe);
      const b = probe.openDocument();
      await b.initialize();
      probe.oldRead.resolve('old draft');
      await flush();
      const current = b.call('storage.get', { key: 'new' });
      await flush();
      probe.newRead.resolve('new draft');
      await expect(current).resolves.toEqual({ value: 'new draft' });
    } finally {
      await probe.dispose();
    }
  });

  it('preserves grants and an already-dispatched write across document replacement', async () => {
    const probe = setup();
    try {
      const a = probe.openDocument();
      await a.initialize();
      const oldOutcome = a
        .call('storage.set', { key: 'saved', value: 'committed by A' })
        .catch((error: unknown) => error);
      await flush();
      expect(probe.writes).toEqual(['saved']);
      a.close();
      await expect(oldOutcome).resolves.toMatchObject({ code: ERROR_CODES.CONNECTION_CLOSED });
      const b = probe.openDocument();
      const initialized = await b.initialize();
      expect(initialized.grantedScopes).toEqual(['storage']);
      probe.writeReady.resolve();
      await flush();
      await expect(b.call('storage.get', { key: 'saved' })).resolves.toEqual({
        value: 'committed by A',
      });
    } finally {
      await probe.dispose();
    }
  });
});

describe('accepted generation direction — expected RED under protocol 0.1', () => {
  it('does not let an old initialization response initialize the replacement document', async () => {
    const probe = setup({ holdInitializationReplies: true });
    try {
      probe.environment.locale = 'en-US';
      const a = probe.openDocument();
      const oldOutcome = a.initialize().catch((error: unknown) => error);
      await flush();
      expect(probe.initializationReplies).toHaveLength(1);
      a.close();
      await expect(oldOutcome).resolves.toMatchObject({ code: ERROR_CODES.CONNECTION_CLOSED });
      probe.environment.locale = 'ko-KR';
      const b = probe.openDocument();
      const initialized = b.initialize();
      await flush();
      expect(probe.initializationReplies).toHaveLength(2);
      expect(probe.requests).toMatchObject([[{ id: 1 }], [{ id: 1 }]]);
      probe.releaseInitialization(0);
      await flush();
      probe.releaseInitialization(1);
      await expect(initialized).resolves.toMatchObject({
        environment: { locale: 'ko-KR' },
      });
    } finally {
      await probe.dispose();
    }
  });

  it('does not let A request 2 satisfy B request 2', async () => {
    const probe = setup();
    try {
      await startOldRead(probe);
      const b = probe.openDocument();
      await b.initialize();
      const current = b.call('storage.get', { key: 'new' });
      await flush();
      expect(probe.reads).toEqual(['old', 'new']);
      expect(probe.requests).toMatchObject([
        [{ id: 1 }, { id: 2 }],
        [{ id: 1 }, { id: 2 }],
      ]);
      probe.oldRead.resolve('old draft');
      await flush();
      probe.newRead.resolve('new draft');
      await expect(current).resolves.toEqual({ value: 'new draft' });
    } finally {
      await probe.dispose();
    }
  });

  it('does not let the first A request 2 satisfy a fresh A request 2 after A→B→A', async () => {
    const probe = setup();
    try {
      await startOldRead(probe);
      const b = probe.openDocument();
      await b.initialize();
      b.close();
      const freshA = probe.openDocument();
      await freshA.initialize();
      const current = freshA.call('storage.get', { key: 'new' });
      await flush();
      expect(probe.reads).toEqual(['old', 'new']);
      expect(probe.requests).toMatchObject([
        [{ id: 1 }, { id: 2 }],
        [{ id: 1 }],
        [{ id: 1 }, { id: 2 }],
      ]);
      probe.oldRead.resolve('old draft');
      await flush();
      probe.newRead.resolve('new draft');
      await expect(current).resolves.toEqual({ value: 'new draft' });
    } finally {
      await probe.dispose();
    }
  });
});
