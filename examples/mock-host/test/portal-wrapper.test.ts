// @vitest-environment happy-dom
/** SPEC §8.1.1 — the wrapper owns its kernel and local JSON/provider objects. */
import { createHost } from '@moonpool/host';
import type { JsonValue } from '@moonpool/protocol';
import { createIframeTransport } from '@moonpool/transport-iframe';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createLinkedTransports, flush } from '../../../test-support/memory-transport';
import type { ProviderGateway, WrapperControls } from '../src/browser-contract';
import { encodeJson } from '../src/json-boundary';
import { isEnforcedFrameViolation, startWrapper } from '../src/portal-wrapper';
import { disableFrameNavigation } from './helpers/dom';

vi.mock('@moonpool/transport-iframe', () => ({ createIframeTransport: vi.fn() }));
vi.mock('@moonpool/host', async (importOriginal) => {
  const original = await importOriginal<typeof import('@moonpool/host')>();
  return { ...original, createHost: vi.fn(original.createHost) };
});
let restoreNavigation: () => void;
let controls: WrapperControls | undefined;
let pair: ReturnType<typeof createLinkedTransports>;
let gateway: ProviderGateway;
let replies: JsonValue[];

beforeEach(() => {
  vi.mocked(createHost).mockClear();
  restoreNavigation = disableFrameNavigation();
  document.body.innerHTML = '<div id="portal"></div>';
  pair = createLinkedTransports();
  replies = [];
  pair.a.onMessage((message) => replies.push(message));
  vi.mocked(createIframeTransport).mockReturnValue(pair.b);
  controls = undefined;
  gateway = {
    configuration: vi.fn(async () =>
      encodeJson({
        hostInfo: { name: 'test', version: '0.1.0', platform: 'browser' },
        manifest: {
          manifestVersion: 1,
          id: 'com.example.hello',
          name: 'Hello',
          version: '1.0.0',
          entry: 'index.html',
          protocolVersion: '0.1',
          permissions: ['profile', 'storage'],
        },
        grantedScopes: ['profile', 'storage'],
        environment: { locale: 'en', colorScheme: 'light' },
        origin: 'http://localhost:5174',
        profileAvailable: true,
        storageAvailable: true,
      }),
    ),
    profile: vi.fn(async () => '{"displayName":"Public user"}'),
    get: vi.fn(async () => '{"nested":[null,false,0]}'),
    set: vi.fn(async () => {}),
    delete: vi.fn(async () => {}),
    close: vi.fn(async () => {}),
  };
  Reflect.set(
    window,
    'moonpoolBootstrap',
    vi.fn(async (_source: unknown, _doc: unknown, _api: unknown) => {
      return gateway;
    }),
  );
});
afterEach(async () => {
  vi.restoreAllMocks();
  await controls?.dispose();
  pair.a.close();
  pair.b.close();
  Reflect.deleteProperty(window, 'moonpoolBootstrap');
  document.body.replaceChildren();
  restoreNavigation();
});
async function start() {
  controls = await startWrapper(window);
  pair.a.send({
    jsonrpc: '2.0',
    id: 1,
    method: 'portal.initialize',
    params: { protocolVersion: '0.1' },
  });
  await flush(40);
}

