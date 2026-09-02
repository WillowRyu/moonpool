/**
 * @moonpool/host — kernel host: dispatcher, permission gate, manifest parsing.
 *
 * Pure by design: nothing here may import a platform API (CLAUDE.md, SPEC §3).
 *
 * Skeleton only — the failing tests in `test/` are the contract to implement.
 */

import type {
  HostInfo,
  MiniAppManifest,
  PortalEnvironment,
  ProfileGetResult,
  Transport,
} from '@moonpool/protocol';
import {
  ERROR_CODES,
  hasRequestId,
  isJsonRpcRequest,
  PORTAL_METHODS,
  PORTAL_NAMESPACE,
  PROFILE_METHODS,
  PROTOCOL_VERSION,
} from '@moonpool/protocol';

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
 * Capability handlers, one slot per §6.3 namespace — the "Capability
 * handlers" layer of SPEC §3. A slot the host leaves empty answers `-32001`.
 */
export interface HostCapabilities {
  profile?: ProfileProvider;
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

      // SPEC §5: "grantedScopes is the authoritative permission set for the
      // connection" — the intersection of what the manifest declares and what
      // this host grants. Computed once per connection: it is origin-scoped
      // consent, so a repeat handshake (§5.1) MUST NOT touch it.
      const grantedScopes = config.manifest.permissions.filter((scope) => {
        return config.grantedScopes.includes(scope);
      });

      // The one place a provider is invoked. Async work lives here so the
      // dispatcher below stays synchronous: one branch, one reply, `return`.
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

      transport.onMessage((message) => {
        if (!hasRequestId(message)) {
          // SPEC §4.1: no id means a notification (or not a request at
          // all) — never answered, no matter how malformed the rest is.
          return;
        }

        const { id } = message;

        if (!isJsonRpcRequest(message)) {
          transport.send({
            jsonrpc: '2.0',
            id,
            error: {
              code: ERROR_CODES.INVALID_REQUEST,
              message: 'malformed request: expected { jsonrpc: "2.0", id, method, params? }',
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
        // Document-scoped state is reset here. Today `initialized` is all of
        // it and the assignment below covers that; anything document-scoped
        // added later MUST be reset in this branch. Origin-scoped state — rate
        // limits, consent records, storage — MUST NOT be touched.
        if (method === PORTAL_METHODS.INITIALIZE) {
          const requested = message.params?.protocolVersion;

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
