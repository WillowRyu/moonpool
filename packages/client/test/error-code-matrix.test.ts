/**
 * T19 / SPEC §4.4 — distinguish receiving an error from implementing its producer.
 * Literal numbers are copied from the normative table, not derived from the SDK.
 * Controlled peer frames cover reserved/unimplemented producers without inventing policy.
 */
import { createClient, MoonpoolError } from '@moonpool/client';
import { ERROR_CODES, isJsonObject, type JsonValue } from '@moonpool/protocol';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createLinkedTransports, flush } from '../../../test-support/memory-transport';
import { createHost, type HostConfig } from '../../host/src/index';

const SPEC_CODES = [
  { name: 'PARSE_ERROR', code: -32700 },
  { name: 'INVALID_REQUEST', code: -32600 },
  { name: 'METHOD_NOT_FOUND', code: -32601 },
  { name: 'INVALID_PARAMS', code: -32602 },
  { name: 'INTERNAL_ERROR', code: -32603 },
  { name: 'PERMISSION_DENIED', code: -32000 },
  { name: 'CAPABILITY_UNAVAILABLE', code: -32001 },
  { name: 'USER_CANCELLED', code: -32002 },
  { name: 'TIMEOUT', code: -32003 },
  { name: 'PROTOCOL_VERSION_UNSUPPORTED', code: -32004 },
  { name: 'NOT_INITIALIZED', code: -32005 },
  { name: 'RATE_LIMITED', code: -32006 },
  { name: 'HOST_UNAVAILABLE', code: -32007 },
  { name: 'CONNECTION_CLOSED', code: -32008 },
];
const INITIALIZED = {
  protocolVersion: '0.1',
  miniApp: { id: 'com.example.errors', version: '1.0.0' },
  host: { name: 'error-matrix-peer', version: '0.1.0', platform: 'browser' },
  grantedScopes: ['profile'],
  environment: { locale: 'en', colorScheme: 'light' },
};
const PUBLIC_CONTEXT: JsonValue = {
  scope: 'profile',
  context: [null, false, 0, '', { attempt: 2 }],
};
const cleanups: Array<() => void> = [];
const reports: Array<() => void> = [];

beforeEach(() => {
  vi.useFakeTimers();
  reports.length = 0;
  // Provider diagnostics stay observable without becoming uncaught test-runner failures.
  vi.spyOn(globalThis, 'queueMicrotask').mockImplementation((report) => reports.push(report));
});
afterEach(() => {
  for (const cleanup of cleanups.splice(0)) {
    cleanup();
  }
  vi.useRealTimers();
  vi.restoreAllMocks();
});

function observe(promise: Promise<unknown>) {
  const settled = vi.fn();
  const outcome = promise.then(
    (value) => {
      settled();
      return { value };
    },
    (error: unknown) => {
      settled();
      return { error };
    },
  );
  return { settled, outcome };
}

function fixture(protocolVersion = '0.1') {
  const bridge = createLinkedTransports();
  const sent: JsonValue[] = [];
  const replies: JsonValue[] = [];
  bridge.b.onMessage((frame) => sent.push(frame));
  bridge.a.onMessage((frame) => replies.push(frame));
  const client = createClient({ transport: bridge.a, timeoutMs: 1_000, protocolVersion });
  cleanups.push(() => {
    client.close();
    bridge.b.close();
  });
  return { client, bridge, sent, replies };
}

async function controlledPeer() {
  const h = fixture();
  h.bridge.b.onMessage((frame) => {
    if (
      isJsonObject(frame) &&
      frame.method === 'portal.initialize' &&
      typeof frame.id === 'number'
    ) {
      h.bridge.b.send({ jsonrpc: '2.0', id: frame.id, result: INITIALIZED });
    }
  });
  await h.client.initialize();
  return h;
}

function realHost(overrides: Partial<HostConfig> = {}, protocolVersion = '0.1') {
  const h = fixture(protocolVersion);
  createHost({
    hostInfo: { name: 'error-matrix-host', version: '0.1.0', platform: 'browser' },
    manifest: {
      manifestVersion: 1,
      id: 'com.example.errors',
      name: 'Errors',
      version: '1.0.0',
      entry: 'index.html',
      protocolVersion: '0.1',
      permissions: ['profile'],
    },
    grantedScopes: ['profile'],
    environment: { locale: 'en', colorScheme: 'light' },
    ...overrides,
  }).connect(h.bridge.b);
  return h;
}

