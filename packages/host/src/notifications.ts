import {
  type HostNotification,
  hasOnlyParamKeys,
  isJsonObject,
  isJsonValue,
  type PortalEnvironmentChangedParams,
  type PortalLifecycleState,
  type Transport,
} from '@moonpool/protocol';

/**
 * SPEC §6.4 / ADR 0020 — sends only to this connection's mini app.
 * Promises confirm local submission, not peer receipt or processing.
 * The embedder owns notification timing, current state, and transport lifetime.
 */
export interface HostConnection {
  notifyLifecycle(state: PortalLifecycleState): Promise<void>;
  notifyEnvironmentChanged(changes: PortalEnvironmentChangedParams): Promise<void>;
}

/** Internal factory; only Host.connect exposes the bound sender. */
export function createNotificationSender(transport: Transport): HostConnection {
  return {
    async notifyLifecycle(state) {
      if (state !== 'resumed' && state !== 'paused') {
        throw new TypeError('invalid portal.lifecycle state');
      }
      const frame: HostNotification = {
        jsonrpc: '2.0',
        method: 'portal.lifecycle',
        params: { state },
      };
      transport.send(frame);
    },
    async notifyEnvironmentChanged(changes) {
      if (
        !isJsonValue(changes) ||
        !isJsonObject(changes) ||
        !hasOnlyParamKeys(changes, ['colorScheme', 'locale'])
      ) {
        throw new TypeError('invalid portal.environmentChanged params');
      }
      const colorScheme = Object.hasOwn(changes, 'colorScheme') ? changes.colorScheme : undefined;
      const locale = Object.hasOwn(changes, 'locale') ? changes.locale : undefined;
      if (
        (colorScheme !== undefined && colorScheme !== 'light' && colorScheme !== 'dark') ||
        (locale !== undefined && typeof locale !== 'string')
      ) {
        throw new TypeError('invalid portal.environmentChanged params');
      }

      // Snapshot declared fields only; never retain the caller's mutable object.
      const params: PortalEnvironmentChangedParams = {};
      if (colorScheme !== undefined) {
        params.colorScheme = colorScheme;
      }
      if (locale !== undefined) {
        params.locale = locale;
      }
      const frame: HostNotification = {
        jsonrpc: '2.0',
        method: 'portal.environmentChanged',
        params,
      };
      transport.send(frame);
    },
  };
}
