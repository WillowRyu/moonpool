/**
 * @moonpool/host — kernel host: request dispatch and scope enforcement.
 *
 * Pure by design: nothing here may import a platform API (CLAUDE.md, SPEC §3).
 *
 * The kernel owns initialization, request routing, and permission checks.
 * The embedding application supplies the actual capability implementations.
 */

import type {
  HostInfo,
  JsonRpcResponse,
  JsonValue,
  MiniAppManifest,
  PortalEnvironment,
  ProfileGetResult,
  StorageGetResult,
  StorageSetValue,
  Transport,
} from '@moonpool/protocol';
import {
  ERROR_CODES,
  hasOnlyParamKeys,
  hasRequestId,
  isJsonRpcRequest,
  isJsonRpcRequestEnvelope,
  isStorageDeleteParams,
  isStorageGetParams,
  isStorageSetParams,
  PORTAL_METHODS,
  PORTAL_NAMESPACE,
  PROFILE_METHODS,
  PROTOCOL_VERSION,
  STORAGE_METHODS,
} from '@moonpool/protocol';

export { parseManifest } from './manifest';
export { ManifestError } from './manifest-fields';

/**
 * The only host-environment global this package touches. Declared narrowly
 * on purpose, the way the client declares `setTimeout`: adding "DOM" or
 * @types/node to typecheck it would also make `window`/`process` compile
 * inside a package that must stay portable. WHATWG-defined; present in every
 * browser and in Node.
 */
declare const queueMicrotask: (callback: () => void) => void;

/**
 * SPEC §6.3 `profile.*`, supplied by the embedding host. The kernel never
 * knows who the user is; it checks the scope, then asks.
 */
export interface ProfileProvider {
  get(): Promise<ProfileGetResult>;
}

/**
 * SPEC §6.3 — storage supplied by the embedding host, async per §9.5.
 * The kernel passes its manifest's app id separately from the caller's key
 * (ADR 0003). The provider MUST partition data by that id; receiving the
 * argument alone does not enforce isolation. Storage layout and platform
 * APIs belong in this implementation, outside the pure kernel (SPEC §3).
 */
export interface StorageProvider {
  /** Return the app's stored value, or null only when its key is absent (ADR 0004). */
  get(miniAppId: string, key: string): Promise<JsonValue>;
  /** Resolve after the write completes; the kernel then sends the empty success result. */
  set(miniAppId: string, key: string, value: StorageSetValue): Promise<void>;
  /** Resolve after deletion completes; the kernel then sends the empty success result. */
  delete(miniAppId: string, key: string): Promise<void>;
}

/**
 * Capability handlers, one slot per §6.3 namespace — the "Capability
 * handlers" layer of SPEC §3. A slot the host leaves empty answers `-32001`.
 * These are executable implementations. Their presence does not grant the
 * caller permission: grantedScopes is checked separately at dispatch (§9.3).
 */
export interface HostCapabilities {
  profile?: ProfileProvider;
  storage?: StorageProvider;
}

export interface HostConfig {
  hostInfo: HostInfo;
  /** Parsed `moonpool.json` of the mini app this connection serves (SPEC §7). */
  manifest: MiniAppManifest;
  /**
   * Scopes the host actually grants. The handshake reports the intersection
   * of this and `manifest.permissions` as `grantedScopes` (SPEC §5).
   */
  grantedScopes: string[];
  environment: PortalEnvironment;
  /** The scoped capabilities this host implements. A host MAY offer none. */
  capabilities?: HostCapabilities;
}

export interface Host {
  /** Attach one Portal's bridge connection. */
  connect(transport: Transport): void;
}

