/**
 * @moonpool/host — kernel host: dispatcher, permission gate, manifest parsing.
 *
 * Pure by design: nothing here may import a platform API (CLAUDE.md, SPEC §3).
 *
 * Skeleton only — the failing tests in `test/` are the contract to implement.
 */

import type { HostInfo, MiniAppManifest, PortalEnvironment, Transport } from '@moonpool/protocol';
import {
  ERROR_CODES,
  hasRequestId,
  isJsonRpcRequest,
  PORTAL_METHODS,
  PROTOCOL_VERSION,
} from '@moonpool/protocol';

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
}

export interface Host {
  /** Attach one Portal's bridge connection. */
  connect(transport: Transport): void;
}

export function createHost(config: HostConfig): Host {
  return {
    connect(transport) {
      let initialized = false;

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
              grantedScopes: config.manifest.permissions.filter((scope) =>
                config.grantedScopes.includes(scope),
              ),
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
