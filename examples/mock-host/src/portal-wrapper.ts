/** Trusted host document, SPEC §8.1.1. The kernel never imports this DOM adapter. */
import { createHost, type HostCapabilities, type HostConnection } from '@moonpool/host';
import {
  hasOnlyParamKeys,
  isJsonObject,
  type PortalEnvironmentChangedParams,
  type Transport,
} from '@moonpool/protocol';
import { createIframeTransport } from '@moonpool/transport-iframe';
import {
  cleanupAll,
  isProviderGateway,
  type ProviderGateway,
  readConfiguration,
  reportHostError,
  type WrapperControls,
} from './browser-contract';
import { decodeJson, encodeJson } from './json-boundary';

export function isEnforcedFrameViolation(event: {
  isTrusted: boolean;
  disposition: string;
  effectiveDirective: string;
}): boolean {
  return (
    event.isTrusted && event.disposition === 'enforce' && event.effectiveDirective === 'frame-src'
  );
}

export async function startWrapper(local: Window = window): Promise<WrapperControls> {
  const doc = local.document;
  const container = doc.querySelector<HTMLElement>('#portal');
  if (container === null) {
    throw new Error('wrapper portal container missing');
  }
  let active = true;
  let guest: HTMLIFrameElement | undefined;
  let transport: Transport | undefined;
  let connection: HostConnection | undefined;
  let gateway: ProviderGateway | undefined;
  const requireActive = () => {
    if (!active) {
      throw new Error('Portal is inactive');
    }
  };
  const dispose = async () => {
    if (!active) {
      return;
    }
    active = false;
    const previousTransport = transport;
    const previousGuest = guest;
    transport = undefined;
    guest = undefined;
    connection = undefined;
    await cleanupAll([
      () => previousTransport?.close(),
      () => doc.removeEventListener('securitypolicyviolation', onViolation),
      () => previousGuest?.remove(),
    ]);
  };
  const onViolation = (event: SecurityPolicyViolationEvent) => {
    if (!active || !isEnforcedFrameViolation(event)) {
      return;
    }
    // Both sides invalidate synchronously before either side awaits cleanup.
    void cleanupAll([dispose, () => gateway?.close('Navigation blocked by Portal policy')]).catch(
      reportHostError,
    );
  };
  const controls: WrapperControls = {
    dispose,
    async notifyLifecycle(text) {
      requireActive();
      const state = decodeJson(text);
      if (state !== 'paused' && state !== 'resumed') {
        throw new TypeError('invalid lifecycle state');
      }
      if (connection === undefined) {
        throw new Error('wrapper is not ready');
      }
      await connection.notifyLifecycle(state);
    },
    async notifyEnvironmentChanged(text) {
      requireActive();
      const value = decodeJson(text);
      if (!isJsonObject(value) || !hasOnlyParamKeys(value, ['locale', 'colorScheme'])) {
        throw new TypeError('invalid environment changes');
      }
      const colorScheme = Object.hasOwn(value, 'colorScheme') ? value.colorScheme : undefined;
      const locale = Object.hasOwn(value, 'locale') ? value.locale : undefined;
      if (
        (colorScheme !== undefined && colorScheme !== 'light' && colorScheme !== 'dark') ||
        (locale !== undefined && typeof locale !== 'string')
      ) {
        throw new TypeError('invalid environment changes');
      }
      const changes: PortalEnvironmentChangedParams = {};
      if (colorScheme !== undefined) {
        changes.colorScheme = colorScheme;
      }
      if (locale !== undefined) {
        changes.locale = locale;
      }
      if (connection === undefined) {
        throw new Error('wrapper is not ready');
      }
      await connection.notifyEnvironmentChanged(changes);
    },
  };

  try {
    const bootstrap: unknown = Reflect.get(local.parent, 'moonpoolBootstrap');
    if (typeof bootstrap !== 'function') {
      throw new Error('trusted browser host missing');
    }
    const candidate: unknown = await bootstrap(local, doc, controls);
    if (!isProviderGateway(candidate)) {
      throw new TypeError('invalid host provider gateway');
    }
    const bound = candidate;
    gateway = bound;
    const config = readConfiguration(await bound.configuration());
    requireActive();
    if (config.origin === local.location.origin) {
      throw new Error('guest origin must differ from host');
    }
    const requireId = (id: string) => {
      requireActive();
      if (id !== config.manifest.id) {
        throw new Error('provider identity mismatch');
      }
    };
    // Only private kernel facades consume these fallbacks after disposal. The
    // closed transport discards their completion; no replacement sees it.
    const providerResult = async <T>(run: () => Promise<T>, retired: T): Promise<T> => {
      requireActive();
      try {
        const value = await run();
        return active ? value : retired;
      } catch (error) {
        if (!active) {
          return retired;
        }
        throw error;
      }
    };
    const capabilities: HostCapabilities = {};
    if (config.profileAvailable) {
      capabilities.profile = {
        async get() {
          return providerResult(
            async () => {
              const value = decodeJson(await bound.profile());
              if (
                !isJsonObject(value) ||
                typeof value.displayName !== 'string' ||
                (Object.hasOwn(value, 'avatarUrl') && typeof value.avatarUrl !== 'string')
              ) {
                throw new TypeError('invalid public profile');
              }
              const profile: { displayName: string; avatarUrl?: string } = {
                displayName: value.displayName,
              };
              if (Object.hasOwn(value, 'avatarUrl') && typeof value.avatarUrl === 'string') {
                profile.avatarUrl = value.avatarUrl;
              }
              return profile;
            },
            { displayName: '' },
          );
        },
      };
    }
    if (config.storageAvailable) {
      capabilities.storage = {
        async get(id, key) {
          requireId(id);
          return providerResult(async () => decodeJson(await bound.get(key)), null);
        },
        async set(id, key, value) {
          requireId(id);
          const text = encodeJson(value);
          await providerResult(() => bound.set(key, text), undefined);
        },
        async delete(id, key) {
          requireId(id);
          await providerResult(() => bound.delete(key), undefined);
        },
      };
    }
    doc.addEventListener('securitypolicyviolation', onViolation);
    guest = doc.createElement('iframe');
    guest.title = config.manifest.id;
    guest.src = new URL(config.manifest.entry, `${config.origin}/`).href;
    container.appendChild(guest);
    if (guest.contentWindow === null) {
      throw new Error('guest window missing');
    }
    const base = createIframeTransport({
      peerWindow: guest.contentWindow,
      peerOrigin: config.origin,
      localWindow: local,
    });
    transport = {
      send(message) {
        if (active) {
          base.send(message);
        }
      },
      onMessage(handler) {
        return base.onMessage((message) => {
          if (active) {
            handler(message);
          }
        });
      },
      close() {
        base.close();
      },
    };
    // Same task as frame insertion: the receiver precedes the first handshake.
    connection = createHost({ ...config, capabilities }).connect(transport, {
      async onCloseRequested(reason) {
        if (active) {
          await bound.close(reason);
        }
      },
    });
    return controls;
  } catch (error) {
    await cleanupAll([dispose, () => gateway?.close('Wrapper startup failed')]).catch(
      reportHostError,
    );
    throw error;
  }
}