async function rejected(outcome: ReturnType<typeof observe>['outcome']): Promise<MoonpoolError> {
  const result = await outcome;
  if (!('error' in result) || !(result.error instanceof MoonpoolError)) {
    throw new Error('expected a rejected call carrying MoonpoolError');
  }
  return result.error;
}

describe('SPEC §4.4 — complete client error-code matrix', () => {
  it('pins all 14 exported constants to the normative table without omissions', () => {
    expect(SPEC_CODES).toHaveLength(14);
    expect(ERROR_CODES).toEqual(
      Object.fromEntries(SPEC_CODES.map(({ name, code }) => [name, code])),
    );
  });

  for (const includeData of [true, false]) {
    describe(
      includeData ? 'correlated errors with public data' : 'correlated errors without data',
      () => {
        it.each(SPEC_CODES)(
          '$name ($code) preserves the error and settles only its request',
          async ({ code, name }) => {
            const h = await controlledPeer();
            const failed = observe(h.client.call('profile.get'));
            // §11 leaves peer-close signaling undefined. Do not turn a synthetic
            // terminal-code response into a new disconnect/retry policy.
            const unrelated = code === -32008 ? undefined : observe(h.client.call('portal.ping'));
            await flush();
            const message = `Public peer error: ${name}`;
            const wireError: { code: number; message: string; data?: JsonValue } = {
              code,
              message,
            };
            if (includeData) {
              wireError.data = PUBLIC_CONTEXT;
            }
            h.bridge.b.send({ jsonrpc: '2.0', id: 2, error: wireError });
            const error = await rejected(failed.outcome);
            expect(error).toBeInstanceOf(Error);
            expect(error.name).toBe('MoonpoolError');
            expect(error.code).toBe(code);
            expect(error.message).toBe(message);
            expect(error.data).toEqual(includeData ? PUBLIC_CONTEXT : undefined);
            expect(failed.settled).toHaveBeenCalledOnce();
            expect(vi.getTimerCount()).toBe(unrelated === undefined ? 0 : 1);

            // Duplicate/late replies cannot replace the first error or settle its neighbor.
            h.bridge.b.send({ jsonrpc: '2.0', id: 2, result: 'late success' });
            await flush();
            if (unrelated !== undefined) {
              expect(unrelated.settled).not.toHaveBeenCalled();
              expect(vi.getTimerCount()).toBe(1);
              h.bridge.b.send({ jsonrpc: '2.0', id: 3, result: false });
              expect(await unrelated.outcome).toEqual({ value: false });
            }
            await vi.advanceTimersByTimeAsync(1_000);
            expect(failed.settled).toHaveBeenCalledOnce();
            expect(vi.getTimerCount()).toBe(0);
            expect(h.sent).toHaveLength(unrelated === undefined ? 2 : 3);
            h.client.close();
          },
        );
      },
    );
  }

  it.each(SPEC_CODES)(
    'uncorrelated $name ($code) cannot consume or extend a request',
    async ({ code, name }) => {
      const h = await controlledPeer();
      const pending = observe(h.client.call('profile.get'));
      await vi.advanceTimersByTimeAsync(600);
      h.bridge.b.send({
        jsonrpc: '2.0',
        id: null,
        error: { code, message: `Uncorrelated ${name}` },
      });
      await flush();
      expect(pending.settled).not.toHaveBeenCalled();
      expect(vi.getTimerCount()).toBe(1);
      await vi.advanceTimersByTimeAsync(399);
      expect(pending.settled).not.toHaveBeenCalled();
      await vi.advanceTimersByTimeAsync(1);
      const error = await rejected(pending.outcome);
      expect(error.code).toBe(-32003);
      expect(error.data).toBeUndefined();
      expect(pending.settled).toHaveBeenCalledOnce();
      expect(vi.getTimerCount()).toBe(0);
      expect(h.sent).toHaveLength(2);
    },
  );
});

