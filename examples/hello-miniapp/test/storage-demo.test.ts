// @vitest-environment happy-dom
/** T04 / SPEC §6.3 and §9.3 — exercise storage controls over the actual bridge kernel. */
import { createClient, MoonpoolError } from '@moonpool/client';
import { ERROR_CODES, type StorageSetValue } from '@moonpool/protocol';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { createHost } from '../../../packages/host/src/index';
import { createLinkedTransports } from '../../../test-support/memory-transport';
import { createMemoryStorageProvider } from '../../mock-host/src/memory-storage';
import { createStorageDemo } from '../src/storage-demo';

const APP_ID = 'com.example.hello';
const cleanup: Array<() => void> = [];

afterEach(() => {
  for (const close of cleanup.splice(0)) {
    close();
  }
  document.body.replaceChildren();
});

function find<T extends Element>(root: HTMLElement, selector: string): T {
  const element = root.querySelector<T>(selector);
  if (element === null) {
    throw new Error(`missing storage control: ${selector}`);
  }
  return element;
}

function setup(grantedScopes = ['profile', 'storage']) {
  const transport = createLinkedTransports();
  const storage = createMemoryStorageProvider();
  const client = createClient({ transport: transport.a });
  const calls = vi.spyOn(client, 'call');
  createHost({
    hostInfo: { name: 'storage-demo-test', version: '0.1.0', platform: 'browser' },
    manifest: {
      manifestVersion: 1,
      id: APP_ID,
      name: 'Hello',
      version: '1.0.0',
      entry: 'index.html',
      protocolVersion: '0.1',
      permissions: ['profile', 'storage'],
    },
    grantedScopes,
    environment: { locale: 'en', colorScheme: 'light' },
    capabilities: { storage },
  }).connect(transport.b);
  cleanup.push(() => {
    client.close();
    transport.b.close();
  });

  const root = document.createElement('div');
  document.body.append(root);
  const demo = createStorageDemo(root, client);
  return {
    root,
    storage,
    calls,
    async initialize() {
      const result = await client.initialize();
      demo.ready(result.grantedScopes);
    },
    click(action: string) {
      find<HTMLButtonElement>(root, `#storage-${action}`).click();
    },
    output: () => find<HTMLElement>(root, '#storage-output').textContent,
    controls: () => find<HTMLFieldSetElement>(root, '#storage-controls'),
  };
}

describe('T04 — mini-app storage controls', () => {
  it('does not send storage requests before initialization', () => {
    const demo = setup();

    demo.click('set');

    expect(demo.controls().disabled).toBe(true);
    expect(demo.calls).not.toHaveBeenCalled();
    expect(demo.output()).toBe('waiting for handshake...');
  });

  it.each(['set', 'get', 'delete'])(
    'shows host denial for storage.%s in the default configuration',
    async (action) => {
      const demo = setup(['profile']);
      await demo.storage.set(APP_ID, 'settings', 'original');
      await demo.initialize();

      expect(find<HTMLElement>(demo.root, '#storage-permission').textContent).toContain(
        'not granted',
      );
      demo.click(action);

      await vi.waitFor(() => expect(demo.output()).toContain(`storage.${action} failed: -32000`));
      expect(demo.controls().disabled).toBe(false);
      await expect(demo.storage.get(APP_ID, 'settings')).resolves.toBe('original');
    },
  );

  it('sets, reads, and deletes text through the host and renders it without HTML interpretation', async () => {
    const demo = setup();
    await demo.initialize();
    const value = '<b>stored text</b>';
    find<HTMLInputElement>(demo.root, '#storage-value').value = value;

    demo.click('set');
    await vi.waitFor(() => expect(demo.output()).toBe('storage.set succeeded'));
    await expect(demo.storage.get(APP_ID, 'settings')).resolves.toBe(value);

    demo.click('get');
    await vi.waitFor(() => expect(demo.output()).toBe(`storage.get → ${JSON.stringify(value)}`));
    expect(demo.root.querySelector('#storage-output b')).toBeNull();

    demo.click('delete');
    await vi.waitFor(() => expect(demo.output()).toBe('storage.delete succeeded'));
    demo.click('get');
    await vi.waitFor(() => expect(demo.output()).toBe('storage.get → null'));
  });

  it('preserves an empty key and empty string value', async () => {
    const demo = setup();
    await demo.initialize();
    find<HTMLInputElement>(demo.root, '#storage-key').value = '';
    find<HTMLInputElement>(demo.root, '#storage-value').value = '';

    demo.click('set');

    await vi.waitFor(() => expect(demo.output()).toBe('storage.set succeeded'));
    await expect(demo.storage.get(APP_ID, '')).resolves.toBe('');
  });

  it('waits for an action to finish and prevents overlapping requests', async () => {
    const demo = setup();
    await demo.initialize();
    let complete!: (result: unknown) => void;
    demo.calls.mockReturnValueOnce(
      new Promise((resolve) => {
        complete = resolve;
      }),
    );

    demo.click('set');
    const disabledWhilePending = demo.controls().disabled;
    demo.click('get');
    const callsWhilePending = demo.calls.mock.calls.length;
    complete({});

    await vi.waitFor(() => expect(demo.output()).toBe('storage.set succeeded'));
    expect(disabledWhilePending).toBe(true);
    expect(callsWhilePending).toBe(1);
    expect(demo.controls().disabled).toBe(false);
  });

  it('renders error details as text and permits another action after failure', async () => {
    const demo = setup();
    await demo.initialize();
    const message = '<img src="invalid" onerror="alert(1)">';
    demo.calls.mockRejectedValueOnce(
      new MoonpoolError(ERROR_CODES.CAPABILITY_UNAVAILABLE, message),
    );

    demo.click('get');

    await vi.waitFor(() => expect(demo.output()).toBe(`storage.get failed: -32001 - ${message}`));
    expect(demo.root.querySelector('#storage-output img')).toBeNull();
    demo.click('get');
    await vi.waitFor(() => expect(demo.output()).toBe('storage.get → null'));
  });

  it.each([
    { label: 'null', result: null },
    { label: 'a missing value', result: {} },
    { label: 'undefined', result: { value: undefined } },
    { label: 'a non-JSON object', result: { value: new Date(0) } },
    { label: 'a non-finite number', result: { value: Number.NaN } },
  ])('rejects $label in a storage.get result', async ({ result }) => {
    const demo = setup();
    await demo.initialize();
    demo.calls.mockResolvedValueOnce(result);

    demo.click('get');

    await vi.waitFor(() =>
      expect(demo.output()).toBe(
        'storage.get failed: Error: storage.get returned an invalid value',
      ),
    );
    expect(demo.controls().disabled).toBe(false);
  });

  const falsyValues: Array<{ label: string; value: StorageSetValue }> = [
    { label: 'false', value: false },
    { label: 'zero', value: 0 },
    { label: 'an empty string', value: '' },
  ];
  it.each(falsyValues)('displays $label without replacing it with null', async ({ value }) => {
    const demo = setup();
    await demo.storage.set(APP_ID, 'settings', value);
    await demo.initialize();

    demo.click('get');

    await vi.waitFor(() => expect(demo.output()).toBe(`storage.get → ${JSON.stringify(value)}`));
  });
});
