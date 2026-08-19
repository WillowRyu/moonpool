/**
 * @moonpool/host — kernel host: dispatcher, permission gate, manifest parsing.
 *
 * Pure by design: nothing here may import a platform API (CLAUDE.md, SPEC §3).
 *
 * Skeleton only — the failing tests in `test/` are the contract to implement.
 */
import type { HostInfo, MiniAppManifest, PortalEnvironment, Transport } from '@moonpool/protocol';

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

export function createHost(_config: HostConfig): Host {
  throw new Error(
    'Not implemented: createHost — start from the failing tests in packages/host/test',
  );
}
