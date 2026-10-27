/** SPEC §6.3 — provider methods retain their instance state at invocation. */
import { createHost } from '@moonpool/host';
import type { JsonValue, StorageSetValue } from '@moonpool/protocol';
import { describe, expect, it } from 'vitest';
import { createLinkedTransports, flush } from '../../../test-support/memory-transport';

class StatefulProfile {
  private readonly record = { displayName: 'Public name', hostSecret: 'never expose' };

  async get() {
    return this.record;
  }
}

class StatefulStorage {
  private readonly entries = new Map<string, JsonValue>();
  readonly calls: Array<[string, string, string]> = [];

  async get(miniAppId: string, key: string): Promise<JsonValue> {
    this.calls.push(['get', miniAppId, key]);
    return this.entries.get(key) ?? null;
  }

  async set(miniAppId: string, key: string, value: StorageSetValue): Promise<void> {
    this.calls.push(['set', miniAppId, key]);
    this.entries.set(key, value);
  }

  async delete(miniAppId: string, key: string): Promise<void> {
    this.calls.push(['delete', miniAppId, key]);
    this.entries.delete(key);
  }
}

function connect(storage = new StatefulStorage()) {
  const { a, b } = createLinkedTransports();
  createHost({
    hostInfo: { name: 'test-host', version: '1.0.0', platform: 'browser' },
    manifest: {
      manifestVersion: 1,
      id: 'com.example.receiver',
      name: 'Receiver',
      version: '1.0.0',
      entry: 'index.html',
      protocolVersion: '0.1',
      permissions: ['profile', 'storage'],
    },
    grantedScopes: ['profile', 'storage'],
    environment: { locale: 'en', colorScheme: 'light' },
    capabilities: { profile: new StatefulProfile(), storage },
  }).connect(b);
  const replies: JsonValue[] = [];
  a.onMessage((message) => replies.push(message));
  return {
    async call(id: number, method: string, params?: Record<string, JsonValue>) {
      a.send({ jsonrpc: '2.0', id, method, ...(params === undefined ? {} : { params }) });
      await flush();
      return replies.at(-1);
    },
    close() {
      a.close();
      b.close();
    },
  };
}

describe('stateful capability providers', () => {
  it('keeps the profile receiver and projects only public fields', async () => {
    const client = connect();
    try {
      await client.call(1, 'portal.initialize', { protocolVersion: '0.1' });
      await expect(client.call(2, 'profile.get')).resolves.toEqual({
        jsonrpc: '2.0',
        id: 2,
        result: { displayName: 'Public name' },
      });
    } finally {
      client.close();
    }
  });

  it('keeps the storage receiver and host-selected identity across CRUD', async () => {
    const storage = new StatefulStorage();
    const client = connect(storage);
    try {
      await client.call(1, 'portal.initialize', { protocolVersion: '0.1' });
      await expect(client.call(2, 'storage.set', { key: 'theme', value: false })).resolves.toEqual({
        jsonrpc: '2.0',
        id: 2,
        result: {},
      });
      await expect(client.call(3, 'storage.get', { key: 'theme' })).resolves.toEqual({
        jsonrpc: '2.0',
        id: 3,
        result: { value: false },
      });
      await expect(client.call(4, 'storage.delete', { key: 'theme' })).resolves.toEqual({
        jsonrpc: '2.0',
        id: 4,
        result: {},
      });
      await expect(client.call(5, 'storage.get', { key: 'theme' })).resolves.toEqual({
        jsonrpc: '2.0',
        id: 5,
        result: { value: null },
      });
      expect(storage.calls).toEqual([
        ['set', 'com.example.receiver', 'theme'],
        ['get', 'com.example.receiver', 'theme'],
        ['delete', 'com.example.receiver', 'theme'],
        ['get', 'com.example.receiver', 'theme'],
      ]);
    } finally {
      client.close();
    }
  });
});
