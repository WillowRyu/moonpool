import {
  type HostNotification,
  isJsonObject,
  isJsonValue,
  type PortalEnvironmentChangedParams,
} from '@moonpool/protocol';

/** Local subscribers may finish synchronously or asynchronously. */
export type NotificationListener = (notification: HostNotification) => void | Promise<void>;

// Same portable exception-reporting pattern as the host and iframe transport.
declare const queueMicrotask: (callback: () => void) => void;

/** Project validated wire data into the known local event view (ADR 0021). */
function readHostNotification(value: unknown): HostNotification | undefined {
  if (
    !isJsonValue(value) ||
    !isJsonObject(value) ||
    !Object.hasOwn(value, 'jsonrpc') ||
    value.jsonrpc !== '2.0' ||
    !Object.hasOwn(value, 'method') ||
    Object.hasOwn(value, 'id')
  ) {
    return undefined;
  }
  const params = Object.hasOwn(value, 'params') ? value.params : undefined;
  if (value.method === 'portal.lifecycle') {
    if (!isJsonObject(params) || !Object.hasOwn(params, 'state')) {
      return undefined;
    }
    const state = params.state;
    if (state !== 'resumed' && state !== 'paused') {
      return undefined;
    }
    return { jsonrpc: '2.0', method: 'portal.lifecycle', params: { state } };
  }
  if (value.method !== 'portal.environmentChanged') {
    return undefined;
  }
  // All environment fields are optional; omitted params is an empty change.
  if (params !== undefined && !isJsonObject(params)) {
    return undefined;
  }
  const colorScheme =
    params !== undefined && Object.hasOwn(params, 'colorScheme') ? params.colorScheme : undefined;
  const locale =
    params !== undefined && Object.hasOwn(params, 'locale') ? params.locale : undefined;
  if (
    (colorScheme !== undefined && colorScheme !== 'light' && colorScheme !== 'dark') ||
    (locale !== undefined && typeof locale !== 'string')
  ) {
    return undefined;
  }
  const changes: PortalEnvironmentChangedParams = {};
  if (colorScheme !== undefined) {
    changes.colorScheme = colorScheme;
  }
  if (locale !== undefined) {
    changes.locale = locale;
  }
  return { jsonrpc: '2.0', method: 'portal.environmentChanged', params: changes };
}

function copyNotification(notification: HostNotification): HostNotification {
  if (notification.method === 'portal.lifecycle') {
    return {
      jsonrpc: '2.0',
      method: 'portal.lifecycle',
      params: { state: notification.params.state },
    };
  }
  return {
    jsonrpc: '2.0',
    method: 'portal.environmentChanged',
    params: { ...notification.params },
  };
}

function reportListenerError(error: unknown): void {
  queueMicrotask(() => {
    throw error;
  });
}

/** Internal subscription registry, owned and cleared by one client. */
export function createNotificationSubscriptions() {
  const subscriptions = new Set<{ listener: NotificationListener }>();
  return {
    subscribe(listener: NotificationListener): () => void {
      if (typeof listener !== 'function') {
        throw new TypeError('notification listener must be a function');
      }
      const subscription = { listener };
      subscriptions.add(subscription);
      return () => {
        subscriptions.delete(subscription);
      };
    },
    dispatch(message: unknown): void {
      const notification = readHostNotification(message);
      if (notification === undefined) {
        return;
      }
      // Snapshot additions, but respect removals/close before each listener's turn.
      for (const subscription of [...subscriptions]) {
        if (!subscriptions.has(subscription)) {
          continue;
        }
        const { listener } = subscription;
        try {
          // Each listener owns its copy; an async listener never delays the next one.
          void Promise.resolve(listener(copyNotification(notification))).catch(reportListenerError);
        } catch (error) {
          reportListenerError(error);
        }
      }
    },
    clear(): void {
      subscriptions.clear();
    },
  };
}
