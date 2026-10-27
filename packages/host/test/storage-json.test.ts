/**
 * SPEC §6.3 / ADR 0008 — reject non-JSON storage values without conversion.
 * Test the actual host boundary. The in-memory transport intentionally
 * preserves invalid values; browser transport wiring is not tested here.
 */
import { createHost, type HostConfig } from '@moonpool/host';
import { ERROR_CODES, type JsonValue } from '@moonpool/protocol';
import { describe, expect, it, vi } from 'vitest';
import { createLinkedTransports, flush } from '../../../test-support/memory-transport';

interface RpcResponse {
  jsonrpc: '2.0';
  id: number;
  result?: Record<string, JsonValue>;
  error?: { code: number; message: string };
}

function setup(overrides: Partial<HostConfig> = {}) {
  const { a: miniAppEnd, b: hostEnd } = createLinkedTransports();
  const set = vi.fn(async (_miniAppId: string, _key: string, _value: JsonValue) => undefined);
  createHost({
    hostInfo: { name: 'test-host', version: '0.0.0', platform: 'browser' },
    manifest: {
      manifestVersion: 1,
      id: 'com.example.hello',
      name: 'Hello',
      version: '1.0.0',
      entry: 'index.html',
      protocolVersion: '0.1',
      permissions: ['storage'],
    },
    grantedScopes: ['storage'],
    environment: { locale: 'ko-KR', colorScheme: 'light' },
    capabilities: { storage: { get: async () => null, set, delete: async () => undefined } },
    ...overrides,
  }).connect(hostEnd);

  const received: RpcResponse[] = [];
  miniAppEnd.onMessage((message) => received.push(message as unknown as RpcResponse));
  return {
    set,
    received,
    send: (message: JsonValue) => miniAppEnd.send(message),
  };
}

async function initialize(bridge: ReturnType<typeof setup>) {
  bridge.send({
    jsonrpc: '2.0',
    id: 1,
    method: 'portal.initialize',
    params: { protocolVersion: '0.1' },
  });
  await flush();
  expect(bridge.received[0]?.result?.protocolVersion).toBe('0.1');
}

function write(id: number, value: unknown): JsonValue {
  // Deliberately cross the typed boundary without serialization. A cast
  // cannot prove runtime JSON validity, which is exactly what these tests expose.
  return {
    jsonrpc: '2.0',
    id,
    method: 'storage.set',
    params: { key: 'settings', value },
  } as JsonValue;
}

async function callWrite(bridge: ReturnType<typeof setup>, value: unknown) {
  await initialize(bridge);
  bridge.send(write(2, value));
  await flush();
  return bridge.received[1];
}

describe('SPEC §6.3 — reject non-JSON storage values before provider access', () => {
  const INVALID_VALUES: Array<[label: string, makeValue: () => unknown]> = [
    ['undefined in an object', () => ({ nickname: undefined })],
    ['undefined in an array', () => [undefined]],
    ['NaN', () => Number.NaN],
    ['nested NaN', () => ({ scores: [Number.NaN] })],
    ['positive infinity', () => Number.POSITIVE_INFINITY],
    ['nested negative infinity', () => ({ score: Number.NEGATIVE_INFINITY })],
    ['a Date', () => new Date(0)],
    ['a nested Date', () => ({ createdAt: new Date(0) })],
    ['a nested Map', () => ({ entries: new Map([['key', 'value']]) })],
    ['a Set', () => new Set(['value'])],
    ['a typed array', () => new Uint8Array([1, 2])],
    ['a nested bigint', () => ({ count: 1n })],
    [
      'an object cycle',
      () => {
        const value: { self?: unknown } = {};
        value.self = value;
        return value;
      },
    ],
    [
      'an indirect cycle',
      () => {
        const first: { next?: unknown } = {};
        first.next = { next: first };
        return first;
      },
    ],
    [
      'an array cycle',
      () => {
        const value: unknown[] = [];
        value.push(value);
        return value;
      },
    ],
    ['a sparse array hole', () => new Array(1)],
    ['a symbol-keyed member', () => ({ [Symbol('hidden')]: 1 })],
    ['a non-enumerable member', () => Object.defineProperty({}, 'hidden', { value: undefined })],
    ['a named array member', () => Object.assign([1], { extra: 'lost in JSON' })],
  ];

  it.each(INVALID_VALUES)('rejects %s with one -32602 reply', async (_label, makeValue) => {
    // Catches shallow checks, serialization-based coercion, accepting empty
    // enumerable views of Map/Set, and missing cycle detection.
    const bridge = setup();

    const reply = await callWrite(bridge, makeValue());

    expect(bridge.received).toHaveLength(2);
    expect(reply).toEqual({
      jsonrpc: '2.0',
      id: 2,
      error: expect.objectContaining({ code: ERROR_CODES.INVALID_PARAMS }),
    });
    expect(bridge.set).not.toHaveBeenCalled();
  });

  it('validates the value before checking provider availability', async () => {
    const bridge = setup({ capabilities: undefined });

    const reply = await callWrite(bridge, { score: Number.NaN });

    expect(reply?.error?.code).toBe(ERROR_CODES.INVALID_PARAMS);
  });

  it('rejects a toJSON function without executing it', async () => {
    // A serialization-based validator can run caller-supplied code and
    // inspect its replacement output instead of rejecting the original value.
    const toJSON = vi.fn(() => ({ replaced: true }));
    const bridge = setup();
    const reply = await callWrite(bridge, { toJSON });
    expect(reply?.error?.code).toBe(ERROR_CODES.INVALID_PARAMS);
    expect(toJSON).not.toHaveBeenCalled();
    expect(bridge.set).not.toHaveBeenCalled();
  });

  it('rejects a getter without evaluating caller-supplied code', async () => {
    // Reading through Object.values or value[key] would execute this getter.
    // JSON input is data; inspection must not manufacture data by running it.
    const get = vi.fn(() => 'computed');
    const value = Object.defineProperty({}, 'nickname', { enumerable: true, get });
    const bridge = setup();
    const reply = await callWrite(bridge, value);
    expect(reply?.error?.code).toBe(ERROR_CODES.INVALID_PARAMS);
    expect(get).not.toHaveBeenCalled();
    expect(bridge.set).not.toHaveBeenCalled();
  });

  it('leaves both existing storage and invalid input intact after rejection', async () => {
    // Removing undefined properties before storage would silently change
    // caller intent. Replying with an error after writing would be too late.
    let saved: JsonValue = { theme: 'dark' };
    const set = vi.fn(async (_id: string, _key: string, value: JsonValue) => {
      saved = value;
    });
    const bridge = setup({
      capabilities: {
        storage: { get: async () => saved, set, delete: async () => undefined },
      },
    });
    const invalid = { nickname: undefined };

    const reply = await callWrite(bridge, invalid);

    expect(reply?.error?.code).toBe(ERROR_CODES.INVALID_PARAMS);
    expect(set).not.toHaveBeenCalled();
    expect(Object.hasOwn(invalid, 'nickname')).toBe(true);
    expect(invalid.nickname).toBeUndefined();
    bridge.send({ jsonrpc: '2.0', id: 3, method: 'storage.get', params: { key: 'settings' } });
    await flush();
    expect(bridge.received[2]?.result).toEqual({ value: { theme: 'dark' } });
  });
});

