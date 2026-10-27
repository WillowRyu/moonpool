/** T14 — existing request gates also protect Portal dismissal. */
import { createHost } from '@moonpool/host';
import { ERROR_CODES, type JsonValue, type Transport } from '@moonpool/protocol';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { createLinkedTransports, flush } from '../../../test-support/memory-transport';
import { createClient } from '../../client/src/index';

afterEach(() => vi.restoreAllMocks());

function setup(onCloseRequested?: (reason?: string) => Promise<void>) {
  let receive: ((message: JsonValue) => void) | undefined;
  const replies: JsonValue[] = [];
  const send = vi.fn((message: JsonValue) => {
    replies.push(message);
  });
  const close = vi.fn(() => {});
  const transport: Transport = {
    send,
    close,
    onMessage(handler) {
      receive = handler;
      return () => {
        receive = undefined;
      };
    },
  };
  const host = createHost({
    hostInfo: { name: 'dismissal-test-host', version: '0.1.0', platform: 'browser' },
    manifest: {
      manifestVersion: 1,
      id: 'com.example.close',
      name: 'Close test',
      version: '1.0.0',
      entry: 'index.html',
      protocolVersion: '0.1',
      permissions: [],
    },
    grantedScopes: [],
    environment: { locale: 'en', colorScheme: 'light' },
  });
  host.connect(transport, { onCloseRequested });
  function inject(message: unknown) {
    if (receive === undefined) {
      throw new Error('host receiver must be attached');
    }
    Reflect.apply(receive, undefined, [message]);
    return replies.at(-1);
  }
  return { host, transport, inject, replies, send, close };
}

function request(id: number, method = 'portal.close', params?: unknown) {
  return { jsonrpc: '2.0', id, method, ...(params === undefined ? {} : { params }) };
}

function initialize(h: ReturnType<typeof setup>) {
  expect(h.inject(request(1, 'portal.initialize', { protocolVersion: '0.1' }))).toMatchObject({
    result: { grantedScopes: [] },
  });
}

describe('SPEC §4 / §5 / §9 — gates before Portal dismissal', () => {
  it.each([undefined, {}, { reason: 'done' }, { reason: false }])(
    'requires initialization before method checks for %j',
    (params) => {
      const h = setup();
      expect(h.inject(request(1, 'portal.close', params))).toMatchObject({
        id: 1,
        error: { code: ERROR_CODES.NOT_INITIALIZED },
      });
      expect(h.close).not.toHaveBeenCalled();
    },
  );

  it('keeps the params container gate before initialization', () => {
    const h = setup();
    expect(h.inject(request(1, 'portal.close', []))).toMatchObject({
      id: 1,
      error: { code: ERROR_CODES.INVALID_PARAMS },
    });
    expect(h.close).not.toHaveBeenCalled();
  });

  it('rejects malformed method syntax before initialization', () => {
    const h = setup();
    expect(h.inject(request(1, 'portal.Close'))).toMatchObject({
      id: 1,
      error: { code: ERROR_CODES.INVALID_REQUEST },
    });
    expect(h.close).not.toHaveBeenCalled();
  });

  it('does not reply to a close notification', () => {
    const h = setup();
    h.inject({ jsonrpc: '2.0', method: 'portal.close', params: { reason: 'done' } });
    expect(h.replies).toEqual([]);
    expect(h.close).not.toHaveBeenCalled();
  });

  it('rejects a batch containing close as one unit', () => {
    const h = setup();
    expect(h.inject([request(1)])).toMatchObject({
      id: null,
      error: { code: ERROR_CODES.INVALID_REQUEST },
    });
    expect(h.replies).toHaveLength(1);
    expect(h.close).not.toHaveBeenCalled();
  });
});

