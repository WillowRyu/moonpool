import { createHost, type HostConnection } from '../../../packages/host/src/index';
import {
  isJsonObject,
  isJsonValue,
  type JsonValue,
  type Transport,
} from '../../../packages/protocol/src/index';
import { createIframeTransport } from '../../../packages/transport-iframe/src/index';

const status = document.querySelector<HTMLElement>('#status');
const portal = document.querySelector<HTMLElement>('#portal');
if (status === null || portal === null) {
  throw new Error('missing wrapper controls');
}
let slot = '';
let origin = '';
let disposed = false;
let holdNext = false;
let profileCalls = 0;
let sent = 0;
let received = 0;
let suppressed = 0;
let lastProfileId = 0;
let listeners = 0;
let grants: string[] = [];
let app: HTMLIFrameElement | undefined;
let transport: Transport | undefined;
let connection: HostConnection | undefined;
let finishProfile: (() => void) | undefined;
const events: Array<Record<string, JsonValue>> = [];
const startedAt = performance.now();
const report = () => {
  const reporter: unknown = Reflect.get(parent, 'multiLabReport');
  if (typeof reporter === 'function') {
    // Only public experiment data crosses this trusted same-origin control boundary.
    reporter(
      window,
      document,
      JSON.stringify({
        slot,
        origin,
        status: disposed ? 'revoked' : 'active',
        grants,
        profileCalls,
        pendingProfile: finishProfile === undefined ? 0 : 1,
        lastProfileId,
        sent,
        received,
        suppressed,
        listeners,
        innerFrames: portal.querySelectorAll('iframe').length,
        events,
      }),
    );
  }
};
const record = (event: string, fields: Record<string, JsonValue> = {}) => {
  events.push({
    n: events.length + 1,
    ms: Math.round(performance.now() - startedAt),
    event,
    ...fields,
  });
  report();
};
const observe = (event: MessageEvent<unknown>) => {
  if (event.source !== app?.contentWindow) {
    return;
  }
  received += 1;
  const data = isJsonValue(event.data) ? event.data : null;
  if (isJsonObject(data) && data.method === 'profile.get' && typeof data.id === 'number') {
    lastProfileId = data.id;
  }
  record('guest-message', {
    origin: event.origin,
    sourceMatches: true,
    expectedOrigin: event.origin === origin,
    data,
  });
};
const violation = (event: SecurityPolicyViolationEvent) => {
  record('policy-event', {
    trusted: event.isTrusted,
    disposition: event.disposition,
    directive: event.effectiveDirective,
    blockedURI: event.blockedURI,
  });
  if (
    event.isTrusted &&
    event.disposition === 'enforce' &&
    event.effectiveDirective === 'frame-src'
  ) {
    dispose('enforced frame-src violation');
  }
};
const dispose = (reason: string) => {
  if (disposed) {
    return;
  }
  disposed = true;
  transport?.close();
  window.removeEventListener('message', observe);
  document.removeEventListener('securitypolicyviolation', violation);
  listeners = 0;
  app?.remove();
  status.textContent = `Wrapper ${slot}: revoked (${reason})`;
  // Keep this trusted wrapper alive only for inspecting late sends; production cleanup is not claimed.
  record('disposed', { reason });
};
const command = (name: string) => {
  if (name === 'release') {
    const finish = finishProfile;
    finishProfile = undefined;
    finish?.();
    report();
    return;
  }
  if (disposed) {
    record('ignored-command', { name });
    return;
  }
  if (name === 'hold') {
    holdNext = true;
    record('hold-next-profile');
    name = 'profile';
  }
  if (name === 'notify-local') {
    void connection
      ?.notifyEnvironmentChanged({ colorScheme: 'dark', locale: 'ko-KR' })
      .then(() => record('local-notification-submitted'));
    return;
  }
  app?.contentWindow?.postMessage({ lab: 'multi-command', name }, origin);
};
const api = {
  command,
  dispose,
  async notify(changes: unknown) {
    if (connection === undefined || disposed) {
      throw new Error('wrapper is inactive');
    }
    // Deliberate cross-realm experiment: do not repair/normalize the supplied object.
    await Reflect.apply(connection.notifyEnvironmentChanged, undefined, [changes]);
  },
};
const bootstrap: unknown = Reflect.get(parent, 'multiLabBootstrap');
if (typeof bootstrap !== 'function') {
  throw new Error('missing trusted coordinator');
}
const configText: unknown = bootstrap(window, document, api);
if (typeof configText !== 'string') {
  status.textContent = 'Bootstrap rejected by coordinator';
} else {
  const config: unknown = JSON.parse(configText);
  if (
    !isJsonValue(config) ||
    !isJsonObject(config) ||
    (config.slot !== 'A' && config.slot !== 'B') ||
    typeof config.origin !== 'string' ||
    typeof config.storageAllowed !== 'boolean'
  ) {
    throw new Error('invalid coordinator config');
  }
  slot = config.slot;
  origin = config.origin;
  grants = config.storageAllowed ? ['profile', 'storage'] : ['profile'];
  const current = document.createElement('iframe');
  current.title = `Mini app ${slot}`;
  current.src = `${origin}/multi-probe.html`;
  app = current;
  window.addEventListener('message', observe);
  document.addEventListener('securitypolicyviolation', violation);
  // Attach synchronously before the new guest can initiate its first handshake.
  portal.replaceChildren(current);
  if (current.contentWindow === null) {
    throw new Error('missing guest window');
  }
  const base = createIframeTransport({ peerWindow: current.contentWindow, peerOrigin: origin });
  listeners = 3; // This fixture's observer, CSP listener, and SDK message listener.
  transport = {
    onMessage(handler) {
      return base.onMessage((message) => {
        if (!disposed) {
          handler(message);
        }
      });
    },
    send(message) {
      if (disposed) {
        suppressed += 1;
        record('suppressed-send');
        return;
      }
      sent += 1;
      record('bridge-send', { data: message });
      base.send(message);
    },
    close() {
      base.close();
    },
  };
  const values = new Map<string, JsonValue>();
  connection = createHost({
    hostInfo: { name: `wrapper-${slot}`, version: '0.1.0', platform: 'browser' },
    manifest: {
      manifestVersion: 1,
      id: `com.example.multi.${slot.toLowerCase()}`,
      name: `Portal ${slot}`,
      version: '1.0.0',
      entry: 'multi-probe.html',
      protocolVersion: '0.1',
      permissions: ['profile', 'storage'],
    },
    grantedScopes: grants,
    environment: { locale: 'en', colorScheme: 'light' },
    capabilities: {
      profile: {
        async get() {
          profileCalls += 1;
          if (holdNext) {
            holdNext = false;
            await new Promise<void>((resolve) => {
              finishProfile = resolve;
              record('profile-pending');
            });
          }
          record('profile-completed');
          return { displayName: `Lab user ${slot}` };
        },
      },
      storage: {
        async get(_id, key) {
          return values.get(key) ?? null;
        },
        async set(_id, key, value) {
          values.set(key, value);
        },
        async delete(_id, key) {
          values.delete(key);
        },
      },
    },
  }).connect(transport);
  status.textContent = `Trusted wrapper ${slot} permits only ${origin}`;
  record('configured', { origin });
}
