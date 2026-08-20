/**
 * @moonpool/client — kernel client: JSON-RPC encoding, promise correlation,
 * timeout, error mapping. Runs inside the mini app.
 *
 * Pure by design: nothing here may import a platform API (CLAUDE.md, SPEC §3).
 *
 * Skeleton only — the failing tests in `test/` are the contract to implement.
 */
import {
  ERROR_CODES,
  type InitializeResult,
  isJsonRpcResponse,
  type JsonValue,
  PORTAL_METHODS,
  PROTOCOL_VERSION,
  type Transport,
} from '@moonpool/protocol';

/**
 * The only host-environment globals this package touches. Declared narrowly
 * on purpose: adding "DOM" or @types/node to typecheck these would also make
 * `window`/`process` compile inside a package that must stay portable.
 */
declare const setTimeout: (handler: () => void, timeoutMs: number) => unknown;
declare const clearTimeout: (handle: unknown) => void;

/** SPEC §4.5 — every request is on a clock; this is how long it runs by default. */
const DEFAULT_TIMEOUT_MS = 30_000;

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

  /** Handle of the §4.5 timer, cleared the moment the request settles. */
  timer: unknown;
}

export function createClient(config: ClientConfig): MoonpoolClient {
  const { transport } = config;
  const protocolVersion = config.protocolVersion ?? PROTOCOL_VERSION;

  /** id → the promise waiting on it. A Map, not an object: ids arrive from off-connection. */
  const pending = new Map<number, Pending>();
  /** SPEC §4.1: ids are positive integers, unique per connection. */
  let nextId = 1;
  const timeoutMs = config.timeoutMs ?? DEFAULT_TIMEOUT_MS;

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
    clearTimeout(entry.timer);

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
      const timer = setTimeout(() => {
        // SPEC §4.5: discard the entry first, so a late reply for this id
        // finds nothing to settle and is ignored.
        pending.delete(id);
        reject(
          new MoonpoolError(ERROR_CODES.TIMEOUT, `no response to ${method} within ${timeoutMs} ms`),
        );
      }, timeoutMs);

      pending.set(id, { resolve, reject, timer });

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

      // SPEC §4.6: nothing may stay pending across a close. Snapshot and clear
      // before settling — the same discard-then-settle order as the return
      // desk and the timeout path.
      const abandoned = [...pending.values()];
      pending.clear();

      for (const entry of abandoned) {
        clearTimeout(entry.timer);
        entry.reject(
          new MoonpoolError(
            ERROR_CODES.CONNECTION_CLOSED,
            'the bridge connection was closed before the host answered',
          ),
        );
      }

      transport.close();
    },
  };
}
