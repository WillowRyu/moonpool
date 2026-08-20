/**
 * @moonpool/client — kernel client: JSON-RPC encoding, promise correlation,
 * timeout, error mapping. Runs inside the mini app.
 *
 * Pure by design: nothing here may import a platform API (CLAUDE.md, SPEC §3).
 *
 * Skeleton only — the failing tests in `test/` are the contract to implement.
 */
import {
  type InitializeResult,
  isJsonRpcResponse,
  type JsonValue,
  PORTAL_METHODS,
  PROTOCOL_VERSION,
  type Transport,
} from '@moonpool/protocol';

/** What a rejected bridge call hands the mini app: the SPEC §4.4 code survives the trip. */
export class MoonpoolError extends Error {
  readonly code: number;
  readonly data?: JsonValue;

  constructor(code: number, message: string, data?: JsonValue) {
    super(message);
    this.name = 'MoonpoolError';
    this.code = code;
    this.data = data;
  }
}
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
  call(method: string, params?: Record<string, JsonValue>): Promise<unknown>;
  close(): void;
}

/** One in-flight request: the promise's settle functions, parked until its reply lands. */
interface Pending {
  resolve: (value: unknown) => void;
  reject: (reason: unknown) => void;
}

export function createClient(config: ClientConfig): MoonpoolClient {
  const { transport } = config;
  const protocolVersion = config.protocolVersion ?? PROTOCOL_VERSION;

  /** id → the promise waiting on it. A Map, not an object: ids arrive from off-connection. */
  const pending = new Map<number, Pending>();
  /** SPEC §4.1: ids are positive integers, unique per connection. */
  let nextId = 1;

  // One return desk for the whole connection, registered once.
  const unsubscribe = transport.onMessage((message) => {
    if (!isJsonRpcResponse(message)) {
      return;
    }

    const entry = pending.get(message.id);
    if (entry === undefined) {
      // SPEC §4.5: a reply to an unknown or already-settled id is ignored.
      return;
    }
    pending.delete(message.id);

    const error = message.error;
    if (error !== undefined) {
      entry.reject(new MoonpoolError(error.code, error.message, error.data));
      return;
    }

    entry.resolve(message.result);
  });

  function request(method: string, params?: Record<string, JsonValue>): Promise<unknown> {
    const id = nextId++;

    return new Promise<unknown>((resolve, reject) => {
      pending.set(id, { resolve, reject });

      const frame: { [key: string]: JsonValue } = { jsonrpc: '2.0', id, method };
      if (params !== undefined) {
        frame.params = params;
      }
      transport.send(frame);
    });
  }

  return {
    async initialize() {
      const result = await request(PORTAL_METHODS.INITIALIZE, { protocolVersion });
      // Asymmetric trust: the host is the trusted end of this bridge, so its
      // handshake result is taken at its word. Validating it is future work.
      return result as InitializeResult;
    },
    call(method, params) {
      return request(method, params);
    },
    close() {
      unsubscribe();
      transport.close();
    },
  };
}
