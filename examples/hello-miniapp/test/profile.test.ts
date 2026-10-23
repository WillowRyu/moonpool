// @vitest-environment happy-dom
/**
 * T02 / SPEC §5 and §6.3 — observe the example's actual entry point.
 * A controlled client isolates UI ordering and text rendering from transport tests.
 */
import { createClient, type MoonpoolClient, MoonpoolError } from '@moonpool/client';
import { ERROR_CODES, type InitializeResult, PROTOCOL_VERSION } from '@moonpool/protocol';
import { createIframeTransport } from '@moonpool/transport-iframe';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@moonpool/client', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@moonpool/client')>()),
  createClient: vi.fn(),
}));
vi.mock('@moonpool/transport-iframe', () => ({ createIframeTransport: vi.fn() }));

const HANDSHAKE: InitializeResult = {
  protocolVersion: PROTOCOL_VERSION,
  miniApp: { id: 'com.example.hello', version: '1.0.0' },
  host: { name: 'moonpool-mock-host', version: '0.1.0', platform: 'browser' },
  grantedScopes: ['profile'],
  environment: { locale: 'ko-KR', colorScheme: 'light' },
};

let client: MoonpoolClient;

beforeEach(() => {
  vi.resetModules();
  document.body.innerHTML = '<div id="app"></div>';
  // Supply an embedder identity; no real window messaging runs in this UI test.
  vi.spyOn(window, 'parent', 'get').mockReturnValue({} as Window);
  vi.mocked(createIframeTransport).mockReturnValue({
    send: vi.fn(),
    onMessage: vi.fn(() => () => {}),
    close: vi.fn(),
  });
  client = {
    initialize: vi.fn().mockResolvedValue(HANDSHAKE),
    call: vi.fn().mockResolvedValue({ displayName: 'Moonpool Explorer' }),
    close: vi.fn(),
  };
  vi.mocked(createClient).mockReturnValue(client);
});

afterEach(() => {
  vi.restoreAllMocks();
  document.body.replaceChildren();
});

describe('T02 — hello-miniapp profile display', () => {
  it('requests profile.get after initialization and displays the host-provided name', async () => {
    await import('../src/main');

    expect(client.call).toHaveBeenCalledExactlyOnceWith('profile.get');
    expect(document.querySelector('#profile')?.textContent).toBe('Moonpool Explorer');
    expect(document.querySelector('#bridge')?.textContent).toContain('connected to');
    expect(document.querySelector<HTMLFieldSetElement>('#storage-controls')?.disabled).toBe(false);
  });

  it('waits for the handshake before asking for a profile', async () => {
    let completeHandshake!: (result: InitializeResult) => void;
    vi.mocked(client.initialize).mockReturnValue(
      new Promise((resolve) => {
        completeHandshake = resolve;
      }),
    );
    const loading = import('../src/main');
    await vi.waitFor(() => expect(client.initialize).toHaveBeenCalledOnce());

    const callsBeforeHandshake = vi.mocked(client.call).mock.calls.length;
    const pendingLabel = document.querySelector('#profile')?.textContent;
    // Settle the entry point even when an assertion below fails during RED.
    completeHandshake(HANDSHAKE);
    await loading;

    expect(callsBeforeHandshake).toBe(0);
    expect(pendingLabel).toBe('waiting for handshake...');
    expect(document.querySelector('#profile')?.textContent).toBe('Moonpool Explorer');
  });

  it('renders profile and handshake strings as text rather than HTML', async () => {
    const displayName = '<img src="invalid" onerror="alert(1)">';
    vi.mocked(client.call).mockResolvedValue({ displayName });
    vi.mocked(client.initialize).mockResolvedValue({
      ...HANDSHAKE,
      host: { ...HANDSHAKE.host, name: '<b>host name</b>' },
    });

    await import('../src/main');

    expect(document.querySelector('#profile')?.textContent).toBe(displayName);
    expect(document.querySelector('#profile img')).toBeNull();
    expect(document.querySelector('#bridge')?.textContent).toContain('<b>host name</b>');
    expect(document.querySelector('#bridge b')).toBeNull();
  });

  it.each([
    { label: 'null', value: null },
    { label: 'undefined', value: undefined },
    { label: 'a scalar result', value: 'Moonpool Explorer' },
    { label: 'an array', value: [] },
    { label: 'a missing displayName', value: {} },
    { label: 'an undefined displayName', value: { displayName: undefined } },
    { label: 'a null displayName', value: { displayName: null } },
    { label: 'a numeric displayName', value: { displayName: 42 } },
    { label: 'a boolean displayName', value: { displayName: false } },
    {
      label: 'an array with a displayName property',
      value: Object.assign([], { displayName: 'Moonpool Explorer' }),
    },
  ])('rejects $label as a profile display error', async ({ value }) => {
    vi.mocked(client.call).mockResolvedValue(value);

    await import('../src/main');

    expect(document.querySelector('#profile')?.textContent).toBe(
      'profile.get failed: Error: profile.get returned an invalid displayName',
    );
    expect(document.querySelector('#bridge')?.textContent).toContain('connected to');
  });

  it('accepts an empty displayName because the contract requires a string, not a nonempty name', async () => {
    vi.mocked(client.call).mockResolvedValue({ displayName: '' });

    await import('../src/main');

    expect(document.querySelector('#profile')?.textContent).toBe('');
    expect(document.querySelector('#bridge')?.textContent).toContain('connected to');
  });

  it.each([
    { code: ERROR_CODES.PERMISSION_DENIED, message: 'Permission denied' },
    { code: ERROR_CODES.CAPABILITY_UNAVAILABLE, message: 'Profile unavailable' },
  ])(
    'shows profile error $code while keeping the handshake successful',
    async ({ code, message }) => {
      vi.mocked(client.call).mockRejectedValue(new MoonpoolError(code, message));

      await import('../src/main');

      expect(document.querySelector('#profile')?.textContent).toBe(
        `profile.get failed: ${code} - ${message}`,
      );
      expect(document.querySelector('#bridge')?.textContent).toContain('connected to');
      expect(document.querySelector<HTMLFieldSetElement>('#storage-controls')?.disabled).toBe(
        false,
      );
    },
  );

  it('does not request a profile when the handshake fails', async () => {
    vi.mocked(client.initialize).mockRejectedValue(
      new MoonpoolError(ERROR_CODES.PROTOCOL_VERSION_UNSUPPORTED, 'Unsupported version'),
    );

    await import('../src/main');

    expect(client.call).not.toHaveBeenCalled();
    expect(document.querySelector('#bridge')?.textContent).toBe(
      'handshake failed: -32004 - Unsupported version',
    );
    expect(document.querySelector('#profile')?.textContent).toBe('not requested: handshake failed');
    expect(document.querySelector<HTMLFieldSetElement>('#storage-controls')?.disabled).toBe(true);
  });
});
