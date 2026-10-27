import { type MoonpoolClient, MoonpoolError } from '@moonpool/client';
import { isJsonValue, STORAGE_METHODS } from '@moonpool/protocol';

type StorageMethod = (typeof STORAGE_METHODS)[keyof typeof STORAGE_METHODS];

/**
 * T04 / SPEC §6.3 — a text-value demo, leaving authorization to the host (§9.3).
 * Ungranted calls remain available deliberately so the demo can show -32000.
 * Disable controls until the handshake and during each request, not by scope.
 */
export function createStorageDemo(
  root: HTMLElement,
  client: Pick<MoonpoolClient, 'call'>,
): { ready(grantedScopes: readonly string[]): void; unavailable(message: string): void } {
  root.innerHTML = `
    <h2>Storage demo</h2>
    <p id="storage-permission">waiting for handshake...</p>
    <fieldset id="storage-controls" disabled>
      <legend>Stored entry</legend>
      <div class="storage-fields">
        <label for="storage-key">Key<input id="storage-key" value="settings"></label>
        <label for="storage-value">Value (text)<input id="storage-value" value="dark"></label>
      </div>
      <div class="actions">
        <button type="button" id="storage-set">Set</button>
        <button type="button" id="storage-get">Get</button>
        <button type="button" id="storage-delete">Delete</button>
      </div>
    </fieldset>
    <pre id="storage-output" role="status" aria-live="polite">waiting for handshake...</pre>
  `;

  const controls = root.querySelector<HTMLFieldSetElement>('#storage-controls');
  const keyInput = root.querySelector<HTMLInputElement>('#storage-key');
  const valueInput = root.querySelector<HTMLInputElement>('#storage-value');
  const setButton = root.querySelector<HTMLButtonElement>('#storage-set');
  const getButton = root.querySelector<HTMLButtonElement>('#storage-get');
  const deleteButton = root.querySelector<HTMLButtonElement>('#storage-delete');
  const permission = root.querySelector<HTMLElement>('#storage-permission');
  const output = root.querySelector<HTMLElement>('#storage-output');
  if (
    controls === null ||
    keyInput === null ||
    valueInput === null ||
    setButton === null ||
    getButton === null ||
    deleteButton === null ||
    permission === null ||
    output === null
  ) {
    throw new Error('hello-miniapp: storage controls are missing');
  }

  const perform = async (method: StorageMethod): Promise<void> => {
    if (controls.disabled) {
      return;
    }
    controls.disabled = true;
    output.textContent = `${method} pending...`;
    const key = keyInput.value;
    try {
      switch (method) {
        case STORAGE_METHODS.SET:
          // Preserve the exact text, including empty strings; the host validates params.
          await client.call(method, { key, value: valueInput.value });
          output.textContent = 'storage.set succeeded';
          break;
        case STORAGE_METHODS.GET: {
          const result = await client.call(method, { key });
          if (
            typeof result !== 'object' ||
            result === null ||
            Array.isArray(result) ||
            !('value' in result) ||
            !isJsonValue(result.value)
          ) {
            throw new Error('storage.get returned an invalid value');
          }
          // Render as text: returned data must never become executable HTML.
          output.textContent = `storage.get → ${JSON.stringify(result.value)}`;
          break;
        }
        case STORAGE_METHODS.DELETE:
          await client.call(method, { key });
          output.textContent = 'storage.delete succeeded';
          break;
      }
    } catch (error) {
      const detail =
        error instanceof MoonpoolError ? `${error.code} - ${error.message}` : String(error);
      output.textContent = `${method} failed: ${detail}`;
    } finally {
      controls.disabled = false;
    }
  };

  setButton.addEventListener('click', () => {
    void perform(STORAGE_METHODS.SET);
  });
  getButton.addEventListener('click', () => {
    void perform(STORAGE_METHODS.GET);
  });
  deleteButton.addEventListener('click', () => {
    void perform(STORAGE_METHODS.DELETE);
  });

  return {
    ready(grantedScopes) {
      permission.textContent = grantedScopes.includes('storage')
        ? 'storage granted — set, get, and delete are available'
        : 'storage not granted — try an action to see host enforcement (-32000)';
      output.textContent = 'ready — choose an action';
      controls.disabled = false;
    },
    unavailable(message) {
      permission.textContent = 'storage unavailable';
      output.textContent = message;
      controls.disabled = true;
    },
  };
}
