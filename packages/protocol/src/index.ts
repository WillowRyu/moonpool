/**
 * @moonpool/protocol — shared types and constants for the Moonpool bridge.
 *
 * This package is pure by design: nothing here may import a platform API.
 * That rule (CLAUDE.md, SPEC.md §3) is what keeps the native ports cheap later.
 */

/** Any value representable in JSON. The bridge carries nothing else. */
export type JsonValue =
  | null
  | boolean
  | number
  | string
  | JsonValue[]
  | { [key: string]: JsonValue };

/**
 * SPEC §3.1 — the entire platform boundary.
 *
 * A transport MUST deliver messages in order and MUST NOT modify payloads.
 */
export interface Transport {
  send(message: JsonValue): void;
  /** Registers a handler; returns an unsubscribe function. */
  onMessage(handler: (message: JsonValue) => void): () => void;
  close(): void;
}

/** The protocol version this implementation speaks. Negotiation is exact-match in 0.x (SPEC §5). */
export const PROTOCOL_VERSION = '0.1';

/** SPEC §4.4 — standard JSON-RPC codes plus the Moonpool implementation-defined range. */
export const ERROR_CODES = {
  PARSE_ERROR: -32700,
  INVALID_REQUEST: -32600,
  METHOD_NOT_FOUND: -32601,
  INVALID_PARAMS: -32602,
  INTERNAL_ERROR: -32603,
  PERMISSION_DENIED: -32000,
  CAPABILITY_UNAVAILABLE: -32001,
  USER_CANCELLED: -32002,
  TIMEOUT: -32003,
  PROTOCOL_VERSION_UNSUPPORTED: -32004,
  NOT_INITIALIZED: -32005,
  RATE_LIMITED: -32006,
  HOST_UNAVAILABLE: -32007,
  CONNECTION_CLOSED: -32008,
} as const;

export type ErrorCode = (typeof ERROR_CODES)[keyof typeof ERROR_CODES];

export type HostPlatform = 'browser' | 'ios' | 'android';

export interface HostInfo {
  name: string;
  version: string;
  platform: HostPlatform;
}

export interface PortalEnvironment {
  locale: string;
  colorScheme: 'light' | 'dark';
}

/** SPEC §5 — successful result of `portal.initialize`. */
export interface InitializeResult {
  protocolVersion: string;
  miniApp: { id: string; version: string };
  host: HostInfo;
  /** Intersection of manifest permissions and what the host actually granted. */
  grantedScopes: string[];
  environment: PortalEnvironment;
}

/** SPEC §7 — `moonpool.json`, shipped at every mini app's package root. */
export interface MiniAppManifest {
  manifestVersion: 1;
  /** Reverse-DNS, immutable across versions. */
  id: string;
  name: string;
  version: string;
  /** Relative path; MUST NOT escape the package root. */
  entry: string;
  protocolVersion: string;
  /** Declared scopes. MAY be empty. */
  permissions: string[];
}

/** Narrow a JSON value to a plain object (not null, not an array). */
export function isJsonObject(value: JsonValue | undefined): value is { [key: string]: JsonValue } {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/**
 * SPEC §4.2 — a request carrying an id. Deliberately a type alias, not an
 * interface: aliases get an implicit index signature, so the guard below
 * may narrow `JsonValue` to it.
 */
export type JsonRpcRequest = {
  jsonrpc: '2.0';
  id: number;
  method: string;
  params?: { [key: string]: JsonValue };
};

/** Checked proof that a frame is a §4.2 request (notifications excluded). */
export function isJsonRpcRequest(value: JsonValue | undefined): value is JsonRpcRequest {
  return (
    isJsonObject(value) &&
    value.jsonrpc === '2.0' &&
    typeof value.id === 'number' &&
    typeof value.method === 'string' &&
    (value.params === undefined || isJsonObject(value.params))
  );
}

/** SPEC §6.2 — reserved core methods; the `portal` namespace needs no scope. */
export const PORTAL_METHODS = {
  INITIALIZE: 'portal.initialize',
  PING: 'portal.ping',
  CLOSE: 'portal.close',
} as const;

/**
 * SPEC §4.3 — a response to a request. Exactly one of `result` / `error`.
 * A type alias, not an interface, for the same reason as `JsonRpcRequest`.
 */
export type JsonRpcResponse = {
  jsonrpc: '2.0';
  id: number;
  result?: JsonValue;
  error?: { code: number; message: string; data?: JsonValue };
};

/** Checked proof that a frame is a §4.3 response. */
export function isJsonRpcResponse(value: JsonValue | undefined): value is JsonRpcResponse {
  if (!isJsonObject(value) || value.jsonrpc !== '2.0' || typeof value.id !== 'number') {
    return false;
  }

  const hasResult = value.result !== undefined;
  const hasError = value.error !== undefined;
  // SPEC §4.3: exactly one of the two. Both or neither is a malformed frame.
  if (hasResult === hasError) {
    return false;
  }
  if (!hasError) {
    return true;
  }

  const error = value.error;
  return isJsonObject(error) && typeof error.code === 'number' && typeof error.message === 'string';
}

/**
 * SPEC §4.1 — a frame with a numeric `id` can expect exactly one reply, even
 * if it turns out to be malformed in some other way. A frame that fails this
 * MUST NOT be answered: it is a notification (or not a request at all).
 */
export function hasRequestId(
  value: JsonValue | undefined,
): value is { [key: string]: JsonValue } & { id: number } {
  return isJsonObject(value) && typeof value.id === 'number';
}
