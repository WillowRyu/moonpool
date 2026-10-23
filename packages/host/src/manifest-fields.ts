/**
 * Internal first stage of SPEC §7 manifest admission.
 * Entry containment and recognized scopes must be checked by the next stage.
 * Do not export this partial parser as the package's full manifest parser.
 */
export interface ManifestFields {
  manifestVersion: 1;
  id: string;
  name: string;
  version: string;
  /** String field only at this stage; path containment is not established. */
  entry: string;
  protocolVersion: string;
  /** String members only at this stage; scope recognition is not established. */
  permissions: string[];
}

/** Local configuration failure, not a JSON-RPC response or bridge error code. */
export class ManifestError extends Error {
  readonly field: string;

  constructor(field: string, message: string) {
    super(message);
    this.name = 'ManifestError';
    this.field = field;
  }
}

/** SPEC §7's exact id expression; do not silently impose extra DNS rules. */
const MINI_APP_ID = /^[a-z0-9]+(\.[a-z0-9-]+)+$/;

/** SemVer 2.0.0's JavaScript-compatible expression; syntax only, not ordering.
 * https://semver.org/spec/v2.0.0.html#is-there-a-suggested-regular-expression-regex-to-check-a-semver-string
 */
const SEMVER =
  /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$/;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/** A required JSON member must not be supplied by a modified Object.prototype. */
function required(record: Record<string, unknown>, field: string): unknown {
  if (!Object.hasOwn(record, field)) {
    throw new ManifestError(field, `manifest.${field} is required`);
  }
  return record[field];
}

function matchesEntirely(pattern: RegExp, value: string): boolean {
  // JavaScript's $ can match before a final newline. Require the whole string.
  return pattern.exec(value)?.[0] === value;
}

/**
 * Parse file text and validate SPEC §7's required field shapes and formats.
 * This pure, synchronous helper performs no I/O and creates no connection.
 * It does not prove entry containment or scope recognition; T06 must finish
 * admission before the package exposes a full parser or the example uses it.
 */
export function parseManifestFields(source: unknown): ManifestFields {
  if (typeof source !== 'string') {
    throw new ManifestError('json', 'manifest source must be JSON text');
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(source);
  } catch {
    // SyntaxError can contain a source excerpt; keep untrusted text out of diagnostics.
    throw new ManifestError('json', 'manifest must contain valid JSON');
  }
  if (!isRecord(parsed)) {
    throw new ManifestError('manifest', 'manifest must be a JSON object');
  }

  const manifestVersion = required(parsed, 'manifestVersion');
  if (manifestVersion !== 1) {
    throw new ManifestError('manifestVersion', 'manifest.manifestVersion must be 1');
  }

  const id = required(parsed, 'id');
  if (typeof id !== 'string' || !matchesEntirely(MINI_APP_ID, id)) {
    throw new ManifestError('id', 'manifest.id must match the reverse-DNS id pattern');
  }

  const name = required(parsed, 'name');
  if (typeof name !== 'string') {
    throw new ManifestError('name', 'manifest.name must be a string');
  }
  // ADR 0010: the string iterator counts code points, including one per surrogate pair.
  // Stop at the first excess character instead of allocating an unbounded character array.
  let nameLength = 0;
  for (const _character of name) {
    nameLength += 1;
    if (nameLength > 40) {
      break;
    }
  }
  if (nameLength < 1 || nameLength > 40) {
    throw new ManifestError('name', 'manifest.name must contain 1–40 Unicode code points');
  }

  const version = required(parsed, 'version');
  if (typeof version !== 'string' || !matchesEntirely(SEMVER, version)) {
    throw new ManifestError('version', 'manifest.version must be a SemVer 2.0.0 string');
  }

  const entry = required(parsed, 'entry');
  if (typeof entry !== 'string') {
    throw new ManifestError('entry', 'manifest.entry must be a string');
  }

  const protocolVersion = required(parsed, 'protocolVersion');
  if (typeof protocolVersion !== 'string') {
    throw new ManifestError('protocolVersion', 'manifest.protocolVersion must be a string');
  }

  const permissions = required(parsed, 'permissions');
  if (
    !Array.isArray(permissions) ||
    !permissions.every((scope: unknown) => typeof scope === 'string')
  ) {
    throw new ManifestError('permissions', 'manifest.permissions must be an array of strings');
  }

  return { manifestVersion, id, name, version, entry, protocolVersion, permissions };
}
