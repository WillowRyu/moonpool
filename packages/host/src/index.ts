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
        if (!isJsonRpcRequest(message)) {
          // SPEC §4.1: notifications (and malformed frames) are never answered.
          return;
        }

        const { id, method } = message;

        if (!initialized && method === PORTAL_METHODS.INITIALIZE) {
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
