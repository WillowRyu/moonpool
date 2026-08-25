/**
 * hello-miniapp — the smallest thing that proves a mini app can run.
 *
 * At this step it only proves the plumbing: TypeScript from a workspace
 * package resolves, transforms, and executes in the browser. The bridge
 * itself arrives with the iframe transport.
 */
import { PROTOCOL_VERSION } from '@moonpool/protocol';

const root = document.querySelector<HTMLElement>('#app');
if (root === null) {
  throw new Error('hello-miniapp: #app is missing from index.html');
}

root.innerHTML = `
  <h1>Hello mini app</h1>
  <dl>
    <dt>origin</dt><dd><code>${window.location.origin}</code></dd>
    <dt>protocol</dt><dd><code>${PROTOCOL_VERSION}</code></dd>
    <dt>bridge</dt><dd>not connected yet</dd>
  </dl>
`;
