/** Internal host-only contracts; these are not guest RPCs or exported SDK APIs. */
import { type HostConfig, parseManifest } from '@moonpool/host';
import { isJsonObject, type MiniAppManifest } from '@moonpool/protocol';
import { decodeJson, encodeJson } from './json-boundary';

export interface WrapperControls {
  notifyLifecycle(text: string): Promise<void>;
  notifyEnvironmentChanged(text: string): Promise<void>;
  dispose(): Promise<void>;
}

export interface ProviderGateway {
  configuration(): Promise<string>;
  profile(): Promise<string>;
  get(key: string): Promise<string>;
  set(key: string, text: string): Promise<void>;
  delete(key: string): Promise<void>;
  close(reason?: string): Promise<void>;
}

export function isWrapperControls(value: unknown): value is WrapperControls {
  return (
    typeof value === 'object' &&
    value !== null &&
    'notifyLifecycle' in value &&
    typeof value.notifyLifecycle === 'function' &&
    'notifyEnvironmentChanged' in value &&
    typeof value.notifyEnvironmentChanged === 'function' &&
    'dispose' in value &&
    typeof value.dispose === 'function'
  );
}

export function isProviderGateway(value: unknown): value is ProviderGateway {
  return (
    typeof value === 'object' &&
    value !== null &&
    'configuration' in value &&
    typeof value.configuration === 'function' &&
    'profile' in value &&
    typeof value.profile === 'function' &&
    'get' in value &&
    typeof value.get === 'function' &&
    'set' in value &&
    typeof value.set === 'function' &&
    'delete' in value &&
    typeof value.delete === 'function' &&
    'close' in value &&
    typeof value.close === 'function'
  );
}

export interface BrowserConfiguration {
  hostInfo: HostConfig['hostInfo'];
  manifest: MiniAppManifest;
  grantedScopes: string[];
  environment: HostConfig['environment'];
  origin: string;
  profileAvailable: boolean;
  storageAvailable: boolean;
}

export function readConfiguration(text: string): BrowserConfiguration {
  const value = decodeJson(text);
  if (!isJsonObject(value)) {
    throw new TypeError('invalid browser host configuration');
  }
  const {
    hostInfo,
    manifest,
    grantedScopes,
    environment,
    origin,
    profileAvailable,
    storageAvailable,
  } = value;
  if (
    !isJsonObject(hostInfo) ||
    typeof hostInfo.name !== 'string' ||
    typeof hostInfo.version !== 'string' ||
    hostInfo.platform !== 'browser' ||
    !Array.isArray(grantedScopes) ||
    !grantedScopes.every((scope): scope is string => typeof scope === 'string') ||
    !isJsonObject(environment) ||
    typeof environment.locale !== 'string' ||
    (environment.colorScheme !== 'light' && environment.colorScheme !== 'dark') ||
    typeof origin !== 'string' ||
    typeof profileAvailable !== 'boolean' ||
    typeof storageAvailable !== 'boolean'
  ) {
    throw new TypeError('invalid browser host configuration');
  }
  const url = new URL(origin);
  if ((url.protocol !== 'http:' && url.protocol !== 'https:') || url.origin !== origin) {
    throw new TypeError('expected an exact development origin');
  }
  return {
    hostInfo: { name: hostInfo.name, version: hostInfo.version, platform: 'browser' },
    manifest: parseManifest(encodeJson(manifest)),
    grantedScopes: [...grantedScopes],
    environment: { locale: environment.locale, colorScheme: environment.colorScheme },
    origin,
    profileAvailable,
    storageAvailable,
  };
}

/** Start every cleanup attempt, then preserve the first failure in declaration order. */
export async function cleanupAll(steps: Array<() => void | Promise<void>>): Promise<void> {
  const results = await Promise.allSettled(steps.map(async (step) => step()));
  for (const result of results) {
    if (result.status === 'rejected') {
      throw result.reason;
    }
  }
}

export function reportHostError(error: unknown): void {
  queueMicrotask(() => {
    throw error;
  });
}
