import type { MiniAppManifest } from '@moonpool/protocol';
import { PROFILE_METHODS, STORAGE_METHODS } from '@moonpool/protocol';
import { ManifestError, parseManifestFields } from './manifest-fields';

/** SPEC §7 / ADR 0011: lexical validation only; actual loading belongs to the embedder. */
function isPackageEntry(entry: string): boolean {
  if (
    entry === '' ||
    entry !== entry.trim() ||
    entry.startsWith('/') ||
    /[\\%:?#\p{Cc}]/u.test(entry)
  ) {
    return false;
  }

  const segments = entry.split('/');
  const last = segments.at(-1);
  if (last === undefined || last === '' || last === '.' || last === '..') {
    return false;
  }

  let depth = 0;
  for (const segment of segments) {
    if (segment === '' || segment === '.') {
      continue;
    }
    if (segment === '..') {
      if (depth === 0) {
        return false;
      }
      depth -= 1;
    } else {
      depth += 1;
    }
  }
  return true;
}

/**
 * Validate SPEC §7 JSON text before the embedder loads a Portal.
 * No I/O, bridge creation, provider installation, grants, or version negotiation.
 * Accepted entry text is preserved; the loader must resolve it inside the package.
 */
export function parseManifest(source: unknown): MiniAppManifest {
  const manifest = parseManifestFields(source);

  if (!isPackageEntry(manifest.entry)) {
    throw new ManifestError(
      'entry',
      'manifest.entry must be an unencoded relative file path inside the package root',
    );
  }

  // SPEC §6.1: derive scopes from capability namespaces, not an independent registry.
  // portal.* is reserved for protocol methods and requires no declared scope.
  const capabilityScopes = new Set(
    [...Object.values(PROFILE_METHODS), ...Object.values(STORAGE_METHODS)].map((method) =>
      method.slice(0, method.indexOf('.')),
    ),
  );
  if (!manifest.permissions.every((scope) => capabilityScopes.has(scope))) {
    throw new ManifestError(
      'permissions',
      'manifest.permissions contains an unknown capability scope',
    );
  }

  return manifest;
}