describe('trusted wrapper integration', () => {
  it('initializes the real kernel before guest calls and reconstructs provider JSON', async () => {
    await start();
    expect(document.querySelector('iframe')?.src).toBe('http://localhost:5174/index.html');
    expect(replies[0]).toMatchObject({
      id: 1,
      result: { miniApp: { id: 'com.example.hello' }, grantedScopes: ['profile', 'storage'] },
    });
    pair.a.send({ jsonrpc: '2.0', id: 2, method: 'profile.get' });
    pair.a.send({ jsonrpc: '2.0', id: 3, method: 'storage.get', params: { key: 'saved' } });
    await flush(40);
    expect(replies).toContainEqual({
      jsonrpc: '2.0',
      id: 2,
      result: { displayName: 'Public user' },
    });
    expect(replies).toContainEqual({
      jsonrpc: '2.0',
      id: 3,
      result: { value: { nested: [null, false, 0] } },
    });
    expect(gateway.get).toHaveBeenCalledExactlyOnceWith('saved');
  });

  it('encodes validated writes and leaves invalid guest data to existing kernel errors', async () => {
    await start();
    pair.a.send({
      jsonrpc: '2.0',
      id: 2,
      method: 'storage.set',
      params: { key: 'x', value: { a: [null, false] } },
    });
    Reflect.apply(pair.a.send, pair.a, [
      { jsonrpc: '2.0', id: 3, method: 'storage.set', params: { key: 'x', value: new Date() } },
    ]);
    await flush(40);
    expect(gateway.set).toHaveBeenCalledExactlyOnceWith('x', '{"a":[null,false]}');
    expect(replies).toContainEqual(
      expect.objectContaining({ id: 3, error: expect.objectContaining({ code: -32602 }) }),
    );
  });

  it('applies repeat handshake without rebuilding providers or erasing grants', async () => {
    await start();
    pair.a.send({
      jsonrpc: '2.0',
      id: 1,
      method: 'portal.initialize',
      params: { protocolVersion: '0.1' },
    });
    await flush(40);
    pair.a.send({ jsonrpc: '2.0', id: 2, method: 'storage.get', params: { key: 'x' } });
    await flush(40);
    expect(gateway.configuration).toHaveBeenCalledOnce();
    expect(
      replies.filter(
        (reply) =>
          typeof reply === 'object' && reply !== null && !Array.isArray(reply) && reply.id === 1,
      ),
    ).toHaveLength(2);
    expect(gateway.get).toHaveBeenCalledExactlyOnceWith('x');
  });

  it('sends notifications using wrapper-local data and rejects malformed controls', async () => {
    await start();
    await controls?.notifyEnvironmentChanged('{"colorScheme":"dark","locale":"ko-KR"}');
    await controls?.notifyLifecycle('"paused"');
    await flush(40);
    expect(replies).toContainEqual({
      jsonrpc: '2.0',
      method: 'portal.environmentChanged',
      params: { colorScheme: 'dark', locale: 'ko-KR' },
    });
    expect(replies).toContainEqual({
      jsonrpc: '2.0',
      method: 'portal.lifecycle',
      params: { state: 'paused' },
    });
    const count = replies.length;
    await expect(controls?.notifyEnvironmentChanged('{"locale":17}')).rejects.toThrow(TypeError);
    await expect(controls?.notifyLifecycle('"stopped"')).rejects.toThrow(TypeError);
    expect(replies).toHaveLength(count);
  });

  it('acknowledges portal.close before invoking outer dismissal', async () => {
    await start();
    const send = vi.spyOn(pair.b, 'send');
    const close = vi.mocked(gateway.close).mockImplementation(async () => {
      expect(send).toHaveBeenCalledWith({ jsonrpc: '2.0', id: 2, result: {} });
      await controls?.dispose();
    });
    pair.a.send({ jsonrpc: '2.0', id: 2, method: 'portal.close', params: { reason: 'finished' } });
    await flush(40);
    expect(close).toHaveBeenCalledExactlyOnceWith('finished');
    expect(document.querySelector('iframe')).toBeNull();
  });

  it('suppresses late provider completion and rejects retired controls', async () => {
    let release: ((text: string) => void) | undefined;
    vi.mocked(gateway.profile).mockImplementation(
      () =>
        new Promise((resolve) => {
          release = resolve;
        }),
    );
    await start();
    pair.a.send({ jsonrpc: '2.0', id: 2, method: 'profile.get' });
    await flush(40);
    await controls?.dispose();
    const send = vi.spyOn(pair.b, 'send');
    release?.('{"displayName":"old"}');
    await flush(40);
    expect(send).not.toHaveBeenCalled();
    await expect(controls?.notifyLifecycle('"paused"')).rejects.toThrow('inactive');
    pair.a.send({ jsonrpc: '2.0', id: 3, method: 'profile.get' });
    await flush(40);
    expect(gateway.profile).toHaveBeenCalledOnce();
  });

  it('removes the guest and CSP listener even if transport cleanup fails', async () => {
    await start();
    const remove = vi.spyOn(document, 'removeEventListener');
    const close = vi.spyOn(pair.b, 'close').mockImplementationOnce(() => {
      throw new Error('close failed');
    });
    await expect(controls?.dispose()).rejects.toThrow('close failed');
    expect(document.querySelector('iframe')).toBeNull();
    expect(remove).toHaveBeenCalledWith('securitypolicyviolation', expect.any(Function));
    await controls?.dispose();
    expect(close).toHaveBeenCalledOnce();
  });

  it('checks the storage facade id instead of trusting a caller override', async () => {
    await start();
    const storage = vi.mocked(createHost).mock.calls[0]?.[0].capabilities?.storage;
    if (storage === undefined) {
      throw new Error('missing local storage facade');
    }
    await expect(storage.get('com.example.second', 'x')).rejects.toThrow('identity mismatch');
    expect(gateway.get).not.toHaveBeenCalled();
  });

  it('ignores retained receive callbacks after wrapper disposal', async () => {
    const subscribe = vi.spyOn(pair.b, 'onMessage');
    await start();
    const receive = subscribe.mock.calls[0]?.[0];
    const send = vi.spyOn(pair.b, 'send');
    await controls?.dispose();
    send.mockClear();
    receive?.({ jsonrpc: '2.0', id: 2, method: 'profile.get' });
    await flush(40);
    expect(gateway.profile).not.toHaveBeenCalled();
    expect(send).not.toHaveBeenCalled();
  });

  it('ignores synthetic CSP events even with matching directive fields', async () => {
    await start();
    const event = Object.assign(new Event('securitypolicyviolation'), {
      disposition: 'enforce',
      effectiveDirective: 'frame-src',
    });
    document.dispatchEvent(event);
    expect(gateway.close).not.toHaveBeenCalled();
    expect(document.querySelector('iframe')).not.toBeNull();
  });

  it('cleans the guest and policy listener if transport startup fails', async () => {
    const remove = vi.spyOn(document, 'removeEventListener');
    vi.mocked(createIframeTransport).mockImplementationOnce(() => {
      throw new Error('transport startup failed');
    });
    await expect(startWrapper(window)).rejects.toThrow('transport startup failed');
    expect(document.querySelector('iframe')).toBeNull();
    expect(remove).toHaveBeenCalledWith('securitypolicyviolation', expect.any(Function));
    expect(gateway.close).toHaveBeenCalledExactlyOnceWith('Wrapper startup failed');
  });

  it('does not read inherited optional-field getters when reconstructing notifications', async () => {
    await start();
    const getter = vi.fn(() => 'inherited');
    Object.defineProperty(Object.prototype, 'locale', { get: getter, configurable: true });
    try {
      await controls?.notifyEnvironmentChanged('{}');
    } finally {
      Reflect.deleteProperty(Object.prototype, 'locale');
    }
    await flush(40);
    expect(getter).not.toHaveBeenCalled();
    expect(replies.at(-1)).toEqual({
      jsonrpc: '2.0',
      method: 'portal.environmentChanged',
      params: {},
    });
  });

  it('does not surface normal revocation as an uncaught late-provider failure', async () => {
    let reject: ((error: Error) => void) | undefined;
    vi.mocked(gateway.profile).mockImplementation(
      () =>
        new Promise((_resolve, fail) => {
          reject = fail;
        }),
    );
    await start();
    pair.a.send({ jsonrpc: '2.0', id: 2, method: 'profile.get' });
    await flush(40);
    await controls?.dispose();
    const send = vi.spyOn(pair.b, 'send');
    reject?.(new Error('Portal is inactive'));
    await flush(40);
    expect(send).not.toHaveBeenCalled();
  });

  it('maps an invalid active provider result to the existing sanitized internal error', async () => {
    vi.useFakeTimers({ toFake: ['queueMicrotask'] });
    try {
      vi.mocked(gateway.get).mockResolvedValue('{"value":1e999}');
      await start();
      pair.a.send({ jsonrpc: '2.0', id: 2, method: 'storage.get', params: { key: 'x' } });
      await flush(40);
      expect(replies.at(-1)).toMatchObject({ id: 2, error: { code: -32603 } });
      expect(() => vi.runAllTicks()).toThrow(TypeError);
    } finally {
      vi.useRealTimers();
    }
  });

  it.each([
    [true, 'enforce', 'frame-src', true],
    [false, 'enforce', 'frame-src', false],
    [true, 'report', 'frame-src', false],
    [true, 'enforce', 'script-src', false],
  ])(
    'policy decision: trusted=%s disposition=%s directive=%s',
    (isTrusted, disposition, effectiveDirective, expected) => {
      expect(isEnforcedFrameViolation({ isTrusted, disposition, effectiveDirective })).toBe(
        expected,
      );
    },
  );
});