describe('SPEC §6.2 / ADR 0019 — accept dismissal before invoking the bound hook', () => {
  it.each([undefined, {}, { reason: 'done' }, { reason: '' }, { reason: '  종료 😀  ' }])(
    'accepts %j without a scope and preserves the reason',
    async (params) => {
      const hook = vi.fn(async (_reason?: string) => {});
      const h = setup(hook);
      initialize(h);
      expect(h.inject(request(2, 'portal.close', params))).toEqual({
        jsonrpc: '2.0',
        id: 2,
        result: {},
      });
      expect(hook).toHaveBeenCalledExactlyOnceWith(params?.reason);
      await flush();
      expect(h.replies).toHaveLength(2);
      expect(h.close).not.toHaveBeenCalled();
    },
  );

  it.each([null, false, 0, [], {}, undefined, new Date(0)])(
    'rejects reason %j before invocation or availability',
    (reason) => {
      const hook = vi.fn(async () => {});
      for (const installed of [undefined, hook]) {
        const h = setup(installed);
        initialize(h);
        expect(h.inject(request(2, 'portal.close', { reason }))).toMatchObject({
          id: 2,
          error: { code: ERROR_CODES.INVALID_PARAMS },
        });
        expect(h.close).not.toHaveBeenCalled();
      }
      expect(hook).not.toHaveBeenCalled();
    },
  );

  it.each(['extra', 'miniAppId', 'portalId'])(
    'rejects the unsupported %s field before handler lookup',
    (field) => {
      const hook = vi.fn(async () => {});
      for (const installed of [undefined, hook]) {
        const h = setup(installed);
        initialize(h);
        expect(
          h.inject(request(2, 'portal.close', { reason: 'done', [field]: 'other' })),
        ).toMatchObject({ error: { code: ERROR_CODES.INVALID_PARAMS } });
      }
      expect(hook).not.toHaveBeenCalled();
    },
  );

  it('does not evaluate a reason getter', () => {
    const hook = vi.fn(async () => {});
    const getter = vi.fn(() => 'done');
    const h = setup(hook);
    initialize(h);
    const params = Object.defineProperty({}, 'reason', { enumerable: true, get: getter });
    expect(h.inject(request(2, 'portal.close', params))).toMatchObject({
      error: { code: ERROR_CODES.INVALID_PARAMS },
    });
    expect(getter).not.toHaveBeenCalled();
    expect(hook).not.toHaveBeenCalled();
  });

  it('returns unavailable for valid params when no hook exists, keeping the connection usable', () => {
    const h = setup();
    initialize(h);
    expect(h.inject(request(2))).toMatchObject({
      id: 2,
      error: { code: ERROR_CODES.CAPABILITY_UNAVAILABLE },
    });
    expect(h.inject(request(3, 'portal.ping'))).toEqual({
      jsonrpc: '2.0',
      id: 3,
      result: { pong: true },
    });
    expect(h.close).not.toHaveBeenCalled();
  });

  it('applies initialization and exact namespace gates even with a hook installed', () => {
    const hook = vi.fn(async () => {});
    const h = setup(hook);
    expect(h.inject(request(1))).toMatchObject({ error: { code: ERROR_CODES.NOT_INITIALIZED } });
    initialize(h);
    expect(h.inject(request(2, 'portalOther.close'))).toMatchObject({
      error: { code: ERROR_CODES.PERMISSION_DENIED },
    });
    expect(hook).not.toHaveBeenCalled();
  });

  it('submits acceptance before calling the hook, without waiting for hook completion', async () => {
    const events: string[] = [];
    let finish: (() => void) | undefined;
    const h = setup(async () => {
      events.push('hook');
      await new Promise<void>((resolve) => {
        finish = resolve;
      });
      events.push('completed');
    });
    initialize(h);
    h.send.mockImplementation((frame) => {
      h.replies.push(frame);
      events.push('send');
    });
    expect(h.inject(request(2))).toEqual({ jsonrpc: '2.0', id: 2, result: {} });
    expect(events).toEqual(['send', 'hook']);
    expect(h.close).not.toHaveBeenCalled();
    if (finish === undefined) {
      throw new Error('hook must be waiting');
    }
    finish();
    await flush();
    expect(events).toEqual(['send', 'hook', 'completed']);
    expect(h.replies).toHaveLength(2);
  });

  it.each(['throw', 'reject'])(
    'reports a hook %s only on the host after one success response',
    async (mode) => {
      const reports: Array<() => void> = [];
      vi.spyOn(globalThis, 'queueMicrotask').mockImplementation((callback) => {
        reports.push(callback);
      });
      const secret = new Error('private host token test-secret');
      const hook =
        mode === 'throw'
          ? () => {
              throw secret;
            }
          : async () => {
              throw secret;
            };
      const h = setup(hook);
      initialize(h);
      h.inject(request(2));
      await flush();
      expect(h.replies).toEqual([
        expect.objectContaining({ id: 1, result: expect.any(Object) }),
        { jsonrpc: '2.0', id: 2, result: {} },
      ]);
      expect(JSON.stringify(h.replies)).not.toContain('test-secret');
      expect(reports).toHaveLength(1);
      expect(reports[0]).toThrow(secret);
      expect(h.close).not.toHaveBeenCalled();
      expect(h.inject(request(3, 'portal.ping'))).toMatchObject({ result: { pong: true } });
    },
  );

  it('does not invoke the hook or attempt a second response when submission throws', () => {
    const hook = vi.fn(async () => {});
    const h = setup(hook);
    initialize(h);
    const failure = new Error('send failed');
    h.send.mockImplementation(() => {
      throw failure;
    });
    expect(() => h.inject(request(2))).toThrow(failure);
    expect(hook).not.toHaveBeenCalled();
    expect(h.send).toHaveBeenCalledTimes(2);
    expect(h.close).not.toHaveBeenCalled();
  });

  it('ignores notifications and rejects batches without invoking dismissal', () => {
    const hook = vi.fn(async () => {});
    const h = setup(hook);
    initialize(h);
    h.inject({ jsonrpc: '2.0', method: 'portal.close' });
    expect(h.replies).toHaveLength(1);
    h.inject([request(2)]);
    expect(h.replies.at(-1)).toMatchObject({
      id: null,
      error: { code: ERROR_CODES.INVALID_REQUEST },
    });
    expect(hook).not.toHaveBeenCalled();
  });

  it('keeps duplicate-id rejection and treats fresh valid close requests separately', async () => {
    const hook = vi.fn(async () => {});
    const h = setup(hook);
    initialize(h);
    h.inject(request(2));
    expect(h.inject(request(2))).toMatchObject({
      id: null,
      error: { code: ERROR_CODES.INVALID_REQUEST },
    });
    h.inject(request(3));
    await flush();
    expect(hook).toHaveBeenCalledTimes(2);
    expect(h.close).not.toHaveBeenCalled();
  });

  it('binds handlers to individual connections even when one host is reused', async () => {
    const firstHook = vi.fn(async () => {});
    const secondHook = vi.fn(async () => {});
    const h = setup(firstHook);
    initialize(h);
    const other = createLinkedTransports();
    h.host.connect(other.b, { onCloseRequested: secondHook });
    const client = createClient({ transport: other.a });
    try {
      await client.initialize();
      await expect(client.call('portal.close', { reason: 'second' })).resolves.toEqual({});
      expect(firstHook).not.toHaveBeenCalled();
      expect(secondHook).toHaveBeenCalledExactlyOnceWith('second');
      h.inject(request(2, 'portal.close', { reason: 'first' }));
      expect(firstHook).toHaveBeenCalledExactlyOnceWith('first');
    } finally {
      client.close();
      other.b.close();
    }
  });

  it('lets an embedder close its transport after submission while the real client receives acceptance', async () => {
    const h = setup();
    const bridge = createLinkedTransports();
    const events: string[] = [];
    const hostTransport: Transport = {
      ...bridge.b,
      send(frame) {
        events.push('send');
        bridge.b.send(frame);
      },
    };
    h.host.connect(hostTransport, {
      async onCloseRequested() {
        events.push('dismiss');
        hostTransport.close();
      },
    });
    const client = createClient({ transport: bridge.a });
    try {
      await client.initialize();
      events.length = 0;
      await expect(client.call('portal.close')).resolves.toEqual({});
      expect(events).toEqual(['send', 'dismiss']);
    } finally {
      client.close();
      bridge.b.close();
    }
  });
});