export function createHost(config: HostConfig): Host {
  return {
    connect(transport) {
      let initialized = false;
      // SPEC §4.1 / §5.1: largest id consumed by this connection's current document.
      let lastRequestId = 0;

      // SPEC §5: "grantedScopes is the authoritative permission set for the
      // connection" — the intersection of what the manifest declares and what
      // this host grants. Computed once per connection: it is origin-scoped
      // consent, so a repeat handshake (§5.1) MUST NOT touch it.
      const grantedScopes = config.manifest.permissions.filter((scope) => {
        return config.grantedScopes.includes(scope);
      });

      /**
       * SPEC §4.2 / ADR 0006 — reply once when params contains unsupported names.
       * Call from a known method's branch, after any required scope check.
       * Returns true after rejection so the caller can stop before provider access.
       */
      function rejectUnknownParams(
        id: number,
        params: JsonValue | undefined,
        allowedKeys: readonly string[],
      ): boolean {
        if (hasOnlyParamKeys(params, allowedKeys)) {
          return false;
        }

        transport.send({
          jsonrpc: '2.0',
          id,
          error: {
            code: ERROR_CODES.INVALID_PARAMS,
            message: 'params contains unsupported fields',
          },
        });
        return true;
      }

      // Provider calls live in async helpers so the dispatcher below stays
      // synchronous: one branch, one reply, `return`.
      // `await` inside `try` catches a provider that rejects AND one that
      // throws synchronously; either way the mini app gets exactly one reply,
      // and the provider's own error text stays on the host side (§4.4).
      async function invokeProfileGet(id: number, provider: ProfileProvider): Promise<void> {
        try {
          const profile = await provider.get();
          // Allowlist on the way out. A provider that hands back its whole
          // user record must not leak the extra fields, and an `undefined`
          // must not cross a structured-clone transport as a non-JSON value.
          // Only the §6.3 fields, only when set.
          const result: ProfileGetResult = { displayName: profile.displayName };
          if (profile.avatarUrl !== undefined) {
            result.avatarUrl = profile.avatarUrl;
          }
          transport.send({ jsonrpc: '2.0', id, result });
        } catch (error) {
          transport.send({
            jsonrpc: '2.0',
            id,
            error: {
              code: ERROR_CODES.INTERNAL_ERROR,
              message: `${PROFILE_METHODS.GET} failed inside the host`,
            },
          });
          // Isolate, but do not swallow (same decision as the transport's
          // handler isolation, E2.1). Re-thrown with no caller above it, the
          // provider's error surfaces as an uncaught error / window.onerror
          // on the HOST side — never in the reply (§4.4).
          queueMicrotask(() => {
            throw error;
          });
        }
      }

      /**
       * SPEC §6.3 — wrap the provider's raw value in the wire result { value }.
       * Dispatch has already checked scope, key, and provider availability.
       * Like profile.get, provider failures get one sanitized reply while
       * the original error remains observable on the host (§4.4).
       */
      async function invokeStorageGet(
        id: number,
        key: string,
        provider: StorageProvider,
      ): Promise<void> {
        try {
          // Identity comes from host-held configuration, never from params.
          // Keep it separate from the key so each provider can choose its
          // own storage layout without changing the bridge contract (ADR 0003).
          const value = await provider.get(config.manifest.id, key);
          const result: StorageGetResult = { value };
          transport.send({ jsonrpc: '2.0', id, result });
        } catch (error) {
          transport.send({
            jsonrpc: '2.0',
            id,
            error: {
              code: ERROR_CODES.INTERNAL_ERROR,
              message: `${STORAGE_METHODS.GET} failed inside the host`,
            },
          });
          // Queue the host-side report after sending the error reply, using
          // the same uncaught-error reporting policy as profile.get.
          queueMicrotask(() => {
            throw error;
          });
        }
      }

      /**
       * SPEC §6.3 — acknowledge the write with {}, only after it completes.
       * The provider's Promise<void> signals completion; it supplies no wire
       * result. Input rejection happens before this helper can mutate storage.
       */
      async function invokeStorageSet(
        id: number,
        key: string,
        value: StorageSetValue,
        provider: StorageProvider,
      ): Promise<void> {
        try {
          // Reads and writes must use the same host-selected app identity.
          // Await completion before telling the mini app its write succeeded.
          await provider.set(config.manifest.id, key, value);
          transport.send({ jsonrpc: '2.0', id, result: {} });
        } catch (error) {
          transport.send({
            jsonrpc: '2.0',
            id,
            error: {
              code: ERROR_CODES.INTERNAL_ERROR,
              message: `${STORAGE_METHODS.SET} failed inside the host`,
            },
          });
          // Keep the original failure visible on the host without exposing
          // provider error details to the mini app (§4.4, as in the read path).
          queueMicrotask(() => {
            throw error;
          });
        }
      }

      /**
       * SPEC §6.3 — acknowledge deletion with {}, only after it completes.
       * Dispatch has already checked scope, key, and provider availability.
       * Provider failures follow the same host-only reporting policy as get/set.
       */
      async function invokeStorageDelete(
        id: number,
        key: string,
        provider: StorageProvider,
      ): Promise<void> {
        try {
          // Use the same host-selected identity as reads and writes (ADR 0003).
          // Await completion before telling the mini app deletion succeeded.
          await provider.delete(config.manifest.id, key);
          transport.send({ jsonrpc: '2.0', id, result: {} });
        } catch (error) {
          transport.send({
            jsonrpc: '2.0',
            id,
            error: {
              code: ERROR_CODES.INTERNAL_ERROR,
              message: `${STORAGE_METHODS.DELETE} failed inside the host`,
            },
          });
          // Report the original failure on the host without exposing provider
          // error details to the mini app (SPEC §4.4).
          queueMicrotask(() => {
            throw error;
          });
        }
      }

      transport.onMessage((message) => {
        // SPEC §4.1: reject the whole array before notifications or session state.
        // There is no single request id; never dispatch members or echo one of theirs.
        if (Array.isArray(message)) {
          const response: JsonRpcResponse = {
            jsonrpc: '2.0',
            id: null,
            error: {
              code: ERROR_CODES.INVALID_REQUEST,
              message: 'batch requests are not supported',
            },
          };
          transport.send(response);
          return;
        }

        if (!hasRequestId(message)) {
          // SPEC §4.1: no id means a notification (or not a request at
          // all) — never answered, no matter how malformed the rest is.
          return;
        }

        const { id } = message;

        // A well-shaped initialize is the document boundary, even if its fields
        // or version will fail later. Malformed containers/names cannot reset it.
        if (message.method === PORTAL_METHODS.INITIALIZE && isJsonRpcRequest(message)) {
          lastRequestId = 0;
        }

        if (Number.isInteger(id) && id > 0) {
          if (id <= lastRequestId) {
            // Never echo an ambiguous id: an earlier provider may still be running.
            const response: JsonRpcResponse = {
              jsonrpc: '2.0',
              id: null,
              error: {
                code: ERROR_CODES.INVALID_REQUEST,
                message: 'request ids must increase within a document',
              },
            };
            transport.send(response);
            return;
          }
          // Reserve before validation/dispatch, including failures and async work.
          lastRequestId = id;
        }

        // SPEC §4.2 / ADR 0005 — distinguish a malformed envelope from bad params.
        // Neither check may reach handshake processing or a capability provider.
        if (!isJsonRpcRequestEnvelope(message)) {
          transport.send({
            jsonrpc: '2.0',
            id,
            error: {
              code: ERROR_CODES.INVALID_REQUEST,
              message:
                'malformed request: expected jsonrpc 2.0, a positive integer id, and a namespace.action method',
            },
          });
          return;
        }

        if (!isJsonRpcRequest(message)) {
          transport.send({
            jsonrpc: '2.0',
            id,
            error: {
              code: ERROR_CODES.INVALID_PARAMS,
              message: 'params must be an object or omitted',
            },
          });
          return;
        }

        const { method } = message;

        // SPEC §5.1: a repeat handshake is ordinary traffic — a reload, a link
        // in a multi-page mini app, a web view recovering from renderer
        // termination (ADR 0002). Each one is a new document with no memory,
        // and this message is the only signal the host gets that it happened.
        // Answer it the same way every time.
        //
        // The id floor was reset and this initialization's id consumed above.
        // Reset initialization here before method-level checks. Origin-scoped
        // state — rate limits, consent records, storage — MUST NOT be touched.
        if (method === PORTAL_METHODS.INITIALIZE) {
          // SPEC §5.1 — a repeat handshake starts a new document's negotiation.
          // Reset before any method-level rejection so the new document cannot
          // inherit a previous successful handshake. Origin-scoped grants and
          // storage remain unchanged.
          initialized = false;

          // SPEC §4.2 — initialization accepts only its declared version input.
          if (rejectUnknownParams(id, message.params, ['protocolVersion'])) {
            return;
          }

          const requested = message.params?.protocolVersion;

          // SPEC §5 / ADR 0007 — validate the input type before version negotiation.
          // Missing params or a missing field yields undefined. Reject without
          // converting numbers, arrays, or other values into strings.
          if (typeof requested !== 'string') {
            transport.send({
              jsonrpc: '2.0',
              id,
              error: {
                code: ERROR_CODES.INVALID_PARAMS,
                message: 'portal.initialize requires a string protocolVersion',
              },
            });
            return;
          }

          if (requested !== PROTOCOL_VERSION) {
            transport.send({
              jsonrpc: '2.0',
              id,
              error: {
                code: ERROR_CODES.PROTOCOL_VERSION_UNSUPPORTED,
                message: `unsupported protocolVersion; this host speaks ${PROTOCOL_VERSION}`,
              },
            });
            return;
          }

          initialized = true;
          transport.send({
            jsonrpc: '2.0',
            id,
            result: {
              protocolVersion: PROTOCOL_VERSION,
              miniApp: { id: config.manifest.id, version: config.manifest.version },
              host: { ...config.hostInfo },
              grantedScopes: [...grantedScopes],
              environment: { ...config.environment },
            },
          });
          return;
        }

        if (!initialized) {
          transport.send({
            jsonrpc: '2.0',
            id,
            error: {
              code: ERROR_CODES.NOT_INITIALIZED,
              message: 'portal.initialize must be the first request on the connection',
            },
          });
          return;
        }

        if (method === PORTAL_METHODS.PING) {
          // SPEC §4.2 — this method defines no params members.
          if (rejectUnknownParams(id, message.params, [])) {
            return;
          }

          transport.send({ jsonrpc: '2.0', id, result: { pong: true } });
          return;
        }

        // SPEC §9.3 — scope enforcement at dispatch. The namespace IS the
        // scope (§6.1). Checked before the method lookup, so a namespace the
        // connection was not granted answers -32000 for every name, real or
        // not: it cannot be enumerated. Only `portal` is exempt (§6.2), and
        // only by exact match.
        const namespace = method.split('.')[0] ?? '';
        if (namespace !== PORTAL_NAMESPACE && !grantedScopes.includes(namespace)) {
          transport.send({
            jsonrpc: '2.0',
            id,
            error: {
              code: ERROR_CODES.PERMISSION_DENIED,
              message: `scope '${namespace}' not granted to this mini app`,
              data: { scope: namespace },
            },
          });
          return;
        }

        if (method === PROFILE_METHODS.GET) {
          // SPEC §4.2 — this method defines no params members.
          if (rejectUnknownParams(id, message.params, [])) {
            return;
          }

          const provider = config.capabilities?.profile;
          if (provider === undefined) {
            transport.send({
              jsonrpc: '2.0',
              id,
              error: {
                code: ERROR_CODES.CAPABILITY_UNAVAILABLE,
                message: `${method} is not available on this host`,
              },
            });
            return;
          }
          void invokeProfileGet(id, provider);
          return;
        }

        // SPEC §9.3 / §9.6 — the scope gate above must run first, then
        // required params are checked before provider availability or access.
        // The provider receives only the validated key plus the host's id.
        if (method === STORAGE_METHODS.GET) {
          // SPEC §4.2 / ADR 0003 — only the key comes from the caller.
          if (rejectUnknownParams(id, message.params, ['key'])) {
            return;
          }

          const params = message.params;

          if (!isStorageGetParams(params)) {
            transport.send({
              jsonrpc: '2.0',
              id,
              error: {
                code: ERROR_CODES.INVALID_PARAMS,
                message: 'storage.get requires a string key',
              },
            });
            return;
          }

          const provider = config.capabilities?.storage;
          if (provider === undefined) {
            transport.send({
              jsonrpc: '2.0',
              id,
              error: {
                code: ERROR_CODES.CAPABILITY_UNAVAILABLE,
                message: `${method} is not available on this host`,
              },
            });
            return;
          }

          void invokeStorageGet(id, params.key, provider);
          return;
        }

        // ADR 0004 — reject a missing/null value before any mutation so a
        // rejected write leaves existing data intact. Preserve the same
        // scope → params → availability → invocation order as storage.get.
        if (method === STORAGE_METHODS.SET) {
          // SPEC §4.2 — check names here; value contents remain application data.
          if (rejectUnknownParams(id, message.params, ['key', 'value'])) {
            return;
          }

          const params = message.params;

          if (!isStorageSetParams(params)) {
            transport.send({
              jsonrpc: '2.0',
              id,
              error: {
                code: ERROR_CODES.INVALID_PARAMS,
                message: 'storage.set requires a string key and a non-null JSON value',
              },
            });
            return;
          }

          const provider = config.capabilities?.storage;
          if (provider === undefined) {
            transport.send({
              jsonrpc: '2.0',
              id,
              error: {
                code: ERROR_CODES.CAPABILITY_UNAVAILABLE,
                message: `${method} is not available on this host`,
              },
            });
            return;
          }

          void invokeStorageSet(id, params.key, params.value, provider);
          return;
        }

        // SPEC §9.3 / §9.6 — the scope gate above runs first.
        // Validate the key before checking availability or invoking deletion.
        if (method === STORAGE_METHODS.DELETE) {
          // SPEC §4.2 / ADR 0003 — only the key comes from the caller.
          if (rejectUnknownParams(id, message.params, ['key'])) {
            return;
          }

          const params = message.params;

          if (!isStorageDeleteParams(params)) {
            transport.send({
              jsonrpc: '2.0',
              id,
              error: {
                code: ERROR_CODES.INVALID_PARAMS,
                message: 'storage.delete requires a string key',
              },
            });
            return;
          }

          const provider = config.capabilities?.storage;

          if (provider === undefined) {
            transport.send({
              jsonrpc: '2.0',
              id,
              error: {
                code: ERROR_CODES.CAPABILITY_UNAVAILABLE,
                message: `${method} is not available on this host`,
              },
            });
            return;
          }

          void invokeStorageDelete(id, params.key, provider);
          return;
        }

        transport.send({
          jsonrpc: '2.0',
          id,
          error: {
            code: ERROR_CODES.METHOD_NOT_FOUND,
            message: `unknown method: ${method}`,
          },
        });
      });
    },
  };
}
