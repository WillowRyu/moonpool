/**
 * T03 / SPEC §6.3 — the development provider must partition data by app id.
 * Exercise the production provider directly and through the real host/client.
 */
import { createHost, type StorageProvider } from '@moonpool/host';
import { ERROR_CODES, type StorageSetValue } from '@moonpool/protocol';
import { afterEach, describe, expect, it } from 'vitest';
import { createClient } from '../../../packages/client/src/index';
import { createLinkedTransports } from '../../../test-support/memory-transport';
import { createMemoryStorageProvider } from '../src/memory-storage';

const APP_A = 'com.example.alpha';
const APP_B = 'com.example.beta';

describe('T03 — per-app in-memory storage', () => {
  it('supports asynchronous get/set/delete and returns null only after the key is absent', async () => {
    const storage = createMemoryStorageProvider();
    const value = { theme: 'dark' };

    await expect(storage.get(APP_A, 'settings')).resolves.toBeNull();
    await expect(storage.set(APP_A, 'settings', value)).resolves.toBeUndefined();
    await expect(storage.get(APP_A, 'settings')).resolves.toEqual(value);
    await expect(storage.delete(APP_A, 'settings')).resolves.toBeUndefined();
    await expect(storage.get(APP_A, 'settings')).resolves.toBeNull();
  });

  const values: Array<{ label: string; value: StorageSetValue }> = [
    { label: 'false', value: false },
    { label: 'zero', value: 0 },
    { label: 'an empty string', value: '' },
    { label: 'nested null in an object', value: { note: null } },
    { label: 'nested null and falsy values in an array', value: [null, false, 0, ''] },
  ];

  it.each(values)(
    'preserves $label rather than treating it as an absent key',
    async ({ value }) => {
      const storage = createMemoryStorageProvider();

      await storage.set(APP_A, 'value', value);

      await expect(storage.get(APP_A, 'value')).resolves.toEqual(value);
    },
  );

  it('replaces an existing value without changing another key', async () => {
    const storage = createMemoryStorageProvider();
    await storage.set(APP_A, 'theme', 'light');
    await storage.set(APP_A, 'language', 'ko');

    await storage.set(APP_A, 'theme', 'dark');

    await expect(storage.get(APP_A, 'theme')).resolves.toBe('dark');
    await expect(storage.get(APP_A, 'language')).resolves.toBe('ko');
  });

  it('stores different values for the same key in different apps', async () => {
    const storage = createMemoryStorageProvider();

    await storage.set(APP_A, 'settings', 'alpha');
    await storage.set(APP_B, 'settings', 'beta');

    await expect(storage.get(APP_A, 'settings')).resolves.toBe('alpha');
    await expect(storage.get(APP_B, 'settings')).resolves.toBe('beta');
  });

  it('deletes only the selected app key and preserves its other keys', async () => {
    const storage = createMemoryStorageProvider();
    await storage.set(APP_A, 'settings', 'alpha');
    await storage.set(APP_A, 'language', 'ko');
    await storage.set(APP_B, 'settings', 'beta');

    await storage.delete(APP_A, 'settings');

    await expect(storage.get(APP_A, 'settings')).resolves.toBeNull();
    await expect(storage.get(APP_A, 'language')).resolves.toBe('ko');
    await expect(storage.get(APP_B, 'settings')).resolves.toBe('beta');
  });

  it('treats deletion of an absent key or app as a no-op', async () => {
    const storage = createMemoryStorageProvider();
    await storage.set(APP_A, 'settings', 'alpha');

    await expect(storage.delete(APP_A, 'missing')).resolves.toBeUndefined();
    await expect(storage.delete(APP_B, 'settings')).resolves.toBeUndefined();
    await expect(storage.get(APP_A, 'settings')).resolves.toBe('alpha');
    await expect(storage.get(APP_B, 'settings')).resolves.toBeNull();
  });

  it.each(['', '__proto__', 'constructor', 'settings:theme'])(
    'preserves the caller key %j without special interpretation',
    async (key) => {
      const storage = createMemoryStorageProvider();

      await storage.set(APP_A, key, 'stored');

      await expect(storage.get(APP_A, key)).resolves.toBe('stored');
      await expect(storage.get(APP_B, key)).resolves.toBeNull();
      await storage.delete(APP_A, key);
      await expect(storage.get(APP_A, key)).resolves.toBeNull();
    },
  );

  it('starts empty for each new provider instance', async () => {
    const first = createMemoryStorageProvider();
    await first.set(APP_A, 'settings', 'stored');

    const second = createMemoryStorageProvider();

    await expect(second.get(APP_A, 'settings')).resolves.toBeNull();
    await expect(first.get(APP_A, 'settings')).resolves.toBe('stored');
  });
});

const connections: Array<() => void> = [];

afterEach(() => {
  for (const close of connections.splice(0)) {
    close();
  }
});

/** A test connection using a host-selected identity and the production provider. */
function connectApp(id: string, storage: StorageProvider, grantedScopes = ['storage']) {
  const bridge = createLinkedTransports();
  const client = createClient({ transport: bridge.a });
  createHost({
    hostInfo: { name: 'storage-test-host', version: '0.1.0', platform: 'browser' },
    manifest: {
      manifestVersion: 1,
      id,
      name: 'Storage test',
      version: '1.0.0',
      entry: 'index.html',
      protocolVersion: '0.1',
      permissions: ['storage'],
    },
    grantedScopes,
    environment: { locale: 'en', colorScheme: 'light' },
    capabilities: { storage },
  }).connect(bridge.b);
  connections.push(() => {
    client.close();
    bridge.b.close();
  });
  return client;
}

describe('T03 — production storage provider through the bridge', () => {
  it('isolates two apps and preserves stored data across repeat initialization', async () => {
    const storage = createMemoryStorageProvider();
    const alpha = connectApp(APP_A, storage);
    const beta = connectApp(APP_B, storage);
    await alpha.initialize();
    await beta.initialize();

    await expect(alpha.call('storage.set', { key: 'settings', value: 'alpha' })).resolves.toEqual(
      {},
    );
    await expect(beta.call('storage.set', { key: 'settings', value: 'beta' })).resolves.toEqual({});
    await expect(alpha.call('storage.get', { key: 'settings' })).resolves.toEqual({
      value: 'alpha',
    });
    await expect(beta.call('storage.get', { key: 'settings' })).resolves.toEqual({ value: 'beta' });

    await expect(alpha.call('storage.delete', { key: 'settings' })).resolves.toEqual({});
    await expect(alpha.call('storage.get', { key: 'settings' })).resolves.toEqual({ value: null });
    await beta.initialize();
    await expect(beta.call('storage.get', { key: 'settings' })).resolves.toEqual({ value: 'beta' });
  });

  it('denies an ungranted write without changing data even when storage is installed', async () => {
    const storage = createMemoryStorageProvider();
    await storage.set(APP_A, 'settings', 'original');
    const client = connectApp(APP_A, storage, []);
    await client.initialize();

    await expect(
      client.call('storage.set', { key: 'settings', value: 'forged' }),
    ).rejects.toMatchObject({
      code: ERROR_CODES.PERMISSION_DENIED,
    });
    await expect(storage.get(APP_A, 'settings')).resolves.toBe('original');
  });
});
