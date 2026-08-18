/**
 * @moonpool/client — kernel client: JSON-RPC encoding, promise correlation,
 * timeout, error mapping. Runs inside the mini app.
 *
 * Pure by design: nothing here may import a platform API (CLAUDE.md, SPEC §3).
 *
 * Skeleton only — the failing tests in `test/` are the contract to implement.
 */
import type { InitializeResult, Transport } from '@moonpool/protocol';

export interface ClientConfig {
  transport: Transport;
  /** Protocol version to request in the handshake. Defaults to PROTOCOL_VERSION. */
  protocolVersion?: string;
  /** Per-request timeout in milliseconds. Defaults to 30_000 (SPEC §4.5). */
  timeoutMs?: number;
}

export interface MoonpoolClient {
  /** SPEC §5 — performs the handshake. MUST be the first request on the connection. */
  initialize(): Promise<InitializeResult>;
  /** Calls a capability, e.g. `call('profile.get')`. */
  call(method: string, params?: Record<string, unknown>): Promise<unknown>;
  close(): void;
}

export function createClient(config: ClientConfig): MoonpoolClient {
  throw new Error('Not implemented: createClient — start from the failing tests in packages/client/test');
}
