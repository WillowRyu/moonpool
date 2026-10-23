// @vitest-environment happy-dom
/** T14 — the dismissal button sends one async request after initialization. */
import { MoonpoolError } from '@moonpool/client';
import type { JsonValue } from '@moonpool/protocol';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { createCloseDemo } from '../src/close-demo';

afterEach(() => document.body.replaceChildren());

function setup() {
  const root = document.createElement('section');
  document.body.append(root);
  const call = vi.fn(
    async (_method: string, _params?: Record<string, JsonValue>): Promise<unknown> => ({}),
  );
  const demo = createCloseDemo(root, { call });
  const button = root.querySelector<HTMLButtonElement>('#portal-close');
  const output = root.querySelector<HTMLElement>('#close-output');
  if (button === null || output === null) {
    throw new Error('close demo controls must exist');
  }
  return { root, call, demo, button, output };
}

describe('T14 — mini-app dismissal controls', () => {
  it('does not send before ready or after an unavailable handshake', () => {
    const h = setup();
    expect(h.button.disabled).toBe(true);
    h.button.click();
    h.demo.unavailable('not requested: handshake failed');
    h.button.click();
    expect(h.call).not.toHaveBeenCalled();
    expect(h.output.textContent).toBe('not requested: handshake failed');
  });

  it('sends the declared method and reason after ready, then displays acceptance', async () => {
    const h = setup();
    h.demo.ready();
    expect(h.button.disabled).toBe(false);
    h.button.click();
    await vi.waitFor(() => expect(h.output.textContent).toBe('Close request accepted'));
    expect(h.call).toHaveBeenCalledExactlyOnceWith('portal.close', { reason: 'finished' });
    expect(h.button.disabled).toBe(true);
    h.button.click();
    expect(h.call).toHaveBeenCalledOnce();
  });

  it('prevents repeated requests while awaiting acceptance', async () => {
    const h = setup();
    let finish: ((value: unknown) => void) | undefined;
    h.call.mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    h.demo.ready();
    h.button.click();
    h.button.click();
    expect(h.button.disabled).toBe(true);
    expect(h.output.textContent).toBe('Close request pending...');
    expect(h.call).toHaveBeenCalledOnce();
    if (finish === undefined) {
      throw new Error('close request must be pending');
    }
    finish({});
    await vi.waitFor(() => expect(h.output.textContent).toBe('Close request accepted'));
  });

  it.each([-32001, -32602, -32603])(
    'displays error code %i and allows a deliberate retry',
    async (code) => {
      const h = setup();
      h.call.mockRejectedValueOnce(new MoonpoolError(code, 'Close unavailable'));
      h.demo.ready();
      h.button.click();
      await vi.waitFor(() =>
        expect(h.output.textContent).toBe(`portal.close failed: ${code} - Close unavailable`),
      );
      expect(h.button.disabled).toBe(false);
      expect(h.call).toHaveBeenCalledOnce();
      h.button.click();
      await vi.waitFor(() => expect(h.output.textContent).toBe('Close request accepted'));
      expect(h.call).toHaveBeenCalledTimes(2);
    },
  );

  it('renders error messages as text', async () => {
    const h = setup();
    h.call.mockRejectedValueOnce(new MoonpoolError(-32001, '<img src="x" onerror="alert(1)">'));
    h.demo.ready();
    h.button.click();
    await vi.waitFor(() => expect(h.output.textContent).toContain('<img'));
    expect(h.root.querySelector('img')).toBeNull();
  });
});
