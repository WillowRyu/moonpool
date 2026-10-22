import type { StorageProvider } from '@moonpool/host';
import type { StorageSetValue } from '@moonpool/protocol';

/**
 * Development-only storage for SPEC §6.3, partitioned by app id (ADR 0003).
 * The kernel supplies the identity and validates input before provider access
 * (SPEC §9.3 / §9.6). Each factory call creates independent in-memory state;
 * retain the returned provider across handshakes, not across host restarts.
 */
export function createMemoryStorageProvider(): StorageProvider {
  const apps = new Map<string, Map<string, StorageSetValue>>();

  return {
    async get(miniAppId, key) {
      // ADR 0004: only absence becomes null; preserve false, 0, and "".
      return apps.get(miniAppId)?.get(key) ?? null;
    },
    async set(miniAppId, key, value) {
      let entries = apps.get(miniAppId);
      if (entries === undefined) {
        entries = new Map<string, StorageSetValue>();
        apps.set(miniAppId, entries);
      }
      entries.set(key, value);
    },
    async delete(miniAppId, key) {
      // Missing apps and keys need no mutation; other app maps stay untouched.
      apps.get(miniAppId)?.delete(key);
    },
  };
}