interface ProducerCase {
  name: string;
  code: number;
  method: string;
  params?: Record<string, JsonValue>;
  grantedScopes: string[];
  provider: 'unused' | 'missing' | 'fails';
  data?: JsonValue;
}
const HOST_CASES: ProducerCase[] = [
  {
    name: 'malformed method',
    code: -32600,
    method: 'Profile.get',
    grantedScopes: ['profile'],
    provider: 'unused',
  },
  {
    name: 'unknown granted method',
    code: -32601,
    method: 'profile.missing',
    grantedScopes: ['profile'],
    provider: 'unused',
  },
  {
    name: 'unsupported params',
    code: -32602,
    method: 'profile.get',
    params: { extra: true },
    grantedScopes: ['profile'],
    provider: 'unused',
  },
  {
    name: 'provider failure',
    code: -32603,
    method: 'profile.get',
    grantedScopes: ['profile'],
    provider: 'fails',
  },
  {
    name: 'scope denial',
    code: -32000,
    method: 'profile.get',
    grantedScopes: [],
    provider: 'unused',
    data: { scope: 'profile' },
  },
  {
    name: 'unavailable capability',
    code: -32001,
    method: 'profile.get',
    grantedScopes: ['profile'],
    provider: 'missing',
  },
];

describe('specified host producers — actual host to actual client', () => {
  it.each(HOST_CASES)(
    '$name produces $code and retains host-only diagnostics',
    async (scenario) => {
      const secret = new Error('private host credential: matrix-test-secret');
      const get = vi.fn(async () => {
        if (scenario.provider === 'fails') {
          throw secret;
        }
        return { displayName: 'Public user' };
      });
      const h = realHost({
        grantedScopes: scenario.grantedScopes,
        capabilities: scenario.provider === 'missing' ? undefined : { profile: { get } },
      });
      await h.client.initialize();
      const error = await rejected(
        observe(h.client.call(scenario.method, scenario.params)).outcome,
      );
      expect(error.code).toBe(scenario.code);
      expect(error.message.length).toBeGreaterThan(0);
      expect(error.data).toEqual(scenario.data);
      expect(get).toHaveBeenCalledTimes(scenario.provider === 'fails' ? 1 : 0);
      expect(JSON.stringify(h.replies)).not.toContain('matrix-test-secret');
      expect(vi.getTimerCount()).toBe(0);
      if (scenario.provider === 'fails') {
        expect(error.message).toBe('profile.get failed inside the host');
        expect(reports).toHaveLength(1);
        expect(reports[0]).toThrow(secret);
      } else {
        expect(reports).toHaveLength(0);
      }
    },
  );

  it('negotiation failure produces -32004 and a valid retry can initialize', async () => {
    const h = realHost({}, '9.9');
    const error = await rejected(observe(h.client.initialize()).outcome);
    expect(error.code).toBe(-32004);
    expect(vi.getTimerCount()).toBe(0);
    await expect(
      h.client.call('portal.initialize', { protocolVersion: '0.1' }),
    ).resolves.toMatchObject({ protocolVersion: '0.1' });
  });

  it('a call before initialize produces -32005, then the same connection can initialize', async () => {
    const h = realHost();
    const error = await rejected(observe(h.client.call('profile.get')).outcome);
    expect(error.code).toBe(-32005);
    expect(vi.getTimerCount()).toBe(0);
    await h.client.initialize();
    await expect(h.client.call('portal.ping')).resolves.toEqual({ pong: true });
  });

  it.each([-32002, -32006, -32007])(
    'a provider throwing code %s still produces sanitized -32603, not a new policy',
    async (code) => {
      const privateFailure = new MoonpoolError(code, 'private provider detail', {
        secret: 'provider-private',
      });
      const h = realHost({
        capabilities: {
          profile: {
            async get() {
              throw privateFailure;
            },
          },
        },
      });
      await h.client.initialize();
      const error = await rejected(observe(h.client.call('profile.get')).outcome);
      expect(error.code).toBe(-32603);
      expect(error.message).toBe('profile.get failed inside the host');
      expect(error.data).toBeUndefined();
      expect(JSON.stringify(h.replies)).not.toContain('provider-private');
      expect(reports).toHaveLength(1);
      expect(reports[0]).toThrow(privateFailure);
    },
  );
});
