/** Drive the actual wrapper entry in happy-dom; real CSP/realms are measured separately. */
import { vi } from 'vitest';
import type { WrapperControls } from '../../src/browser-contract';
import { startWrapper } from '../../src/portal-wrapper';

const controls: WrapperControls[] = [];
export async function mountCurrentWrapper(): Promise<void> {
  const frame = document.querySelector<HTMLIFrameElement>('#portal > iframe');
  const child = frame?.contentWindow;
  const doc = frame?.contentDocument;
  if (
    frame === null ||
    frame === undefined ||
    child === null ||
    child === undefined ||
    doc === null ||
    doc === undefined
  ) {
    throw new Error('missing wrapper frame');
  }
  vi.spyOn(child.location, 'href', 'get').mockReturnValue(frame.src);
  // Vitest's global Window proxy differs from happy-dom's iframe.parent wrapper.
  // The actual browser parent/source identities are verified separately.
  vi.spyOn(child, 'parent', 'get').mockReturnValue(window);
  doc.body.innerHTML = '<div id="portal"></div>';
  controls.push(await startWrapper(child));
}
export async function loadMockHost(): Promise<void> {
  await import('../../src/main');
  await mountCurrentWrapper();
}
export function currentGuest(): HTMLIFrameElement | null {
  return (
    document
      .querySelector<HTMLIFrameElement>('#portal > iframe')
      ?.contentDocument?.querySelector('iframe') ?? null
  );
}
export async function cleanupWrappers(): Promise<void> {
  for (const control of controls.splice(0)) {
    await control.dispose();
  }
  Reflect.deleteProperty(window, 'moonpoolBootstrap');
}
