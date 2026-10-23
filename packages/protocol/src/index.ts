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

/**
 * SPEC §6.3 — result of `profile.get`. A type alias, not an interface, for
 * the same reason as `JsonRpcRequest`: the host sends it as a `JsonValue`,
 * and only aliases get the implicit index signature that allows that.
 */
export type ProfileGetResult = {
  displayName: string;
  avatarUrl?: string;
};

/** SPEC §7 — `moonpool.json`, shipped at every mini app's package root. */
export interface MiniAppManifest {
  manifestVersion: 1;
  /** Reverse-DNS, immutable across versions. */
  id: string;
  /** Display name, 1–40 Unicode code points (SPEC §7 / ADR 0010). */
  name: string;
  version: string;
  /** Unencoded relative file path; MUST NOT escape the package root (SPEC §7). */
  entry: string;
  protocolVersion: string;
  /** Declared scopes. MAY be empty. */
  permissions: string[];
}

/** Narrow a JSON value to a plain object (not null, not an array). */
export function isJsonObject(value: JsonValue | undefined): value is { [key: string]: JsonValue } {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

type JsonValueTask = { kind: 'visit'; value: unknown } | { kind: 'complete'; value: object };

/**
 * SPEC §6.3 / §9.6 / ADR 0008 — inspect JSON data without conversion.
 * Accept finite scalars, dense arrays, and ordinary records.
 * Do not mutate input, evaluate getters, or invoke toJSON.
 * An explicit stack supports deep data; completed objects may be shared.
 * This check does not impose size limits or prevent Proxy trap side effects.
 */
export function isJsonValue(value: unknown): value is JsonValue {
  const tasks: JsonValueTask[] = [{ kind: 'visit', value }];
  const states = new Map<object, 'visiting' | 'valid'>();

  try {
    while (tasks.length > 0) {
      const task = tasks.pop();
      // pop() can return undefined in its TypeScript signature.
      if (task === undefined) {
        return false;
      }

      if (task.kind === 'complete') {
        states.set(task.value, 'valid');
        continue;
      }

      const current = task.value;

      // null is valid JSON; storage's top-level null rule is separate.
      if (current === null || typeof current === 'string' || typeof current === 'boolean') {
        continue;
      }

      if (typeof current === 'number') {
        if (!Number.isFinite(current)) {
          return false;
        }
        continue;
      }

      // Reject undefined, functions, symbols, and bigint.
      if (typeof current !== 'object') {
        return false;
      }

      const state = states.get(current);
      if (state === 'visiting') {
        return false;
      }

      if (state === 'valid') {
        continue;
      }

      const array = Array.isArray(current);
      const keys = Reflect.ownKeys(current);
      let arrayLength = 0;

      if (array) {
        const length: unknown = Object.getOwnPropertyDescriptor(current, 'length')?.value;
        // Dense arrays own every index plus their bookkeeping length.
        if (typeof length !== 'number' || keys.length !== length + 1) {
          return false;
        }
        arrayLength = length;
      } else {
        const prototype = Object.getPrototypeOf(current);
        if (prototype !== Object.prototype && prototype !== null) {
          return false;
        }
      }

      states.set(current, 'visiting');
      // The stack processes children before this completion task.
      tasks.push({ kind: 'complete', value: current });

      for (const key of keys) {
        if (typeof key !== 'string') {
          return false;
        }
        if (array && key === 'length') {
          continue;
        }

        if (array) {
          const index = Number(key);
          // Reject named members and non-canonical index spellings.
          if (
            !Number.isInteger(index) ||
            index < 0 ||
            index >= arrayLength ||
            String(index) !== key
          ) {
            return false;
          }
        }

        const descriptor = Object.getOwnPropertyDescriptor(current, key);
        // Inspect stored data without executing an accessor.
        if (
          descriptor === undefined ||
          !descriptor.enumerable ||
          !Object.hasOwn(descriptor, 'value')
        ) {
          return false;
        }

        tasks.push({ kind: 'visit', value: descriptor.value });
      }
    }

    return true;
  } catch {
    // Failed structural inspection cannot establish valid JSON data.
    return false;
  }
}

/**
 * SPEC §4.2 / ADR 0006 — check only top-level params names.
 * Omission and an empty object contain no unknown names; required fields
 * and their value types must still be checked separately.
 * Inspect only params itself so application-defined storage values survive.
 */
export function hasOnlyParamKeys(
  params: JsonValue | undefined,
  allowedKeys: readonly string[],
): boolean {
  return (
    params === undefined ||
    (isJsonObject(params) && Object.keys(params).every((key) => allowedKeys.includes(key)))
  );
}

/**
 * SPEC §4.2 — intermediate receive-side shape.
 * The envelope guard proves jsonrpc, id, and method-name syntax, but does
 * not yet require params to be an object. This is not a complete valid request.
 */
export type JsonRpcRequestEnvelope = {
  jsonrpc: '2.0';
  id: number;
  method: string;
  params?: JsonValue;
};

/** SPEC §6.1 / ADR 0014 — ASCII lowerCamelCase components, separated by one dot. */
const METHOD_NAME = /^[a-z][A-Za-z0-9]*\.[a-z][A-Za-z0-9]*$/;

/**
 * SPEC §4.1 / §4.2 / §6.1 — validate the envelope independently of params.
 * Separating these checks lets the host distinguish -32600 from -32602
 * without claiming that unchecked params is an object (ADR 0005).
 */
export function isJsonRpcRequestEnvelope(
  value: JsonValue | undefined,
): value is JsonRpcRequestEnvelope {
  return (
    isJsonObject(value) &&
    value.jsonrpc === '2.0' &&
    typeof value.id === 'number' &&
    Number.isInteger(value.id) &&
    value.id > 0 &&
    typeof value.method === 'string' &&
    // JavaScript's $ can match before a final newline; require the entire input.
    METHOD_NAME.exec(value.method)?.[0] === value.method
  );
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

/**
 * SPEC §4.2 — validate the envelope and object-or-omitted params shape.
 * This remains usable on its own. Required fields for each method are
 * checked separately before invoking a capability (SPEC §9.6).
 */
export function isJsonRpcRequest(value: JsonValue | undefined): value is JsonRpcRequest {
  return (
    isJsonRpcRequestEnvelope(value) && (value.params === undefined || isJsonObject(value.params))
  );
}

/** SPEC §6.2 — the one namespace that needs no scope. Compared exactly, never as a prefix. */
export const PORTAL_NAMESPACE = 'portal';

/** SPEC §6.2 — reserved core methods; the `portal` namespace needs no scope. */
export const PORTAL_METHODS = {
  INITIALIZE: 'portal.initialize',
  PING: 'portal.ping',
  CLOSE: 'portal.close',
} as const;

/** SPEC §6.3 — the `profile` namespace; scope `profile`. */
export const PROFILE_METHODS = {
  GET: 'profile.get',
} as const;

/** SPEC §6.3 — storage methods; the namespace itself is the permission scope. */
export const STORAGE_METHODS = {
  GET: 'storage.get',
  SET: 'storage.set',
  DELETE: 'storage.delete',
} as const;

/**
 * SPEC §6.3 — the caller selects a key, never the owning mini app.
 * The host supplies the app identity separately to its provider (ADR 0003).
 */
export type StorageGetParams = {
  key: string;
};

/**
 * SPEC §6.3 / ADR 0004 — null means the key is absent. The value envelope
 * remains present even for null, false, zero, or an empty string.
 * A wire type alias, like ProfileGetResult, so it is assignable to JsonValue.
 */
export type StorageGetResult = {
  value: JsonValue;
};

/**
 * SPEC §9.6 — prove the required read field before the host uses params.key.
 * Omitted params, a missing key, and a non-string key fail this check.
 * Additional fields do not participate in selecting the storage owner.
 */
export function isStorageGetParams(value: JsonValue | undefined): value is StorageGetParams {
  return isJsonObject(value) && typeof value.key === 'string';
}

/**
 * SPEC §6.3 / ADR 0004 — reserve a top-level null for the missing-key result.
 * Exclude removes only that union member: objects and arrays may still
 * contain null. This is a type-level contract; runtime input needs a guard.
 */
export type StorageSetValue = Exclude<JsonValue, null>;

/** SPEC §6.3 — a write carries both the caller's key and the value to store. */
export type StorageSetParams = {
  key: string;
  value: StorageSetValue;
};

/**
 * SPEC §6.3 / §9.6 / ADR 0004 / ADR 0008 — validate before storage access.
 * Require a string key and a non-null JSON value without changing input.
 * isJsonValue checks nested data and rejects non-JSON values and cycles.
 * Nested null remains valid; only a top-level null is reserved for absence.
 * This validates storage params, not the complete inbound message.
 */
export function isStorageSetParams(params: JsonValue | undefined): params is StorageSetParams {
  // Check absence explicitly so false, 0, and "" remain valid values.
  // Reject only top-level null here; isJsonValue validates nested contents.
  return (
    isJsonObject(params) &&
    typeof params.key === 'string' &&
    params.value !== undefined &&
    params.value !== null &&
    isJsonValue(params.value)
  );
}

/**
 * SPEC §6.3 — deletion carries only the caller's key.
 * The host supplies the owning app identity separately (ADR 0003).
 */
export type StorageDeleteParams = {
  key: string;
};

/**
 * SPEC §9.6 — validate the required key before deletion can reach a provider.
 * Omitted params, a missing key, and a non-string key fail this check.
 * App identity is never taken from these params.
 */
export function isStorageDeleteParams(value: JsonValue | undefined): value is StorageDeleteParams {
  return isJsonObject(value) && typeof value.key === 'string';
}

/**
 * SPEC §4.3 — a response to a request. Exactly one of `result` / `error`.
 * A type alias, not an interface, for the same reason as `JsonRpcRequest`.
 */
export type JsonRpcResponse = {
  jsonrpc: '2.0';
  /** null identifies an uncorrelated error (JSON-RPC §5), never a valid request id. */
  id: number | null;
  result?: JsonValue;
  error?: { code: number; message: string; data?: JsonValue };
};

/** SPEC §4.3 / ADR 0017 — validate complete JSON data before response fields. */
export function isJsonRpcResponse(value: unknown): value is JsonRpcResponse {
  if (
    !isJsonValue(value) ||
    !isJsonObject(value) ||
    !Object.hasOwn(value, 'jsonrpc') ||
    !Object.hasOwn(value, 'id') ||
    value.jsonrpc !== '2.0' ||
    (typeof value.id !== 'number' && value.id !== null)
  ) {
    return false;
  }

  const hasResult = Object.hasOwn(value, 'result');
  const hasError = Object.hasOwn(value, 'error');
  // SPEC §4.3: exactly one of the two. Both or neither is a malformed frame.
  if (hasResult === hasError) {
    return false;
  }
  if (!hasError) {
    // Moonpool requests use numeric ids. Only uncorrelated errors can carry null.
    return value.id !== null;
  }

  const error = value.error;
  return (
    isJsonObject(error) &&
    Object.hasOwn(error, 'code') &&
    Object.hasOwn(error, 'message') &&
    typeof error.code === 'number' &&
    Number.isInteger(error.code) &&
    typeof error.message === 'string'
  );
}

/**
 * SPEC §4.1 / §4.2 — find a numeric id to echo before envelope validation.
 * This does not establish a valid request. The host rejects top-level arrays
 * separately, before using this check for ordinary object frames.
 */
export function hasRequestId(
  value: JsonValue | undefined,
): value is { [key: string]: JsonValue } & { id: number } {
  return isJsonObject(value) && typeof value.id === 'number';
}
