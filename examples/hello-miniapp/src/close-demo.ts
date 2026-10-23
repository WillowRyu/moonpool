import { type MoonpoolClient, MoonpoolError } from '@moonpool/client';
import { PORTAL_METHODS } from '@moonpool/protocol';

/** T14 — request host dismissal; acceptance does not confirm completed teardown. */
export function createCloseDemo(
  root: HTMLElement,
  client: Pick<MoonpoolClient, 'call'>,
): { ready(): void; unavailable(message: string): void } {
  root.innerHTML = `
    <h2>Portal</h2>
    <button type="button" id="portal-close" disabled>Close mini app</button>
    <p id="close-output" role="status" aria-live="polite">waiting for handshake...</p>
  `;
  const button = root.querySelector<HTMLButtonElement>('#portal-close');
  const output = root.querySelector<HTMLElement>('#close-output');
  if (button === null || output === null) {
    throw new Error('hello-miniapp: close controls are missing');
  }
  let available = false;

  const requestClose = async (): Promise<void> => {
    if (button.disabled) {
      return;
    }
    button.disabled = true;
    output.textContent = 'Close request pending...';
    try {
      await client.call(PORTAL_METHODS.CLOSE, { reason: 'finished' });
      available = false;
      output.textContent = 'Close request accepted';
    } catch (error) {
      const detail =
        error instanceof MoonpoolError ? `${error.code} - ${error.message}` : String(error);
      output.textContent = `portal.close failed: ${detail}`;
      button.disabled = !available;
    }
  };

  button.addEventListener('click', () => {
    void requestClose();
  });
  return {
    ready() {
      available = true;
      button.disabled = false;
      output.textContent = 'ready — request dismissal when finished';
    },
    unavailable(message) {
      available = false;
      button.disabled = true;
      output.textContent = message;
    },
  };
}
