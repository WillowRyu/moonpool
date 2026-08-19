/**
 * SPEC §5 — Handshake, client side.
 *
 * The mini app initiates: `portal.initialize` MUST be the first request on
 * the connection, and a -32004 refusal from the host must surface to the
 * caller as a rejection. The test plays the host side of the bridge.
 */
import { createClient } from '@moonpool/client';
import { ERROR_CODES, type InitializeResult, type JsonValue } from '@moonpool/protocol';
import { describe, expect, it } from 'vitest';
import { createLinkedTransports, flush } from './helpers/memory-transport';

/** Shape of a JSON-RPC request, loose on purpose — for assertions only. */
interface RpcRequest {
  jsonrpc: '2.0';
  id: number;
  method: string;
  params?: Record<string, JsonValue>;
}

const HANDSHAKE_RESULT: InitializeResult = {
  protocolVersion: '0.1',
  miniApp: { id: 'com.example.hello', version: '1.0.0' },
  host: { name: 'fake-host', version: '0.0.0', platform: 'browser' },
  grantedScopes: ['profile'],
  environment: { locale: 'ko-KR', colorScheme: 'light' },
};

describe('SPEC §5 — the mini app initiates', () => {
  it('sends portal.initialize as the first request on the connection', async () => {
    const { a: clientEnd, b: hostEnd } = createLinkedTransports();
    const sentToHost: RpcRequest[] = [];
    hostEnd.onMessage((message) => {
      sentToHost.push(message as unknown as RpcRequest);
    });

    const client = createClient({ transport: clientEnd });
    client.initialize().catch(() => {
      // Never answered in this test; only the outgoing message matters.
    });
    await flush();

    expect(sentToHost).toHaveLength(1);
    const first = sentToHost[0];
    expect(first).toMatchObject({
      jsonrpc: '2.0',
      method: 'portal.initialize',
      params: { protocolVersion: '0.1' },
    });
    // §4.1: ids are positive integers, unique per connection.
    expect(Number.isInteger(first?.id)).toBe(true);
    expect(first?.id).toBeGreaterThan(0);
  });

  it('resolves initialize() with the handshake result from the host', async () => {
    const { a: clientEnd, b: hostEnd } = createLinkedTransports();
    hostEnd.onMessage((message) => {
      const { id } = message as unknown as RpcRequest;
      hostEnd.send({ jsonrpc: '2.0', id, result: HANDSHAKE_RESULT } as unknown as JsonValue);
    });

    const client = createClient({ transport: clientEnd });

    await expect(client.initialize()).resolves.toEqual(HANDSHAKE_RESULT);
  });

  it('rejects initialize() with code -32004 when the host cannot speak the version', async () => {
    const { a: clientEnd, b: hostEnd } = createLinkedTransports();
    hostEnd.onMessage((message) => {
      const { id } = message as unknown as RpcRequest;
      hostEnd.send({
        jsonrpc: '2.0',
        id,
        error: {
          code: ERROR_CODES.PROTOCOL_VERSION_UNSUPPORTED,
          message: 'Host cannot speak the requested protocol version',
        },
      });
    });

    const client = createClient({ transport: clientEnd });

    // The error shape is the implementer's choice; the code must survive the trip.
    await expect(client.initialize()).rejects.toMatchObject({
      code: ERROR_CODES.PROTOCOL_VERSION_UNSUPPORTED,
    });
  });
});
