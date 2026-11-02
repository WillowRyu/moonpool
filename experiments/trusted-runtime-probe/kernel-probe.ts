// Compatibility fixture only. Client and providers here are test doubles of the
// peer/native provider boundary; the real existing kernels are imported below.

import { decodeJson, encodeJson } from '../../examples/mock-host/src/json-boundary';
import { createClient, type MoonpoolClient } from '../../packages/client/src/index';
import { createHost, type HostConfig } from '../../packages/host/src/index';
import {
  ERROR_CODES,
  isJsonObject,
  isJsonValue,
  type JsonValue,
  PROTOCOL_VERSION,
  type Transport,
} from '../../packages/protocol/src/index';

declare const setTimeout: (handler: () => void, timeoutMs: number) => unknown;
declare const clearTimeout: (handle: unknown) => void;
declare const queueMicrotask: (callback: () => void) => void;

type Report = {
  complete: boolean;
  closed: boolean;
  checks: Array<{ label: string; passed: boolean }>;
  globals: Record<string, boolean>;
  storedValue?: JsonValue;
  initialValue?: JsonValue;
  appId?: string;
  protocolVersion: string;
  error?: string;
};
const globals = globalThis as unknown as Record<string, unknown>;
const report: Report = {
  complete: false,
  closed: false,
  checks: [],
  globals: {
    window: typeof globals.window !== 'undefined',
    document: typeof globals.document !== 'undefined',
    timeout: typeof globals.setTimeout === 'function',
    microtask: typeof globals.queueMicrotask === 'function',
  },
  protocolVersion: PROTOCOL_VERSION,
};
const clients: MoonpoolClient[] = [];
let started = false;
function check(label: string, passed: boolean) {
  report.checks.push({ label, passed });
  if (!passed) {
    throw new Error(label);
  }
}
async function flush() {
  for (let i = 0; i < 12; i++) {
    await Promise.resolve();
  }
}
function linked() {
  const a = new Set<(message: JsonValue) => void>();
  const b = new Set<(message: JsonValue) => void>();
  const end = (own: typeof a, peer: typeof a): Transport => ({
    send(message) {
      queueMicrotask(() => {
        for (const callback of peer) {
          callback(message);
        }
      });
    },
    onMessage(callback) {
      own.add(callback);
      return () => {
        own.delete(callback);
      };
    },
    close() {
      own.clear();
    },
  });
  return { client: end(a, b), host: end(b, a) };
}