describe('SPEC §5 / §9.3 — preserve gates before value validation', () => {
  it('denies an ungranted write before reporting its invalid value', async () => {
    // Already green. Value inspection must stay below permission enforcement.
    const bridge = setup({ grantedScopes: [] });
    const reply = await callWrite(bridge, { score: Number.NaN });
    expect(reply?.error?.code).toBe(ERROR_CODES.PERMISSION_DENIED);
    expect(bridge.set).not.toHaveBeenCalled();
  });

  it('rejects an uninitialized write before reporting its invalid value', async () => {
    // Already green. The new validation must not bypass the handshake gate.
    const bridge = setup();
    bridge.send(write(1, { score: Number.NaN }));
    await flush();
    expect(bridge.received).toHaveLength(1);
    expect(bridge.received[0]?.error?.code).toBe(ERROR_CODES.NOT_INITIALIZED);
    expect(bridge.set).not.toHaveBeenCalled();
  });
});

describe('SPEC §6.3 — preserve valid JSON values', () => {
  it('preserves nested null, falsy values, finite numbers, empty containers, and arbitrary keys', async () => {
    // Already green. Catches rejecting nested null, restricting stored key
    // names, or accepting only integers/positive numbers during number checks.
    const bridge = setup();
    const reply = await callWrite(bridge, {
      miniAppId: 'application data',
      values: [null, false, 0, '', -0.5, Number.MAX_VALUE],
      emptyObject: {},
      emptyArray: [],
    });
    expect(reply).toEqual({ jsonrpc: '2.0', id: 2, result: {} });
    expect(bridge.set).toHaveBeenCalledExactlyOnceWith('com.example.hello', 'settings', {
      miniAppId: 'application data',
      values: [null, false, 0, '', -0.5, Number.MAX_VALUE],
      emptyObject: {},
      emptyArray: [],
    });
  });

  it('accepts shared acyclic content in two positions', async () => {
    // Already green. A global seen-object rejection would mistake sharing
    // for a cycle. Each position represents ordinary JSON object content.
    const shared = { enabled: true };
    const bridge = setup();
    const reply = await callWrite(bridge, { first: shared, second: shared });
    expect(reply).toEqual({ jsonrpc: '2.0', id: 2, result: {} });
    expect(bridge.set).toHaveBeenCalledExactlyOnceWith('com.example.hello', 'settings', {
      first: { enabled: true },
      second: { enabled: true },
    });
  });

  it('accepts a deep finite tree without depending on the JavaScript call stack', async () => {
    // Already green. This is a stress sample, not an approved maximum depth.
    // Avoid recursive matchers too: inspect the provider argument iteratively.
    const depth = 20_000;
    let value: JsonValue = 'leaf';
    for (let i = 0; i < depth; i += 1) {
      value = { next: value };
    }
    const bridge = setup();
    const reply = await callWrite(bridge, value);
    expect(reply).toEqual({ jsonrpc: '2.0', id: 2, result: {} });
    expect(bridge.set).toHaveBeenCalledTimes(1);

    let cursor: unknown = bridge.set.mock.calls[0]?.[2];
    let traversed = 0;
    while (
      traversed <= depth &&
      typeof cursor === 'object' &&
      cursor !== null &&
      'next' in cursor
    ) {
      cursor = cursor.next;
      traversed += 1;
    }
    expect(traversed).toBe(depth);
    expect(cursor).toBe('leaf');
  });

  it('validates repeatedly shared subtrees without expanding every path', async () => {
    // Only 31 distinct objects, but expanding every left/right path would
    // revisit the leaf more than a billion times. Completion caching should
    // recognize previously validated objects; the ordinary test timeout is
    // a backstop, not a new protocol size or timing limit.
    let value: JsonValue = { leaf: true };
    for (let i = 0; i < 30; i += 1) {
      value = { left: value, right: value };
    }
    const bridge = setup();
    const reply = await callWrite(bridge, value);
    expect(reply).toEqual({ jsonrpc: '2.0', id: 2, result: {} });
    expect(bridge.set).toHaveBeenCalledTimes(1);
    // Do not recursively compare or stringify this shared graph in the test.
  });
});
