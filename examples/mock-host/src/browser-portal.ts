/** SPEC §8.1.1 / ADR 0022 — outer-host registry and retained provider ownership. */
import { type HostCapabilities, type HostConfig, parseManifest } from '@moonpool/host';
import { isJsonObject, type MiniAppManifest } from '@moonpool/protocol';
import {
  cleanupAll,
  isWrapperControls,
  type ProviderGateway,
  readConfiguration,
  reportHostError,
  type WrapperControls,
} from './browser-contract';
import { decodeJson, encodeJson } from './json-boundary';

export interface BrowserPortal {
  readonly frame: HTMLIFrameElement;
  close(reason?: string): Promise<void>;
  notifyLifecycle(state: unknown): Promise<void>;
  notifyEnvironmentChanged(changes: unknown): Promise<void>;
}

interface OpenPortal {
  container: HTMLElement;
  manifest: MiniAppManifest;
  grantedScopes: string[];
  onClosed?(reason: string): void;
}
interface BrowserHostConfig {
  localWindow?: Window;
  origins: ReadonlyMap<string, string>;
  hostInfo: HostConfig['hostInfo'];
  environment: HostConfig['environment'];
  capabilities?: HostCapabilities;
}
export interface BrowserHost {
  open(config: OpenPortal): BrowserPortal;
  bootstrap(source: unknown, document: unknown, controls: unknown): Promise<ProviderGateway>;
  close(): Promise<void>;
}
interface Entry {
  portal: BrowserPortal;
  bind(source: unknown, document: unknown, controls: unknown): ProviderGateway;
}

