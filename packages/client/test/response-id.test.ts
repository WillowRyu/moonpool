/** T08 — uncorrelated errors must not settle requests or clear their timers. */
import { createClient, type MoonpoolClient } from '@moonpool/client';
import { ERROR_CODES, type JsonValue, type ProfileGetResult } from '@moonpool/protocol';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createLinkedTransports, flush } from '../../../test-support/memory-transport';
import { createHost } from '../../host/src/index';

const UNCORRELATED = {
  jsonrpc: '2.0',
  id: null,
  error: { code: ERROR_CODES.INVALID_REQUEST, message: 'Invalid Request' },
};

const connections: Array<{
  client: MoonpoolClient;
  bridge: ReturnType<typeof createLinkedTransports>;
}> = [];

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  for (const { client, bridge } of connections.splice(0)) {
    client.close();
    bridge.b.close();
  }
  vi.useRealTimers();
});

function setup() {
  const bridge = createLinkedTransports();
  const client = createClient({ transport: bridge.a, timeoutMs: 1_000 });
  connections.push({ client, bridge });
  const sent: JsonValue[] = [];
  bridge.b.onMessage((message) => sent.push(message));
  return { client, bridge, sent };
}

describe('SPEC §4.1 / §4.5 — uncorrelated errors', () => {
  it('leaves multiple pending requests and their individual timers alone', async () => {
    const { client, bridge, sent } = setup();
    const settled: unknown[] = [];
    const first = client.call('profile.get');
    const second = client.call('portal.ping');
    first.then(
      (value) => settled.push(value),
      (error) => settled.push(error),
    );
    second.then(
      (value) => settled.push(value),
      (error) => settled.push(error),
    );
    await flush();
    expect(sent).toEqual([expect.objectContaining({ id: 1 }), expect.objectContaining({ id: 2 })]);

    bridge.b.send(UNCORRELATED);
    await flush();

    expect(settled).toEqual([]);
    expect(vi.getTimerCount()).toBe(2);
    bridge.b.send({ jsonrpc: '2.0', id: 2, result: false });
    await expect(second).resolves.toBe(false);
    expect(vi.getTimerCount()).toBe(1);
    bridge.b.send({ jsonrpc: '2.0', id: 1, result: { displayName: 'Matched user' } });
    await expect(first).resolves.toEqual({ displayName: 'Matched user' });
    expect(vi.getTimerCount()).toBe(0);
  });

  it('still times out when no correlated reply follows the null-id error', async () => {
    const { client, bridge } = setup();
    let settled = false;
    const outcome = client.call('profile.get').then(
      (value) => {
        settled = true;
        return { value };
      },
      (error: unknown) => {
        settled = true;
        return { error };
      },
    );
    bridge.b.send(UNCORRELATED);
    await flush();

    await vi.advanceTimersByTimeAsync(999);
    expect(settled).toBe(false);
    expect(vi.getTimerCount()).toBe(1);
    await vi.advanceTimersByTimeAsync(1);
    expect(await outcome).toMatchObject({ error: { code: ERROR_CODES.TIMEOUT } });
    expect(vi.getTimerCount()).toBe(0);
  });

  it('ignores an unsolicited null-id error without replying or poisoning later calls', async () => {
    const { client, bridge, sent } = setup();
    bridge.b.send(UNCORRELATED);
    await flush();
    expect(sent).toEqual([]);
    expect(vi.getTimerCount()).toBe(0);

    const ping = client.call('portal.ping');
    await flush();
    expect(sent).toEqual([expect.objectContaining({ id: 1, method: 'portal.ping' })]);
    bridge.b.send({ jsonrpc: '2.0', id: 1, result: { pong: true } });
    await expect(ping).resolves.toEqual({ pong: true });
    expect(vi.getTimerCount()).toBe(0);
  });

  it('keeps an actual host request pending while a separate batch is rejected', async () => {
    const { client, bridge } = setup();
    let completeProfile: ((value: ProfileGetResult) => void) | undefined;
    createHost({
      hostInfo: { name: 'batch-test-host', version: '0.1.0', platform: 'browser' },
      manifest: {
        manifestVersion: 1,
        id: 'com.example.batch',
        name: 'Batch test',
        version: '1.0.0',
        entry: 'index.html',
        protocolVersion: '0.1',
        permissions: ['profile'],
      },
      grantedScopes: ['profile'],
      environment: { locale: 'en', colorScheme: 'light' },
      capabilities: {
        profile: {
          get: () =>
            new Promise((resolve) => {
              completeProfile = resolve;
            }),
        },
      },
    }).connect(bridge.b);
    await client.initialize();
    const received: JsonValue[] = [];
    bridge.a.onMessage((message) => received.push(message));
    let settled = false;
    const profile = client.call('profile.get');
    profile.then(
      () => {
        settled = true;
      },
      () => {
        settled = true;
      },
    );
    await flush();

    bridge.a.send([]);
    await flush();

    expect(received).toEqual([
      expect.objectContaining({
        id: null,
        error: expect.objectContaining({ code: ERROR_CODES.INVALID_REQUEST }),
      }),
    ]);
    expect(settled).toBe(false);
    expect(vi.getTimerCount()).toBe(1);
    if (completeProfile === undefined) {
      throw new Error('profile provider must be waiting for completion');
    }
    completeProfile({ displayName: 'Matched user' });
    await expect(profile).resolves.toEqual({ displayName: 'Matched user' });
    expect(vi.getTimerCount()).toBe(0);
  });
});
