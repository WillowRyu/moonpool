/**
 * SPEC §4.1 / §4.2 — malformed and notification-shaped frames.
 *
 * §4.1: "Requests without an id are notifications. The receiver MUST NOT
 * reply." A frame that DOES carry an id is addressable — it still gets
 * exactly one reply even if it fails §4.2's request shape in some other way.
 * Before this fix, `isJsonRpcRequest` collapsed both failures (no id; id but
 * malformed) into the same silent `return`, which is correct for the first
 * and wrong for the second.
 *
 * Deliberately out of scope here: top-level batch arrays (§4.1 also assigns
 * these -32600, but there is no single id to reply to — needs its own
 * id:null handling) and a malformed `params` shape (§4.2 assigns that its
 * own code, -32602). Both are tracked as remaining §4.4 coverage in
 * HANDOFF.md, not folded into this fix.
 */
import { createHost, type HostConfig } from '@moonpool/host';
import { ERROR_CODES, type JsonValue, type MiniAppManifest } from '@moonpool/protocol';
import { describe, expect, it } from 'vitest';
import { createLinkedTransports, flush } from './helpers/memory-transport';

const HELLO_MANIFEST: MiniAppManifest = {
  manifestVersion: 1,
  id: 'com.example.hello',
  name: 'Hello',
  version: '1.0.0',
  entry: 'index.html',
  protocolVersion: '0.1',
  permissions: [],
};

/** Shape of a JSON-RPC response, loose on purpose — for assertions only. */
interface RpcResponse {
  jsonrpc: '2.0';
  id: number;
  result?: Record<string, JsonValue>;
  error?: { code: number; message: string; data?: JsonValue };
}

/** Boots a host on one end of an in-memory bridge; the test plays the mini app on the other. */
function setup(overrides: Partial<HostConfig> = {}) {
  const { a: miniAppEnd, b: hostEnd } = createLinkedTransports();

  const host = createHost({
    hostInfo: { name: 'test-host', version: '0.0.0', platform: 'browser' },
    manifest: HELLO_MANIFEST,
    grantedScopes: [],
    environment: { locale: 'ko-KR', colorScheme: 'light' },
    ...overrides,
  });
  host.connect(hostEnd);

  const received: RpcResponse[] = [];
  miniAppEnd.onMessage((message) => received.push(message as unknown as RpcResponse));

  return {
    received,
    send: (message: JsonValue) => miniAppEnd.send(message),
  };
}

const NOTIFICATION_SHAPED: Array<[label: string, frame: JsonValue]> = [
  ['a well-formed notification (no id)', { jsonrpc: '2.0', method: 'portal.ping' }],
  ['a bare string', 'not even an object'],
  ['null', null],
  ['a number', 42],
];

const MALFORMED_WITH_ID: Array<[label: string, frame: JsonValue]> = [
  ['wrong jsonrpc version', { jsonrpc: '1.0', id: 1, method: 'portal.ping' }],
  ['missing method', { jsonrpc: '2.0', id: 1 }],
  ['non-string method', { jsonrpc: '2.0', id: 1, method: 42 }],
];

describe('SPEC §4.1 — frames with no id are notifications, never answered', () => {
  it.each(NOTIFICATION_SHAPED)('stays silent for %s', async (_label, frame) => {
    const bridge = setup();

    bridge.send(frame);
    await flush();

    expect(bridge.received).toEqual([]);
  });
});

describe('SPEC §4.1/§4.2 — a frame with an id still gets exactly one reply, even malformed', () => {
  it.each(MALFORMED_WITH_ID)('rejects %s with -32600 Invalid Request', async (_label, frame) => {
    const bridge = setup();

    bridge.send(frame);
    await flush();

    expect(bridge.received).toEqual([
      {
        jsonrpc: '2.0',
        id: 1,
        error: expect.objectContaining({
          code: ERROR_CODES.INVALID_REQUEST,
          message: expect.any(String),
        }),
      },
    ]);
  });

  it('never silently drops a malformed frame just because it carries an id', async () => {
    const bridge = setup();

    bridge.send({ jsonrpc: 'nonsense', id: 7, method: 'portal.ping' });
    await flush();

    expect(bridge.received).toHaveLength(1);
    expect(bridge.received[0]?.id).toBe(7);
  });
});