export function createBrowserHost(options: BrowserHostConfig): BrowserHost {
  const local = options.localWindow ?? window;
  const entries = new Set<Entry>();
  let generation = 0;
  let closed = false;
  const bootstrap = async (
    source: unknown,
    doc: unknown,
    controls: unknown,
  ): Promise<ProviderGateway> => {
    const entry = [...entries].find((candidate) => candidate.portal.frame.contentWindow === source);
    if (closed || entry === undefined) {
      throw new Error('unknown or inactive wrapper');
    }
    return entry.bind(source, doc, controls);
  };
  // SOP excludes cross-origin guests. All host-only handles are additionally instance-bound.
  Reflect.set(local, 'moonpoolBootstrap', bootstrap);

  return {
    bootstrap,
    open(input) {
      if (closed) {
        throw new Error('browser host is inactive');
      }
      const manifest = parseManifest(encodeJson(input.manifest));
      const origin = options.origins.get(manifest.id);
      if (origin === undefined) {
        throw new Error(`no development origin pinned for ${manifest.id}`);
      }
      if (origin === local.location.origin) {
        throw new Error('host and mini app origins must differ');
      }
      const configurationText = encodeJson({
        manifest,
        origin,
        hostInfo: options.hostInfo,
        environment: options.environment,
        grantedScopes: input.grantedScopes,
        profileAvailable: options.capabilities?.profile !== undefined,
        storageAvailable: options.capabilities?.storage !== undefined,
      });
      const config = readConfiguration(configurationText);
      const grants = config.manifest.permissions.filter((scope) =>
        config.grantedScopes.includes(scope),
      );
      const profile = options.capabilities?.profile;
      const storage = options.capabilities?.storage;
      const frame = local.document.createElement('iframe');
      frame.title = manifest.id;
      const expected = new URL('/portal-wrapper.html', local.location.origin);
      expected.searchParams.set('app', manifest.id);
      expected.searchParams.set('instance', String(++generation));
      frame.src = expected.href;
      let active = true;
      let boundDocument: Document | null = null;
      let controls: WrapperControls | undefined;

      const matches = (): boolean => {
        try {
          return (
            frame.isConnected &&
            frame.contentWindow?.location.href === expected.href &&
            frame.contentDocument !== null &&
            (boundDocument === null || frame.contentDocument === boundDocument)
          );
        } catch {
          return false;
        }
      };
      const close = async (reason = 'Portal closed', notify = true): Promise<void> => {
        if (!active) {
          return;
        }
        // Revoke first: no provider or host control can run during failing/reentrant cleanup.
        active = false;
        entries.delete(entry);
        const previous = controls;
        controls = undefined;
        boundDocument = null;
        await cleanupAll([
          () => previous?.dispose(),
          () => frame.removeEventListener('load', loaded),
          () => frame.remove(),
          () => {
            if (notify) {
              input.onClosed?.(reason);
            }
          },
        ]);
      };
      const requireActive = () => {
        if (active && !matches()) {
          void close('Wrapper binding changed').catch(reportHostError);
        }
        if (!active) {
          throw new Error('Portal is inactive');
        }
      };
      const requireScope = (scope: string) => {
        requireActive();
        if (!grants.includes(scope)) {
          throw new Error(`${scope} not granted`);
        }
      };
      const loaded = () => {
        if (active && !matches()) {
          void close('Wrapper binding changed').catch(reportHostError);
        }
      };
      const gateway: ProviderGateway = {
        async configuration() {
          requireActive();
          return configurationText;
        },
        async profile() {
          requireScope('profile');
          if (profile === undefined) {
            throw new Error('profile unavailable');
          }
          const value = await profile.get();
          requireActive();
          const publicData = decodeJson(encodeJson(value));
          if (
            !isJsonObject(publicData) ||
            typeof publicData.displayName !== 'string' ||
            (Object.hasOwn(publicData, 'avatarUrl') && typeof publicData.avatarUrl !== 'string')
          ) {
            throw new TypeError('invalid profile data');
          }
          return encodeJson(
            Object.hasOwn(publicData, 'avatarUrl')
              ? { displayName: publicData.displayName, avatarUrl: publicData.avatarUrl }
              : { displayName: publicData.displayName },
          );
        },
        async get(key) {
          requireScope('storage');
          if (typeof key !== 'string' || storage === undefined) {
            throw new TypeError('invalid storage read');
          }
          // The owning id is captured from this registry, never supplied by the caller.
          const value = await storage.get(manifest.id, key);
          requireActive();
          return encodeJson(value);
        },
        async set(key, text) {
          requireScope('storage');
          const value = decodeJson(text);
          if (typeof key !== 'string' || value === null || storage === undefined) {
            throw new TypeError('invalid storage write');
          }
          await storage.set(manifest.id, key, value);
          requireActive();
        },
        async delete(key) {
          requireScope('storage');
          if (typeof key !== 'string' || storage === undefined) {
            throw new TypeError('invalid storage deletion');
          }
          await storage.delete(manifest.id, key);
          requireActive();
        },
        async close(reason) {
          requireActive();
          if (reason !== undefined && typeof reason !== 'string') {
            throw new TypeError('invalid close reason');
          }
          await close(reason);
        },
      };
      const portal: BrowserPortal = {
        frame,
        async close(reason) {
          await close(reason);
        },
        async notifyLifecycle(state) {
          requireActive();
          if (controls === undefined) {
            throw new Error('wrapper is not ready');
          }
          const text = encodeJson(state);
          await controls.notifyLifecycle(text);
        },
        async notifyEnvironmentChanged(changes) {
          requireActive();
          if (controls === undefined) {
            throw new Error('wrapper is not ready');
          }
          const text = encodeJson(changes);
          await controls.notifyEnvironmentChanged(text);
        },
      };
      const entry: Entry = {
        portal,
        bind(_source, doc, api) {
          requireActive();
          if (frame.contentDocument !== doc || !isWrapperControls(api)) {
            void close('Wrapper bootstrap rejected').catch(reportHostError);
            throw new Error('wrapper Document/API mismatch');
          }
          if (boundDocument !== null) {
            throw new Error('wrapper already bound');
          }
          boundDocument = frame.contentDocument;
          controls = api;
          return gateway;
        },
      };
      entries.add(entry);
      try {
        frame.addEventListener('load', loaded);
        input.container.appendChild(frame);
      } catch (error) {
        // A failed constructor never publishes a Portal or calls its onClosed hook.
        void close('Wrapper startup failed', false).catch(reportHostError);
        throw error;
      }
      return portal;
    },
    async close() {
      if (closed) {
        return;
      }
      closed = true;
      if (Reflect.get(local, 'moonpoolBootstrap') === bootstrap) {
        Reflect.deleteProperty(local, 'moonpoolBootstrap');
      }
      await cleanupAll([...entries].map((entry) => () => entry.portal.close()));
    },
  };
}