async function run(text: string) {
  const input = decodeJson(text);
  if (
    !isJsonObject(input) ||
    typeof input.appId !== 'string' ||
    !['ios', 'android', 'browser'].includes(String(input.platform))
  ) {
    throw new TypeError('invalid trusted probe config');
  }
  const appId = input.appId;
  const initialValue = input.initialValue ?? null;
  const writeValue = typeof input.writeValue === 'string' ? input.writeValue : undefined;
  report.appId = appId;
  report.initialValue = initialValue;
  check(
    'language primitives',
    typeof Promise === 'function' &&
      typeof Map === 'function' &&
      typeof Reflect.ownKeys === 'function' &&
      typeof Object.getOwnPropertyDescriptor === 'function',
  );
  check(
    'recursive JSON inspection',
    isJsonValue({ items: [false, 0, null, 'text'] }) && !isJsonValue({ value: Infinity }),
  );
  let getterCalls = 0;
  const getter = Object.defineProperty({}, 'value', {
    enumerable: true,
    get() {
      getterCalls++;
      return 1;
    },
  });
  check('getter rejected without evaluation', !isJsonValue(getter) && getterCalls === 0);
  const values = new Map<string, JsonValue>();
  if (initialValue !== null) {
    values.set('marker', initialValue);
  }
  const owner = (value: string) => {
    if (value !== appId) {
      throw new Error('wrong native owner');
    }
  };
  let providerWrites = 0;
  const config: HostConfig = {
    hostInfo: {
      name: 'trusted-runtime-probe',
      version: '0.0.0',
      platform: input.platform as 'ios' | 'android' | 'browser',
    },
    manifest: {
      manifestVersion: 1,
      id: appId,
      name: 'Runtime probe',
      version: '1.0.0',
      entry: 'index.html',
      protocolVersion: PROTOCOL_VERSION,
      permissions: ['profile', 'storage'],
    },
    grantedScopes: ['profile', 'storage'],
    environment: { locale: 'en', colorScheme: 'light' },
    capabilities: {
      profile: {
        async get() {
          return { displayName: 'Public runtime profile', privateDummy: 'public-test-sentinel' };
        },
      },
      storage: {
        async get(app, key) {
          owner(app);
          return values.get(key) ?? null;
        },
        async set(app, key, value) {
          owner(app);
          providerWrites++;
          values.set(key, value);
        },
        async delete(app, key) {
          owner(app);
          values.delete(key);
        },
      },
    },
  };
  const pair = linked();
  const connection = createHost(config).connect(pair.host);
  const client = createClient({ transport: pair.client });
  clients.push(client);
  const initialized = await client.initialize();
  check(
    'real kernel handshake',
    initialized.protocolVersion === PROTOCOL_VERSION && initialized.miniApp.id === appId,
  );
  const ping = await client.call('portal.ping', {});
  check('real kernel ping', isJsonValue(ping) && isJsonObject(ping) && ping.pong === true);
  const profile = await client.call('profile.get', {});
  check(
    'public profile projection',
    isJsonValue(profile) &&
      isJsonObject(profile) &&
      profile.displayName === 'Public runtime profile' &&
      !Object.hasOwn(profile, 'privateDummy'),
  );
  const before = await client.call('storage.get', { key: 'marker' });
  check(
    'initial public fixture snapshot',
    isJsonValue(before) && isJsonObject(before) && before.value === initialValue,
  );
  if (writeValue !== undefined) {
    await client.call('storage.set', { key: 'marker', value: writeValue });
  }
  const after = await client.call('storage.get', { key: 'marker' });
  check(
    'storage provider fixture',
    isJsonValue(after) && isJsonObject(after) && after.value === (writeValue ?? initialValue),
  );
  report.storedValue = isJsonValue(after) && isJsonObject(after) ? (after.value ?? null) : null;
  const writes = providerWrites;
  let invalidCode: unknown;
  try {
    await client.call('storage.set', { key: 'marker', value: Infinity });
  } catch (error) {
    invalidCode = (error as { code?: unknown }).code;
  }
  check(
    'invalid JSON rejected before provider',
    invalidCode === ERROR_CODES.INVALID_PARAMS && providerWrites === writes,
  );
  const deniedPair = linked();
  let deniedProviderCalls = 0;
  createHost({
    ...config,
    grantedScopes: [],
    capabilities: {
      storage: {
        async get() {
          deniedProviderCalls++;
          return null;
        },
        async set() {
          deniedProviderCalls++;
        },
        async delete() {
          deniedProviderCalls++;
        },
      },
    },
  }).connect(deniedPair.host);
  const denied = createClient({ transport: deniedPair.client });
  clients.push(denied);
  await denied.initialize();
  let deniedCode: unknown;
  try {
    await denied.call('storage.get', { key: 'marker' });
  } catch (error) {
    deniedCode = (error as { code?: unknown }).code;
  }
  check(
    'permission enforced before provider',
    deniedCode === ERROR_CODES.PERMISSION_DENIED && deniedProviderCalls === 0,
  );
  denied.close();
  let notificationCount = 0;
  client.onNotification(() => {
    notificationCount++;
  });
  await connection.notifyEnvironmentChanged({ colorScheme: 'dark' });
  await flush();
  check('notification delivery', notificationCount === 1);
  const failurePair = linked();
  createHost({
    ...config,
    capabilities: {
      profile: {
        async get() {
          throw new Error('host-only-test-error');
        },
      },
    },
  }).connect(failurePair.host);
  const failed = createClient({ transport: failurePair.client });
  clients.push(failed);
  await failed.initialize();
  let failureCode: unknown;
  let failureMessage = '';
  try {
    await failed.call('profile.get', {});
  } catch (error) {
    failureCode = (error as { code?: unknown }).code;
    failureMessage = String((error as { message?: unknown }).message);
  }
  await flush();
  const scheduler = globals.__t27Scheduler as { snapshot(): { hostDiagnosticCount: number } };
  check(
    'provider error stays in host diagnostic sink',
    failureCode === ERROR_CODES.INTERNAL_ERROR &&
      !failureMessage.includes('host-only-test-error') &&
      scheduler.snapshot().hostDiagnosticCount === 1,
  );
  failed.close();
  const silent: Transport = {
    send() {},
    onMessage() {
      return () => {};
    },
    close() {},
  };
  const timeout = createClient({ transport: silent, timeoutMs: 8 });
  clients.push(timeout);
  let timeoutCode: unknown;
  try {
    await timeout.call('portal.ping', {});
  } catch (error) {
    timeoutCode = (error as { code?: unknown }).code;
  }
  check('client timer timeout', timeoutCode === ERROR_CODES.TIMEOUT);
  timeout.close();
  let cancelledTimerRan = false;
  const timer = setTimeout(() => {
    cancelledTimerRan = true;
  }, 12);
  clearTimeout(timer);
  const order: string[] = [];
  queueMicrotask(() => {
    order.push('microtask');
  });
  await new Promise<void>((resolve) =>
    setTimeout(() => {
      order.push('timer');
      resolve();
    }, 20),
  );
  check('timer cancellation', !cancelledTimerRan);
  check('microtask before later timer', order.join(',') === 'microtask,timer');
  report.complete = true;
}

globals.__t27 = {
  start(text: string) {
    if (started || report.closed) {
      return false;
    }
    started = true;
    void run(text).catch((error) => {
      report.error = String(error);
      report.complete = true;
    });
    return true;
  },
  report() {
    return encodeJson(report);
  },
  close() {
    if (report.closed) {
      return;
    }
    report.closed = true;
    for (const client of clients) {
      client.close();
    }
  },
};
